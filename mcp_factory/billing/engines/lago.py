"""
Lago Billing Engine

Complete Lago billing engine including SDK client and provider implementation.
All Lago-related functionality is consolidated in this module for better cohesion.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from ...exceptions import ServerError
from ..models import BillingResult, PricingPlan, Subscription, SubscriptionStatus, UsageEvent
from . import BillingClient

logger = logging.getLogger(__name__)


# ============================================================================
# Lago SDK Client Implementation
# ============================================================================


class LagoBillingClient(BillingClient):
    """
    Lago client using the official Python SDK.

    This wrapper provides async compatibility and integrates the official
    Lago SDK with MCP Factory's billing architecture.
    """

    def _ensure_client_initialized(self) -> bool:
        """Check if client is initialized and return status"""
        return self._client is not None

    def _standardize_data_list(
        self, data_list: list[dict[str, Any]], standardization_map: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Standardize a list of data objects using a field mapping"""
        standardized_list = []
        for item in data_list:
            standardized_item = {}
            for standard_key, source_key in standardization_map.items():
                if "." in source_key:
                    # Handle nested keys like "lago_id|id"
                    keys = source_key.split("|")
                    value = None
                    for key in keys:
                        if key in item:
                            value = item[key]
                            break
                    standardized_item[standard_key] = value or ""
                else:
                    standardized_item[standard_key] = item.get(source_key, "")
            standardized_list.append(standardized_item)
        return standardized_list

    def __init__(self, api_key: str, api_url: str = "https://api.lago.dev") -> None:
        """
        Initialize Lago SDK client.

        Args:
            api_key: Lago API key
            api_url: Lago API URL (default: cloud service)
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.api_url = api_url
        self._client: Any = None

        logger.info(f"LagoBillingClient initialized for {self.api_url}")
        logger.info("Using official Lago Python SDK")

    async def initialize(self) -> bool:
        """Initialize the Lago SDK client"""
        try:
            # Import the official Lago SDK
            from lago_python_client import Client

            # Configure the client (simplified - no separate Configuration class needed)
            self._client = Client(api_key=self.api_key, api_url=self.api_url)

            # Test connection by getting organization info
            if self._client:
                await asyncio.to_thread(self._client.organizations.find)

            logger.info("Successfully connected to Lago using official SDK")
            return True

        except ImportError:
            logger.error("Lago Python SDK not installed. Run: pip install lago-python-client")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Lago SDK client: {e}")
            raise ServerError(f"Failed to initialize Lago SDK client: {e}") from e

    async def cleanup(self) -> None:
        """Clean up resources"""
        self._client = None
        logger.info("LagoBillingClient cleaned up")

    async def create_customer(self, customer_id: str, email: str, name: str) -> BillingResult:
        """Create a customer in Lago"""
        if not self._ensure_client_initialized():
            return BillingResult(success=False, message="Client not initialized")

        try:
            customer_data = {"external_id": customer_id, "email": email, "name": name}

            result = await asyncio.to_thread(self._client.customers.create, customer_data)

            logger.info(f"Customer created in Lago: {customer_id}")
            return BillingResult(success=True, message="Customer created", data=result)

        except Exception as e:
            logger.error(f"Failed to create customer {customer_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get customer from Lago"""
        if not self._ensure_client_initialized():
            return None

        try:
            result = await asyncio.to_thread(self._client.customers.find, customer_id)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Failed to get customer {customer_id}: {e}")
            return None

    async def create_subscription(self, customer_id: str, plan_id: str) -> BillingResult:
        """Create a subscription in Lago"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            # Note: Lago API uses "plan_code" field, but we use plan_id in our interface
            subscription_data = {"external_customer_id": customer_id, "plan_code": plan_id}

            result = await asyncio.to_thread(self._client.subscriptions.create, subscription_data)

            logger.info(f"Subscription created for customer {customer_id}")
            return BillingResult(success=True, message="Subscription created", data=result)

        except Exception as e:
            logger.error(f"Failed to create subscription for {customer_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_subscription(self, customer_id: str) -> Subscription | None:
        """Get customer subscription from Lago"""
        if not self._client:
            return None

        try:
            result = await asyncio.to_thread(self._client.subscriptions.find, customer_id)

            if result:
                # Convert Lago subscription to our Subscription model
                return Subscription(
                    user_id=customer_id,
                    plan_id=result.get("plan_code", ""),
                    status=SubscriptionStatus(result.get("status", "inactive")),
                    started_at=datetime.fromisoformat(result.get("started_at", datetime.now().isoformat())),
                    expires_at=datetime.fromisoformat(result["ended_at"]) if result.get("ended_at") else None,
                )
            return None

        except Exception as e:
            logger.error(f"Failed to get subscription for {customer_id}: {e}")
            return None

    async def cancel_subscription(self, subscription_id: str) -> BillingResult:
        """Cancel a subscription in Lago"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            await asyncio.to_thread(self._client.subscriptions.terminate, subscription_id)

            logger.info(f"Subscription cancelled: {subscription_id}")
            return BillingResult(success=True, message="Subscription cancelled")

        except Exception as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def record_usage_event(self, event: UsageEvent) -> BillingResult:
        """Record a usage event in Lago"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            # Use the UsageEvent's built-in Lago conversion method
            event_data = event.to_lago_event()

            await asyncio.to_thread(self._client.events.create, event_data)

            logger.info(f"Usage event recorded for {event.user_id}: {event.event_type}")
            return BillingResult(success=True, message="Usage event recorded")

        except Exception as e:
            logger.error(f"Failed to record usage event: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_plans(self) -> list[PricingPlan]:
        """Get available pricing plans from Lago"""
        if not self._client:
            return []

        try:
            result = await asyncio.to_thread(self._client.plans.find_all)

            plans = []
            for plan_data in result.get("plans", []):
                plan = PricingPlan(
                    plan_id=plan_data.get("code", ""),
                    name=plan_data.get("name", ""),
                    description=plan_data.get("description", ""),
                    price=float(plan_data.get("amount_cents", 0)) / 100,
                    currency=plan_data.get("amount_currency", "USD"),
                    billing_cycle=plan_data.get("interval", "monthly"),
                )
                plans.append(plan)

            return plans

        except Exception as e:
            logger.error(f"Failed to get plans: {e}")
            return []

    # ============================================================================
    # Wallet and Prepaid Credits API
    # ============================================================================

    async def create_wallet(
        self, customer_id: str, name: str = "Default Wallet", rate_amount: float = 1.0, currency: str = "USD"
    ) -> BillingResult:
        """Create a wallet for prepaid credits"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            wallet_data = {
                "external_customer_id": customer_id,
                "name": name,
                "rate_amount": str(int(rate_amount * 100)),  # Convert to cents
                "currency": currency,
            }

            result = await asyncio.to_thread(self._client.wallets.create, wallet_data)

            logger.info(f"Wallet created for customer {customer_id}")
            return BillingResult(success=True, message="Wallet created", data=result)

        except Exception as e:
            logger.error(f"Failed to create wallet for {customer_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_wallet(self, customer_id: str) -> dict[str, Any] | None:
        """Get customer's wallet information"""
        if not self._client:
            return None

        try:
            result = await asyncio.to_thread(self._client.wallets.find, customer_id)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Failed to get wallet for {customer_id}: {e}")
            return None

    async def add_credits(self, customer_id: str, credits: float, source: str = "purchase") -> BillingResult:
        """Add credits to customer's wallet"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            transaction_data = {
                "external_customer_id": customer_id,
                "paid_credits": str(credits) if source == "purchase" else "0",
                "granted_credits": str(credits) if source == "grant" else "0",
            }

            result = await asyncio.to_thread(self._client.wallet_transactions.create, transaction_data)

            logger.info(f"Added {credits} credits to {customer_id} via {source}")
            return BillingResult(success=True, message="Credits added", data=result)

        except Exception as e:
            logger.error(f"Failed to add credits for {customer_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_wallet_balance(self, customer_id: str) -> dict[str, Any] | None:
        """Get current wallet balance and usage"""
        if not self._client:
            return None

        try:
            wallet = await self.get_wallet(customer_id)
            if wallet:
                return {
                    "balance_cents": wallet.get("balance_cents", 0),
                    "credits_balance": wallet.get("credits_balance", 0),
                    "ongoing_balance_cents": wallet.get("ongoing_balance_cents", 0),
                    "currency": wallet.get("currency", "USD"),
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get wallet balance for {customer_id}: {e}")
            return None

    async def get_wallet_transactions(self, customer_id: str) -> list[dict[str, Any]]:
        """Get wallet transaction history with standardized format"""
        if not self._client:
            return []

        try:
            result = await asyncio.to_thread(self._client.wallet_transactions.find_all, customer_id)

            raw_transactions = result.get("wallet_transactions", [])

            # Standardize transaction format for analytics
            standardized_transactions = []
            for tx in raw_transactions:
                standardized_tx = {
                    "id": tx.get("lago_id", tx.get("id", "")),
                    "credits": float(tx.get("amount", 0)),
                    "transaction_type": "inbound" if float(tx.get("amount", 0)) > 0 else "outbound",
                    "source": tx.get("transaction_type", "unknown"),
                    "created_at": tx.get("created_at", ""),
                    "metadata": tx.get("metadata", {}),
                    "status": tx.get("status", "settled"),
                }
                standardized_transactions.append(standardized_tx)

            logger.info(f"Retrieved {len(standardized_transactions)} transactions for {customer_id}")
            return standardized_transactions

        except Exception as e:
            logger.error(f"Failed to get wallet transactions for {customer_id}: {e}")
            return []

    # ============================================================================
    # Invoice Management API (Enterprise-level required features)
    # ============================================================================

    async def create_invoice(self, customer_id: str, currency: str = "USD") -> BillingResult:
        """Create an invoice for a customer"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            invoice_data = {"external_customer_id": customer_id, "currency": currency}

            result = await asyncio.to_thread(self._client.invoices.create, invoice_data)

            logger.info(f"Invoice created for customer {customer_id}")
            return BillingResult(success=True, message="Invoice created", data=result)

        except Exception as e:
            logger.error(f"Failed to create invoice for {customer_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_invoices(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get invoices for a customer"""
        if not self._client:
            return []

        try:
            result = await asyncio.to_thread(
                self._client.invoices.find_all, {"external_customer_id": customer_id, "per_page": limit}
            )

            invoices = result.get("invoices", [])

            # Standardize invoice format
            standardized_invoices = []
            for invoice in invoices:
                standardized_invoice = {
                    "id": invoice.get("lago_id", ""),
                    "invoice_number": invoice.get("number", ""),
                    "status": invoice.get("status", ""),
                    "amount_cents": invoice.get("fees_amount_cents", 0),
                    "currency": invoice.get("currency", "USD"),
                    "issued_at": invoice.get("issued_at", ""),
                    "payment_due_date": invoice.get("payment_due_date", ""),
                    "customer_id": customer_id,
                }
                standardized_invoices.append(standardized_invoice)

            logger.info(f"Retrieved {len(standardized_invoices)} invoices for {customer_id}")
            return standardized_invoices

        except Exception as e:
            logger.error(f"Failed to get invoices for {customer_id}: {e}")
            return []

    async def get_invoice_pdf(self, invoice_id: str) -> bytes | None:
        """Get invoice PDF"""
        if not self._client:
            return None

        try:
            # Note: This would need to be implemented based on Lago's PDF API
            # For now, return None as placeholder
            logger.info(f"PDF requested for invoice {invoice_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get PDF for invoice {invoice_id}: {e}")
            return None

    # ============================================================================
    # Billable Metrics API (Complex billing rules)
    # ============================================================================

    async def create_billable_metric(self, metric_data: dict[str, Any]) -> BillingResult:
        """Create a billable metric"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            result = await asyncio.to_thread(self._client.billable_metrics.create, metric_data)

            logger.info(f"Billable metric created: {metric_data.get('code', 'unknown')}")
            return BillingResult(success=True, message="Billable metric created", data=result)

        except Exception as e:
            logger.error(f"Failed to create billable metric: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_billable_metrics(self) -> list[dict[str, Any]]:
        """Get all billable metrics"""
        if not self._client:
            return []

        try:
            result = await asyncio.to_thread(self._client.billable_metrics.find_all)

            metrics = result.get("billable_metrics", [])

            # Standardize metric format
            standardized_metrics = []
            for metric in metrics:
                standardized_metric = {
                    "id": metric.get("lago_id", ""),
                    "code": metric.get("code", ""),
                    "name": metric.get("name", ""),
                    "description": metric.get("description", ""),
                    "aggregation_type": metric.get("aggregation_type", ""),
                    "field_name": metric.get("field_name", ""),
                }
                standardized_metrics.append(standardized_metric)

            logger.info(f"Retrieved {len(standardized_metrics)} billable metrics")
            return standardized_metrics

        except Exception as e:
            logger.error(f"Failed to get billable metrics: {e}")
            return []

    # ============================================================================
    # Coupon Management API (Marketing features)
    # ============================================================================

    async def create_coupon(self, coupon_data: dict[str, Any]) -> BillingResult:
        """Create a coupon"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            result = await asyncio.to_thread(self._client.coupons.create, coupon_data)

            logger.info(f"Coupon created: {coupon_data.get('code', 'unknown')}")
            return BillingResult(success=True, message="Coupon created", data=result)

        except Exception as e:
            logger.error(f"Failed to create coupon: {e}")
            return BillingResult(success=False, message=str(e))

    async def apply_coupon(self, customer_id: str, coupon_code: str) -> BillingResult:
        """Apply a coupon to a customer"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            coupon_data = {"external_customer_id": customer_id, "coupon_code": coupon_code}

            result = await asyncio.to_thread(self._client.applied_coupons.create, coupon_data)

            logger.info(f"Coupon {coupon_code} applied to customer {customer_id}")
            return BillingResult(success=True, message="Coupon applied", data=result)

        except Exception as e:
            logger.error(f"Failed to apply coupon {coupon_code} to {customer_id}: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_coupons(self) -> list[dict[str, Any]]:
        """Get all coupons"""
        if not self._client:
            return []

        try:
            result = await asyncio.to_thread(self._client.coupons.find_all)

            coupons = result.get("coupons", [])

            # Standardize coupon format
            standardized_coupons = []
            for coupon in coupons:
                standardized_coupon = {
                    "id": coupon.get("lago_id", ""),
                    "code": coupon.get("code", ""),
                    "name": coupon.get("name", ""),
                    "description": coupon.get("description", ""),
                    "coupon_type": coupon.get("coupon_type", ""),
                    "amount_cents": coupon.get("amount_cents", 0),
                    "percentage_rate": coupon.get("percentage_rate", 0),
                    "frequency": coupon.get("frequency", ""),
                    "status": coupon.get("status", ""),
                }
                standardized_coupons.append(standardized_coupon)

            logger.info(f"Retrieved {len(standardized_coupons)} coupons")
            return standardized_coupons

        except Exception as e:
            logger.error(f"Failed to get coupons: {e}")
            return []

    # ============================================================================
    # Webhook Management API (Event notification)
    # ============================================================================

    async def create_webhook_endpoint(self, webhook_data: dict[str, Any]) -> BillingResult:
        """Create a webhook endpoint"""
        if not self._client:
            return BillingResult(success=False, message="Client not initialized")

        try:
            result = await asyncio.to_thread(self._client.webhook_endpoints.create, webhook_data)

            logger.info(f"Webhook endpoint created: {webhook_data.get('webhook_url', 'unknown')}")
            return BillingResult(success=True, message="Webhook endpoint created", data=result)

        except Exception as e:
            logger.error(f"Failed to create webhook endpoint: {e}")
            return BillingResult(success=False, message=str(e))

    async def get_webhook_endpoints(self) -> list[dict[str, Any]]:
        """Get all webhook endpoints"""
        if not self._client:
            return []

        try:
            result = await asyncio.to_thread(self._client.webhook_endpoints.find_all)

            endpoints = result.get("webhook_endpoints", [])

            # Standardize webhook format
            standardized_endpoints = []
            for endpoint in endpoints:
                standardized_endpoint = {
                    "id": endpoint.get("lago_id", ""),
                    "webhook_url": endpoint.get("webhook_url", ""),
                    "signature_algo": endpoint.get("signature_algo", ""),
                    "created_at": endpoint.get("created_at", ""),
                }
                standardized_endpoints.append(standardized_endpoint)

            logger.info(f"Retrieved {len(standardized_endpoints)} webhook endpoints")
            return standardized_endpoints

        except Exception as e:
            logger.error(f"Failed to get webhook endpoints: {e}")
            return []

    # ============================================================================
    # Analytics and Reporting API (Analytics and reporting)
    # ============================================================================

    async def get_mrr_analytics(self, currency: str = "USD") -> dict[str, Any]:
        """Get Monthly Recurring Revenue analytics"""
        if not self._client:
            return {}

        try:
            result = await asyncio.to_thread(self._client.mrrs.find_all, {"currency": currency})

            mrr_data = result.get("mrrs", [])

            # Calculate analytics
            total_mrr = sum(float(mrr.get("amount_cents", 0)) for mrr in mrr_data) / 100

            analytics = {
                "total_mrr": total_mrr,
                "currency": currency,
                "data_points": len(mrr_data),
                "raw_data": mrr_data,
            }

            logger.info(f"Retrieved MRR analytics: ${total_mrr:.2f} {currency}")
            return analytics

        except Exception as e:
            logger.error(f"Failed to get MRR analytics: {e}")
            return {}

    async def get_gross_revenue_analytics(self, currency: str = "USD") -> dict[str, Any]:
        """Get gross revenue analytics"""
        if not self._client:
            return {}

        try:
            result = await asyncio.to_thread(self._client.gross_revenues.find_all, {"currency": currency})

            revenue_data = result.get("gross_revenues", [])

            # Calculate analytics
            total_revenue = sum(float(rev.get("amount_cents", 0)) for rev in revenue_data) / 100

            analytics = {
                "total_gross_revenue": total_revenue,
                "currency": currency,
                "data_points": len(revenue_data),
                "raw_data": revenue_data,
            }

            logger.info(f"Retrieved gross revenue analytics: ${total_revenue:.2f} {currency}")
            return analytics

        except Exception as e:
            logger.error(f"Failed to get gross revenue analytics: {e}")
            return {}


class MockLagoBillingClient(BillingClient):
    """
    Mock Lago billing client for testing and development.

    Provides the same interface as LagoBillingClient but with simulated responses.
    """

    def __init__(self, api_key: str = "mock_key", api_url: str = "http://localhost:3000") -> None:
        """Initialize mock client"""
        self.api_key = api_key
        self.api_url = api_url
        self._initialized = False

        logger.info("MockLagoBillingClient initialized (development mode)")

    async def initialize(self) -> bool:
        """Initialize mock client"""
        self._initialized = True
        logger.info("Mock Lago client initialized successfully")
        return True

    async def cleanup(self) -> None:
        """Clean up mock resources"""
        self._initialized = False
        logger.info("MockLagoBillingClient cleaned up")

    async def create_customer(self, customer_id: str, email: str, name: str) -> BillingResult:
        """Mock customer creation"""
        logger.info(f"Mock: Created customer {customer_id}")
        return BillingResult(
            success=True, message="Mock customer created", data={"id": customer_id, "email": email, "name": name}
        )

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Mock get customer"""
        return {"external_id": customer_id, "email": f"{customer_id}@example.com", "name": f"User {customer_id}"}

    async def create_subscription(self, customer_id: str, plan_id: str) -> BillingResult:
        """Mock subscription creation"""
        logger.info(f"Mock: Created subscription for {customer_id} with plan {plan_id}")
        return BillingResult(
            success=True, message="Mock subscription created", data={"customer_id": customer_id, "plan_id": plan_id}
        )

    async def get_subscription(self, customer_id: str) -> Subscription | None:
        """Mock get subscription"""
        return Subscription(
            user_id=customer_id,
            plan_id="mock_plan",
            status=SubscriptionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
            expires_at=None,
        )

    async def cancel_subscription(self, subscription_id: str) -> BillingResult:
        """Mock subscription cancellation"""
        logger.info(f"Mock: Cancelled subscription {subscription_id}")
        return BillingResult(success=True, message="Mock subscription cancelled")

    async def record_usage_event(self, event: UsageEvent) -> BillingResult:
        """Mock usage event recording"""
        logger.info(f"Mock: Recorded usage for {event.user_id}")
        return BillingResult(
            success=True, message="Mock usage recorded", data={"event_id": f"mock_event_{event.user_id}"}
        )

    async def get_plans(self) -> list[PricingPlan]:
        """Mock get plans"""
        return [
            PricingPlan(
                plan_id="mock_basic",
                name="Mock Basic Plan",
                description="Basic plan for testing",
                price=9.99,
                currency="USD",
                billing_cycle="monthly",
            ),
            PricingPlan(
                plan_id="mock_pro",
                name="Mock Pro Plan",
                description="Pro plan for testing",
                price=29.99,
                currency="USD",
                billing_cycle="monthly",
            ),
        ]

    # ============================================================================
    # Mock Wallet and Prepaid Credits API
    # ============================================================================

    async def create_wallet(
        self, customer_id: str, name: str = "Default Wallet", rate_amount: float = 1.0, currency: str = "USD"
    ) -> BillingResult:
        """Mock wallet creation"""
        logger.info(f"Mock: Created wallet for {customer_id}")
        return BillingResult(
            success=True,
            message="Mock wallet created",
            data={
                "id": f"wallet_{customer_id}",
                "external_customer_id": customer_id,
                "name": name,
                "rate_amount": rate_amount,
                "currency": currency,
            },
        )

    async def get_wallet(self, customer_id: str) -> dict[str, Any] | None:
        """Mock get wallet"""
        return {
            "id": f"wallet_{customer_id}",
            "external_customer_id": customer_id,
            "name": "Mock Wallet",
            "balance_cents": 10000,  # $100 in cents
            "credits_balance": 100.0,
            "ongoing_balance_cents": 9500,  # $95 in cents
            "currency": "USD",
        }

    async def add_credits(self, customer_id: str, credits: float, source: str = "purchase") -> BillingResult:
        """Mock add credits"""
        logger.info(f"Mock: Added {credits} credits to {customer_id} via {source}")
        return BillingResult(
            success=True,
            message="Mock credits added",
            data={"transaction_id": f"txn_{customer_id}_{credits}", "credits": credits, "source": source},
        )

    async def get_wallet_balance(self, customer_id: str) -> dict[str, Any] | None:
        """Mock get wallet balance"""
        return {"balance_cents": 10000, "credits_balance": 100.0, "ongoing_balance_cents": 9500, "currency": "USD"}

    async def get_wallet_transactions(self, customer_id: str) -> list[dict[str, Any]]:
        """Mock get wallet transactions with realistic developer data"""
        # Generate realistic transaction history for developers
        transactions = []
        base_date = datetime.now() - timedelta(days=30)

        # Simulate revenue transactions over 30 days
        for i in range(20):  # 20 transactions over 30 days
            date = base_date + timedelta(
                days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59)
            )

            # Simulate different services and operations
            services = ["weather_api", "weather_maps", "weather_alerts"]
            operations = ["get_forecast", "get_radar", "get_alerts", "get_historical"]
            users = ["alice", "bob", "charlie", "diana", "eve"]

            service = random.choice(services)
            operation = random.choice(operations)
            user = random.choice(users)
            credits = round(random.uniform(2.0, 15.0), 1)

            transaction = {
                "id": f"txn_{i + 1}_{customer_id}",
                "credits": credits,
                "transaction_type": "inbound",
                "source": "platform_payment",
                "created_at": date.isoformat() + "Z",
                "metadata": {
                    "service_name": service,
                    "operation": operation,
                    "user_id": user,
                    "original_credits": round(credits / 0.7, 1),  # Assuming 70% revenue share
                },
                "status": "settled",
            }
            transactions.append(transaction)

        # Add some payout transactions
        payout_date = datetime.now() - timedelta(days=5)
        transactions.append(
            {
                "id": f"payout_1_{customer_id}",
                "credits": -50.0,
                "transaction_type": "outbound",
                "source": "payout_withdrawal",
                "created_at": payout_date.isoformat() + "Z",
                "metadata": {"payout_method": "paypal", "payout_id": f"payout_{customer_id}_123"},
                "status": "settled",
            }
        )

        # Sort by date (newest first)
        transactions.sort(key=lambda x: x["created_at"], reverse=True)  # type: ignore[arg-type,return-value]

        return transactions

    # ============================================================================
    # Mock Enterprise Features (Interface consistent with real client)
    # ============================================================================

    async def create_invoice(self, customer_id: str, currency: str = "USD") -> BillingResult:
        """Mock invoice creation"""
        logger.info(f"Mock: Created invoice for {customer_id}")
        return BillingResult(
            success=True,
            message="Mock invoice created",
            data={
                "id": f"invoice_{customer_id}_{datetime.now().strftime('%Y%m%d')}",
                "invoice_number": f"INV-{customer_id}-001",
                "status": "finalized",
                "amount_cents": 10000,  # $100
                "currency": currency,
                "customer_id": customer_id,
            },
        )

    async def get_invoices(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Mock get invoices"""
        # Generate mock invoices
        invoices = []
        for i in range(min(3, limit)):  # Generate 3 mock invoices
            date = datetime.now() - timedelta(days=30 * i)
            invoice = {
                "id": f"invoice_{customer_id}_{i + 1}",
                "invoice_number": f"INV-{customer_id}-{i + 1:03d}",
                "status": "paid" if i > 0 else "pending",
                "amount_cents": 10000 + (i * 2000),
                "currency": "USD",
                "issued_at": date.isoformat() + "Z",
                "payment_due_date": (date + timedelta(days=30)).isoformat() + "Z",
                "customer_id": customer_id,
            }
            invoices.append(invoice)

        return invoices

    async def get_invoice_pdf(self, invoice_id: str) -> bytes | None:
        """Mock PDF generation"""
        logger.info(f"Mock: PDF requested for invoice {invoice_id}")
        return b"Mock PDF content"

    async def create_billable_metric(self, metric_data: dict[str, Any]) -> BillingResult:
        """Mock billable metric creation"""
        logger.info(f"Mock: Created billable metric {metric_data.get('code', 'unknown')}")
        return BillingResult(
            success=True,
            message="Mock billable metric created",
            data={
                "id": f"metric_{metric_data.get('code', 'unknown')}",
                "code": metric_data.get("code", "api_calls"),
                "name": metric_data.get("name", "API Calls"),
                "aggregation_type": metric_data.get("aggregation_type", "count_agg"),
            },
        )

    async def get_billable_metrics(self) -> list[dict[str, Any]]:
        """Mock get billable metrics"""
        return [
            {
                "id": "metric_api_calls",
                "code": "api_calls",
                "name": "API Calls",
                "description": "Number of API calls made",
                "aggregation_type": "count_agg",
                "field_name": "calls",
            },
            {
                "id": "metric_storage",
                "code": "storage_gb",
                "name": "Storage Usage",
                "description": "Storage usage in GB",
                "aggregation_type": "sum_agg",
                "field_name": "storage_gb",
            },
        ]

    async def create_coupon(self, coupon_data: dict[str, Any]) -> BillingResult:
        """Mock coupon creation"""
        logger.info(f"Mock: Created coupon {coupon_data.get('code', 'unknown')}")
        return BillingResult(
            success=True,
            message="Mock coupon created",
            data={
                "id": f"coupon_{coupon_data.get('code', 'unknown')}",
                "code": coupon_data.get("code", "WELCOME10"),
                "name": coupon_data.get("name", "Welcome Discount"),
                "coupon_type": coupon_data.get("coupon_type", "percentage"),
                "percentage_rate": coupon_data.get("percentage_rate", 10.0),
            },
        )

    async def apply_coupon(self, customer_id: str, coupon_code: str) -> BillingResult:
        """Mock coupon application"""
        logger.info(f"Mock: Applied coupon {coupon_code} to {customer_id}")
        return BillingResult(
            success=True,
            message="Mock coupon applied",
            data={
                "customer_id": customer_id,
                "coupon_code": coupon_code,
                "discount_amount": 10.0,
                "applied_at": datetime.now().isoformat(),
            },
        )

    async def get_coupons(self) -> list[dict[str, Any]]:
        """Mock get coupons"""
        return [
            {
                "id": "coupon_welcome10",
                "code": "WELCOME10",
                "name": "Welcome Discount",
                "description": "10% off for new customers",
                "coupon_type": "percentage",
                "amount_cents": 0,
                "percentage_rate": 10.0,
                "frequency": "once",
                "status": "active",
            },
            {
                "id": "coupon_save20",
                "code": "SAVE20",
                "name": "Save $20",
                "description": "$20 off your next bill",
                "coupon_type": "fixed_amount",
                "amount_cents": 2000,
                "percentage_rate": 0,
                "frequency": "once",
                "status": "active",
            },
        ]

    async def create_webhook_endpoint(self, webhook_data: dict[str, Any]) -> BillingResult:
        """Mock webhook endpoint creation"""
        logger.info(f"Mock: Created webhook endpoint {webhook_data.get('webhook_url', 'unknown')}")
        return BillingResult(
            success=True,
            message="Mock webhook endpoint created",
            data={
                "id": f"webhook_{hash(webhook_data.get('webhook_url', ''))}",
                "webhook_url": webhook_data.get("webhook_url"),
                "signature_algo": webhook_data.get("signature_algo", "jwt"),
                "created_at": datetime.now().isoformat(),
            },
        )

    async def get_webhook_endpoints(self) -> list[dict[str, Any]]:
        """Mock get webhook endpoints"""
        return [
            {
                "id": "webhook_123",
                "webhook_url": "https://example.com/webhooks/lago",
                "signature_algo": "jwt",
                "created_at": datetime.now().isoformat(),
            }
        ]

    async def get_mrr_analytics(self, currency: str = "USD") -> dict[str, Any]:
        """Mock MRR analytics"""
        # Generate realistic MRR data
        total_mrr = random.uniform(50000, 100000)  # $50k-$100k MRR

        return {
            "total_mrr": total_mrr,
            "currency": currency,
            "data_points": 12,  # 12 months of data
            "raw_data": [
                {"month": f"2024-{i + 1:02d}", "amount_cents": int(total_mrr * 100 * random.uniform(0.8, 1.2))}
                for i in range(12)
            ],
        }

    async def get_gross_revenue_analytics(self, currency: str = "USD") -> dict[str, Any]:
        """Mock gross revenue analytics"""
        # Generate realistic revenue data
        total_revenue = random.uniform(500000, 1000000)  # $500k-$1M total revenue

        return {
            "total_gross_revenue": total_revenue,
            "currency": currency,
            "data_points": 12,
            "raw_data": [
                {"month": f"2024-{i + 1:02d}", "amount_cents": int(total_revenue * 100 * random.uniform(0.05, 0.15))}
                for i in range(12)
            ],
        }


# ============================================================================
# Lago Provider Implementation
# ============================================================================


# ============================================================================
# Factory Functions
# ============================================================================


def create_lago_client(
    api_key: str, api_url: str = "https://api.lago.dev", mock: bool = False
) -> LagoBillingClient | MockLagoBillingClient:
    """
    Create Lago client for use with BillingManager.

    Args:
        api_key: Lago API key
        api_url: Lago API URL
        mock: Use mock client for testing

    Returns:
        LagoBillingClient or MockLagoBillingClient instance
    """
    if mock:
        return MockLagoBillingClient(api_key=api_key, api_url=api_url)
    else:
        return LagoBillingClient(api_key=api_key, api_url=api_url)
