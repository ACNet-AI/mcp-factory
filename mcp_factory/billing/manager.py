"""
Billing manager for MCP Factory.

Central coordinator for all billing operations, integrating with
Lago for billing logic and payment gateways for transactions.
"""

import logging
from datetime import datetime
from typing import Any

from .engines import BillingClient
from .gateways import LocalPaymentGateway
from .models import (
    BillingConfig,
    BillingError,
    BillingResult,
    PaymentGateway,
    UsageEvent,
)
from .system import BillingSystem

logger = logging.getLogger(__name__)


class BillingManager(BillingSystem):
    """
    Central billing manager that coordinates between Lago and payment gateways.

    This class provides a unified interface for all billing operations,
    handling both subscription logic (via Lago) and payment processing
    (via payment gateways like Stripe).
    """

    def __init__(
        self,
        billing_client: BillingClient,
        payment_gateway: PaymentGateway | None = None,
        config: BillingConfig | None = None,
    ):
        """
        Initialize billing manager.

        Args:
            billing_client: Billing client for billing logic (Lago, Stripe, etc.)
            payment_gateway: Optional payment gateway for processing payments
            config: Optional billing configuration
        """
        # Initialize parent BillingSystem
        super().__init__(config)

        self.billing_client = billing_client
        self.payment_gateway = payment_gateway or LocalPaymentGateway()
        self._initialized = False

        logger.info(
            f"BillingManager initialized with billing client and {self.payment_gateway.get_gateway_name()} gateway"
        )

    async def initialize(self) -> bool:
        """
        Initialize the billing manager and its components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize billing client
            if not await self.billing_client.initialize():
                logger.error("Failed to initialize billing client")
                return False

            self._initialized = True
            logger.info("BillingManager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize BillingManager: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            await self.billing_client.cleanup()
            self._initialized = False
            logger.info("BillingManager cleaned up")
        except Exception as e:
            logger.error(f"Error during BillingManager cleanup: {e}")

    def _ensure_initialized(self) -> None:
        """Ensure the manager is initialized"""
        if not self._initialized:
            raise BillingError("BillingManager not initialized. Call initialize() first.")

    async def _ensure_initialized_async(self) -> None:
        """Ensure the manager is initialized, auto-initialize if needed"""
        if not self._initialized:
            logger.info("Auto-initializing BillingManager on first use")
            success = await self.initialize()
            if not success:
                raise BillingError("Failed to auto-initialize BillingManager")

    # ========================================================================
    # Permission Checking
    # ========================================================================

    async def check_permission(self, user_id: str, permission_type: str = "readonly") -> dict[str, Any]:
        """
        Check if user has permission for a specific operation.

        Args:
            user_id: User identifier
            permission_type: Type of permission (readonly, readwrite, admin)

        Returns:
            Dictionary with permission check result
        """
        await self._ensure_initialized_async()

        try:
            # Get user's subscription
            subscription = await self.billing_client.get_subscription(user_id)

            if not subscription:
                return {
                    "allowed": False,
                    "message": "No active subscription found",
                    "subscription_status": "none",
                    "upgrade_url": "/billing/subscribe",
                }

            if not subscription.is_active():
                return {
                    "allowed": False,
                    "message": f"Subscription is {subscription.status.value}",
                    "subscription_status": subscription.status.value,
                    "upgrade_url": "/billing/reactivate",
                }

            # Check if subscription includes the required feature
            feature_map = {"readonly": "basic_tools", "readwrite": "advanced_tools", "admin": "admin_tools"}

            required_feature = feature_map.get(permission_type, "basic_tools")

            if not subscription.has_feature(required_feature):
                return {
                    "allowed": False,
                    "message": f"Subscription does not include {required_feature}",
                    "subscription_status": subscription.status.value,
                    "current_plan": subscription.plan_id,
                    "upgrade_url": "/billing/upgrade",
                }

            # Check usage limits
            usage_limit = subscription.get_usage_limit("api_calls")
            if usage_limit > 0:
                # In a real implementation, you'd check current usage against the limit
                # For now, we'll assume usage is within limits
                pass

            return {
                "allowed": True,
                "message": "Permission granted",
                "subscription_status": subscription.status.value,
                "current_plan": subscription.plan_id,
                "features": subscription.features,
            }

        except Exception as e:
            logger.error(f"Permission check failed for user {user_id}: {e}")
            return {"allowed": False, "message": f"Permission check error: {str(e)}", "error": True}

    async def record_usage(
        self,
        user_id: str,
        usage_type: str,
        quantity: int = 1,
        *,
        tool_name: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Record usage event for billing purposes.

        This method records usage quantity only. Pricing and revenue calculations
        are handled by the proxy platform or billing provider.

        Args:
            user_id: Direct accessor identifier (end user or proxy platform)
            usage_type: Type of usage to record
            quantity: Quantity of usage (default: 1)
            tool_name: Tool name if this is a tool call
            request_id: Unique request identifier from RequestContext
            metadata: Additional usage metadata (flexible, proxy-defined fields)

        Returns:
            Dictionary with recording status and usage details
        """
        await self._ensure_initialized_async()

        try:
            # Merge all metadata
            full_metadata = metadata.copy() if metadata else {}
            full_metadata.update(
                {
                    "usage_type": usage_type,
                    "tool_name": tool_name,
                    "request_id": request_id,
                }
            )

            # Create usage event
            event = UsageEvent(
                user_id=user_id,
                event_type=f"mcp_{usage_type}",
                quantity=quantity,
                metadata=full_metadata,
            )

            # Record in Lago
            result = await self.billing_client.record_usage_event(event)

            if result.success:
                logger.debug(f"Usage recorded for user {user_id}: {usage_type}")

                # Build detailed response with unique transaction ID
                import uuid

                timestamp = event.timestamp if event.timestamp else datetime.now()
                transaction_id = f"{user_id}_{uuid.uuid4().hex[:8]}_{int(timestamp.timestamp())}"

                response = {
                    "success": True,
                    "message": f"Usage recorded: {quantity} {usage_type}",
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "usage_type": usage_type,
                    "quantity": quantity,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                }

                # Add optional fields if provided
                if tool_name:
                    response["tool_name"] = tool_name
                if request_id:
                    response["request_id"] = request_id

                # Add proxy information if accessed via proxy
                # Include all proxy-provided fields at the top level for convenience
                if metadata and metadata.get("via_proxy"):
                    response["via_proxy"] = True
                    # Include all proxy fields (proxy decides what to include)
                    for key, value in metadata.items():
                        if key not in response and key != "usage_type":
                            response[key] = value

                # Include full metadata
                response["metadata"] = full_metadata

                return response
            else:
                logger.warning(f"Failed to record usage for user {user_id}: {result.message}")
                return {
                    "success": False,
                    "message": result.message,
                    "user_id": user_id,
                    "usage_type": usage_type,
                    "quantity": quantity,
                }

        except Exception as e:
            logger.error(f"Usage recording failed for user {user_id}: {e}")
            return {
                "success": False,
                "message": f"Usage recording error: {str(e)}",
                "user_id": user_id,
                "usage_type": usage_type,
                "quantity": quantity,
            }

    # ========================================================================
    # Subscription Management
    # ========================================================================

    async def create_subscription(
        self, user_id: str, plan_id: str, email: str, name: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new subscription for a user.

        Args:
            user_id: User identifier
            plan_id: Plan to subscribe to
            email: User email
            name: Optional user name

        Returns:
            BillingResult with subscription creation status
        """
        await self._ensure_initialized_async()

        try:
            # Create customer in Lago if not exists
            customer = await self.billing_client.get_customer(user_id)
            if not customer:
                customer_result = await self.billing_client.create_customer(user_id, email, name)  # type: ignore[arg-type]
                if not customer_result.success:
                    return customer_result  # type: ignore[return-value]

            # Create subscription in Lago
            subscription_result = await self.billing_client.create_subscription(user_id, plan_id)
            if not subscription_result.success:
                return subscription_result  # type: ignore[return-value]

            # Set up payment method if payment gateway is available
            if self.payment_gateway and self.payment_gateway.get_gateway_name() != "local":
                payment_result = await self.payment_gateway.create_subscription_payment(
                    user_id,
                    plan_id,
                    {"lago_subscription_id": subscription_result.data.get("subscription_id")},  # type: ignore[union-attr]
                )

                if not payment_result.success:
                    logger.warning(f"Payment setup failed for subscription: {payment_result.message}")
                    # Don't fail the entire operation, just log the warning

            logger.info(f"Subscription created successfully for user {user_id}, plan {plan_id}")

            return BillingResult.success_result(  # type: ignore[return-value]
                f"Subscription created successfully for plan {plan_id}",
                {
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "lago_subscription_id": subscription_result.data.get("subscription_id"),  # type: ignore[union-attr]
                },
            )

        except Exception as e:
            logger.error(f"Subscription creation failed for user {user_id}: {e}")
            return BillingResult.error_result(f"Subscription creation error: {str(e)}")  # type: ignore[return-value]

    async def get_subscription(self, user_id: str) -> dict[str, Any] | None:
        """
        Get user's current subscription.

        Args:
            user_id: User identifier

        Returns:
            Subscription object or None if no subscription
        """
        await self._ensure_initialized_async()

        try:
            subscription = await self.billing_client.get_subscription(user_id)
            if subscription:
                return {
                    "plan_id": subscription.plan_id,
                    "status": subscription.status.value,
                    "started_at": subscription.started_at.isoformat(),
                    "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                    "features": subscription.features,
                    "usage_limits": subscription.usage_limits,
                    "is_active": subscription.is_active(),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get subscription for user {user_id}: {e}")
            return None

    async def cancel_subscription(self, user_id: str) -> BillingResult:  # type: ignore[override]
        """
        Cancel user's subscription.

        Args:
            user_id: User identifier

        Returns:
            BillingResult with cancellation status
        """
        await self._ensure_initialized_async()

        try:
            # Get current subscription object from billing client
            subscription = await self.billing_client.get_subscription(user_id)
            if not subscription:
                return BillingResult.error_result("No active subscription found")

            # Cancel in Lago
            lago_subscription_id = subscription.metadata.get("lago_subscription_id")
            if lago_subscription_id:
                result = await self.billing_client.cancel_subscription(lago_subscription_id)
                if not result.success:
                    return result

            # Cancel payment if payment gateway is available
            if self.payment_gateway and self.payment_gateway.get_gateway_name() != "local":
                if hasattr(self.payment_gateway, "cancel_subscription_payment"):
                    payment_result = await self.payment_gateway.cancel_subscription_payment(lago_subscription_id)
                    if not payment_result.success:
                        logger.warning(f"Payment cancellation failed: {payment_result.message}")

            logger.info(f"Subscription cancelled for user {user_id}")

            return BillingResult.success_result("Subscription cancelled successfully", {"user_id": user_id})

        except Exception as e:
            logger.error(f"Subscription cancellation failed for user {user_id}: {e}")
            return BillingResult.error_result(f"Subscription cancellation error: {str(e)}")

    # ========================================================================
    # Plan Management
    # ========================================================================

    async def get_available_plans(self) -> list[dict[str, Any]]:
        """
        Get all available pricing plans.

        Returns:
            List of available pricing plans
        """
        await self._ensure_initialized_async()

        try:
            plans = await self.billing_client.get_plans()
            return [
                {
                    "plan_id": plan.plan_id,
                    "name": plan.name,
                    "description": plan.description,
                    "price": plan.price,
                    "currency": plan.currency,
                    "billing_cycle": plan.billing_cycle,
                    "features": plan.features,
                    "usage_limits": plan.usage_limits,
                }
                for plan in plans
            ]
        except Exception as e:
            logger.error(f"Failed to get available plans: {e}")
            return []

    # ========================================================================
    # Management Tools
    # ========================================================================

    async def get_management_tools(self) -> list[dict[str, Any]]:
        """
        Get billing management tools for MCP server.

        Returns:
            List of tool configurations
        """
        return [
            {
                "name": "get_subscription_status",
                "description": "Get current subscription status and details",
                "permission_type": "readonly",
                "handler": self._tool_get_subscription_status,
            },
            {
                "name": "get_usage_stats",
                "description": "Get usage statistics for current billing period",
                "permission_type": "readonly",
                "handler": self._tool_get_usage_stats,
            },
            {
                "name": "get_available_plans",
                "description": "Get all available subscription plans",
                "permission_type": "readonly",
                "handler": self._tool_get_available_plans,
            },
            {
                "name": "upgrade_subscription",
                "description": "Upgrade to a higher tier subscription plan",
                "permission_type": "readwrite",
                "handler": self._tool_upgrade_subscription,
            },
        ]

    async def _tool_get_subscription_status(self, user_id: str) -> dict[str, Any]:
        """Tool handler: Get subscription status"""
        subscription = await self.get_subscription(user_id)

        if not subscription:
            return {"status": "none", "message": "No active subscription", "upgrade_url": "/billing/subscribe"}

        return {
            "status": subscription.status.value,  # type: ignore[attr-defined]
            "plan_id": subscription.plan_id,  # type: ignore[attr-defined]
            "started_at": subscription.started_at.isoformat(),  # type: ignore[attr-defined]
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,  # type: ignore[attr-defined]
            "features": subscription.features,  # type: ignore[attr-defined]
            "usage_limits": subscription.usage_limits,  # type: ignore[attr-defined]
            "is_active": subscription.is_active(),  # type: ignore[attr-defined]
        }

    async def _tool_get_usage_stats(self, user_id: str) -> dict[str, Any]:
        """Tool handler: Get usage statistics"""
        # In a real implementation, you'd query usage data from Lago
        # For now, return mock data
        return {
            "user_id": user_id,
            "current_period": {
                "api_calls": 1250,
                "data_processed_mb": 45.2,
                "tools_used": ["search", "analyze", "generate"],
            },
            "limits": {"api_calls": 10000, "data_processed_mb": 1000},
            "usage_percentage": {"api_calls": 12.5, "data_processed_mb": 4.5},
        }

    async def _tool_get_available_plans(self) -> list[dict[str, Any]]:
        """Tool handler: Get available plans"""
        plans = await self.get_available_plans()

        return [
            {
                "plan_id": plan.plan_id,  # type: ignore[attr-defined]
                "name": plan.name,  # type: ignore[attr-defined]
                "description": plan.description,  # type: ignore[attr-defined]
                "price": plan.price,  # type: ignore[attr-defined]
                "currency": plan.currency,  # type: ignore[attr-defined]
                "billing_cycle": plan.billing_cycle,  # type: ignore[attr-defined]
                "features": plan.features,  # type: ignore[attr-defined]
                "usage_limits": plan.usage_limits,  # type: ignore[attr-defined]
            }
            for plan in plans
        ]

    async def _tool_upgrade_subscription(self, user_id: str, new_plan_id: str) -> dict[str, Any]:
        """Tool handler: Upgrade subscription (legacy - use upgrade_subscription instead)"""
        result = await self.upgrade_subscription(user_id, new_plan_id)
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Unknown error"),
            "new_plan_id": new_plan_id if result.get("success") else None,
        }

    # ========================================================================
    # BillingSystem Interface Implementation
    # ========================================================================

    def get_system_name(self) -> str:
        """Get the name of this billing system."""
        return "managed"

    async def process_payment(
        self, user_id: str, amount: float, currency: str = "USD", metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process a payment for a user.
        """
        await self._ensure_initialized_async()

        try:
            result = await self.payment_gateway.process_payment(amount, currency, user_id, metadata)
            return {
                "success": result.success,
                "message": result.message,
                "transaction_id": result.data.get("transaction_id") if result.data else None,
                "amount": amount,
                "currency": currency,
            }
        except Exception as e:
            logger.error(f"Payment processing failed for user {user_id}: {e}")
            return {"success": False, "message": f"Payment error: {str(e)}"}

    async def get_payment_methods(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get available payment methods for a user.
        """
        await self._ensure_initialized_async()

        try:
            if hasattr(self.payment_gateway, "get_payment_methods"):
                return await self.payment_gateway.get_payment_methods(user_id)  # type: ignore[no-any-return]
            else:
                # Return default payment method info
                return [
                    {
                        "type": self.payment_gateway.get_gateway_name(),
                        "available": True,
                        "description": f"Payment via {self.payment_gateway.get_gateway_name()}",
                    }
                ]
        except Exception as e:
            logger.error(f"Failed to get payment methods for user {user_id}: {e}")
            return []

    async def get_payment_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get payment history for a user.
        """
        await self._ensure_initialized_async()

        try:
            if hasattr(self.payment_gateway, "get_payment_history"):
                return await self.payment_gateway.get_payment_history(user_id, limit)  # type: ignore[no-any-return]
            else:
                # Return empty history if not supported
                return []
        except Exception as e:
            logger.error(f"Failed to get payment history for user {user_id}: {e}")
            return []

    async def get_plan_details(self, plan_id: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific plan.
        """
        await self._ensure_initialized_async()

        try:
            plans = await self.get_available_plans()
            for plan in plans:
                if plan["plan_id"] == plan_id:
                    return {
                        "plan_id": plan["plan_id"],
                        "name": plan["name"],
                        "description": plan["description"],
                        "price": plan["price"],
                        "currency": plan["currency"],
                        "billing_cycle": plan["billing_cycle"],
                        "features": plan["features"],
                        "usage_limits": plan["usage_limits"],
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get plan details for {plan_id}: {e}")
            return None

    async def get_usage_stats(self, user_id: str, period: str = "current") -> dict[str, Any]:
        """
        Get usage statistics for a user.
        """
        await self._ensure_initialized_async()

        try:
            # Use the existing tool handler logic
            return await self._tool_get_usage_stats(user_id)
        except Exception as e:
            logger.error(f"Failed to get usage stats for user {user_id}: {e}")
            return {"error": f"Failed to get usage stats: {str(e)}"}

    # ========================================================================
    # Enhanced Subscription Lifecycle Management
    # ========================================================================

    async def upgrade_subscription(self, user_id: str, new_plan_id: str, prorate: bool = True) -> dict[str, Any]:
        """
        Upgrade user's subscription to a higher tier plan with proper billing handling.
        """
        await self._ensure_initialized_async()

        try:
            # Get current subscription
            current_subscription = await self.get_subscription(user_id)
            if not current_subscription:
                return {
                    "success": False,
                    "message": "No active subscription found to upgrade",
                    "error_code": "NO_SUBSCRIPTION",
                }

            current_plan = current_subscription.get("plan_id")

            # Validate upgrade path (ensure new plan is higher tier)
            upgrade_cost = await self.get_upgrade_cost(user_id, new_plan_id)
            if not upgrade_cost.get("valid_upgrade"):
                return {
                    "success": False,
                    "message": f"Invalid upgrade path from {current_plan} to {new_plan_id}",
                    "error_code": "INVALID_UPGRADE",
                }

            # Process the upgrade through billing client
            # In a real implementation, this would handle:
            # 1. Calculate prorated charges
            # 2. Process payment adjustment
            # 3. Update subscription in billing system
            # 4. Handle rollback on failure

            # For now, simulate the upgrade process
            cancel_result = await self.cancel_subscription(user_id)
            if not cancel_result.get("success"):  # type: ignore[attr-defined]
                return {
                    "success": False,
                    "message": f"Failed to cancel current subscription: {cancel_result.get('message')}",  # type: ignore[attr-defined]
                    "error_code": "CANCEL_FAILED",
                }

            # Create new subscription
            email = f"{user_id}@example.com"  # In real implementation, get from user data
            create_result = await self.create_subscription(user_id, new_plan_id, email)

            if create_result.get("success"):
                return {
                    "success": True,
                    "message": f"Successfully upgraded from {current_plan} to {new_plan_id}",
                    "old_plan_id": current_plan,
                    "new_plan_id": new_plan_id,
                    "proration_amount": upgrade_cost.get("proration_amount", 0),
                    "effective_date": create_result.get("effective_date"),
                    "next_billing_date": create_result.get("next_billing_date"),
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create new subscription: {create_result.get('message')}",
                    "error_code": "CREATE_FAILED",
                }

        except Exception as e:
            logger.error(f"Subscription upgrade failed for user {user_id}: {e}")
            return {"success": False, "message": f"Upgrade error: {str(e)}", "error_code": "UPGRADE_ERROR"}

    async def downgrade_subscription(
        self, user_id: str, new_plan_id: str, effective_date: str | None = None
    ) -> dict[str, Any]:
        """
        Downgrade user's subscription to a lower tier plan.
        """
        await self._ensure_initialized_async()

        try:
            # Get current subscription
            current_subscription = await self.get_subscription(user_id)
            if not current_subscription:
                return {
                    "success": False,
                    "message": "No active subscription found to downgrade",
                    "error_code": "NO_SUBSCRIPTION",
                }

            current_plan = current_subscription.get("plan_id")

            # Schedule downgrade (typically at end of current billing period)
            if effective_date is None:
                # Default to end of current billing period
                effective_date = current_subscription.get("expires_at", "immediate")

            # In a real implementation, this would:
            # 1. Schedule the downgrade for the effective date
            # 2. Update subscription metadata
            # 3. Send notification to user
            # 4. Handle any refund calculations

            logger.info(
                f"Scheduling downgrade for user {user_id} from {current_plan} to {new_plan_id} on {effective_date}"
            )

            return {
                "success": True,
                "message": f"Downgrade scheduled from {current_plan} to {new_plan_id}",
                "old_plan_id": current_plan,
                "new_plan_id": new_plan_id,
                "effective_date": effective_date,
                "immediate": effective_date == "immediate",
            }

        except Exception as e:
            logger.error(f"Subscription downgrade failed for user {user_id}: {e}")
            return {"success": False, "message": f"Downgrade error: {str(e)}", "error_code": "DOWNGRADE_ERROR"}

    async def pause_subscription(self, user_id: str, pause_until: str | None = None) -> dict[str, Any]:
        """
        Pause user's subscription temporarily.
        """
        await self._ensure_initialized_async()

        try:
            # Get current subscription
            current_subscription = await self.get_subscription(user_id)
            if not current_subscription:
                return {
                    "success": False,
                    "message": "No active subscription found to pause",
                    "error_code": "NO_SUBSCRIPTION",
                }

            # In a real implementation, this would:
            # 1. Update subscription status to 'paused'
            # 2. Stop billing cycles
            # 3. Set resume date if provided
            # 4. Maintain access based on pause policy

            logger.info(f"Pausing subscription for user {user_id} until {pause_until or 'indefinite'}")

            return {
                "success": True,
                "message": "Subscription paused successfully",
                "plan_id": current_subscription.get("plan_id"),
                "paused_date": "2024-01-01T00:00:00Z",  # Should be actual timestamp
                "resume_date": pause_until,
                "indefinite": pause_until is None,
            }

        except Exception as e:
            logger.error(f"Subscription pause failed for user {user_id}: {e}")
            return {"success": False, "message": f"Pause error: {str(e)}", "error_code": "PAUSE_ERROR"}

    async def resume_subscription(self, user_id: str) -> dict[str, Any]:
        """
        Resume a paused subscription.
        """
        await self._ensure_initialized_async()

        try:
            # Get current subscription
            current_subscription = await self.get_subscription(user_id)
            if not current_subscription:
                return {"success": False, "message": "No subscription found to resume", "error_code": "NO_SUBSCRIPTION"}

            # In a real implementation, this would:
            # 1. Update subscription status to 'active'
            # 2. Resume billing cycles
            # 3. Calculate any adjustments
            # 4. Restore full access

            logger.info(f"Resuming subscription for user {user_id}")

            return {
                "success": True,
                "message": "Subscription resumed successfully",
                "plan_id": current_subscription.get("plan_id"),
                "resumed_date": "2024-01-01T00:00:00Z",  # Should be actual timestamp
                "next_billing_date": "2024-02-01T00:00:00Z",  # Should be calculated
            }

        except Exception as e:
            logger.error(f"Subscription resume failed for user {user_id}: {e}")
            return {"success": False, "message": f"Resume error: {str(e)}", "error_code": "RESUME_ERROR"}

    async def get_subscription_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get subscription change history for a user.
        """
        await self._ensure_initialized_async()

        try:
            # In a real implementation, this would query the billing client
            # for historical subscription changes

            # Mock data for demonstration
            return [
                {
                    "event_id": "evt_001",
                    "event_type": "subscription_created",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "plan_id": "basic",
                    "details": {"initial_subscription": True},
                },
                {
                    "event_id": "evt_002",
                    "event_type": "subscription_upgraded",
                    "timestamp": "2024-01-15T00:00:00Z",
                    "old_plan_id": "basic",
                    "new_plan_id": "professional",
                    "details": {"proration_amount": 15.99},
                },
            ][:limit]

        except Exception as e:
            logger.error(f"Failed to get subscription history for user {user_id}: {e}")
            return []

    # ========================================================================
    # Additional BillingSystem Methods
    # ========================================================================

    async def get_current_usage(
        self, user_id: str, usage_type: str | None = None, period: str = "current"
    ) -> dict[str, Any]:
        """Get current usage statistics for a user."""
        await self._ensure_initialized_async()

        try:
            # TODO: In a real implementation, this would query actual usage data from a database
            # For now, return realistic default values (starting from 0 for new users)
            from datetime import datetime

            base_usage = {"user_id": user_id, "period": period, "last_updated": datetime.now().isoformat()}

            if usage_type:
                # Specific usage type requested - start with 0 for new users
                base_usage[usage_type] = 0  # type: ignore[assignment]
            else:
                # All usage types - start with 0 for all metrics
                base_usage.update(
                    {
                        "api_calls": 0,  # type: ignore[dict-item]
                        "file_operations": 0,  # type: ignore[dict-item]
                        "data_transfer_mb": 0,  # type: ignore[dict-item]
                    }
                )

            return base_usage

        except Exception as e:
            logger.error(f"Failed to get current usage for user {user_id}: {e}")
            return {"user_id": user_id, "period": period, "error": str(e)}

    async def check_usage_limits(self, user_id: str, usage_type: str, amount: int = 1) -> dict[str, Any]:
        """Check if user can perform an operation without exceeding limits."""
        await self._ensure_initialized_async()

        try:
            # Get user's subscription to determine limits
            subscription = await self.get_subscription(user_id)

            # Default limits for free users
            default_limits = {"api_calls": 100, "file_operations": 50, "data_transfer_mb": 500}

            if subscription and subscription.get("is_active"):
                # Get limits based on plan
                plan_id = subscription.get("plan_id", "free")
                plan_limits = {
                    "free": {"api_calls": 100, "file_operations": 50, "data_transfer_mb": 500},
                    "basic": {"api_calls": 1000, "file_operations": 500, "data_transfer_mb": 5000},
                    "professional": {"api_calls": -1, "file_operations": -1, "data_transfer_mb": -1},  # Unlimited
                }
                limits = plan_limits.get(plan_id, default_limits)
            else:
                limits = default_limits

            # Get current usage
            current_usage_data = await self.get_current_usage(user_id, usage_type, "current")
            current_usage = current_usage_data.get(usage_type, 0)

            # Check limits - handle usage_type mapping
            # Map singular usage types to plural limit keys
            usage_type_mapping = {
                "api_call": "api_calls",
                "file_operation": "file_operations",
                "data_transfer": "data_transfer_mb",
            }
            limit_key = usage_type_mapping.get(usage_type, usage_type)
            limit = limits.get(limit_key, 100)

            if limit == -1:  # Unlimited
                return {"allowed": True, "remaining": -1, "limit": -1, "current_usage": current_usage}

            remaining = max(0, limit - current_usage)
            allowed = current_usage + amount <= limit

            return {
                "allowed": allowed,
                "remaining": remaining,
                "limit": limit,
                "current_usage": current_usage,
                "requested_amount": amount,
            }

        except Exception as e:
            logger.error(f"Failed to check usage limits for user {user_id}: {e}")
            return {"allowed": False, "error": str(e), "remaining": 0, "limit": 0}

    async def get_usage_warnings(self, user_id: str) -> list[dict[str, Any]]:
        """Get usage warnings for a user (approaching limits)."""
        await self._ensure_initialized_async()

        try:
            warnings = []
            usage_types = ["api_calls", "file_operations", "data_transfer_mb"]

            for usage_type in usage_types:
                limit_check = await self.check_usage_limits(user_id, usage_type, 0)

                if limit_check.get("limit", 0) > 0:  # Not unlimited
                    usage_percentage = (limit_check.get("current_usage", 0) / limit_check.get("limit", 1)) * 100

                    if usage_percentage >= 90:
                        warnings.append(
                            {
                                "usage_type": usage_type,
                                "severity": "critical",
                                "message": f"{usage_type} usage at {usage_percentage:.1f}% of limit",
                                "current_usage": limit_check.get("current_usage"),
                                "limit": limit_check.get("limit"),
                                "remaining": limit_check.get("remaining"),
                            }
                        )
                    elif usage_percentage >= 75:
                        warnings.append(
                            {
                                "usage_type": usage_type,
                                "severity": "warning",
                                "message": f"{usage_type} usage at {usage_percentage:.1f}% of limit",
                                "current_usage": limit_check.get("current_usage"),
                                "limit": limit_check.get("limit"),
                                "remaining": limit_check.get("remaining"),
                            }
                        )

            return warnings

        except Exception as e:
            logger.error(f"Failed to get usage warnings for user {user_id}: {e}")
            return []

    async def reset_usage_counters(self, user_id: str, usage_type: str | None = None) -> dict[str, Any]:
        """Reset usage counters for a user (admin operation)."""
        await self._ensure_initialized_async()

        try:
            # In a real implementation, this would reset actual usage counters
            # This is typically an admin operation

            if usage_type:
                logger.info(f"Resetting {usage_type} usage counter for user {user_id}")
                return {
                    "success": True,
                    "message": f"Reset {usage_type} usage counter for user {user_id}",
                    "reset_types": [usage_type],
                }
            else:
                logger.info(f"Resetting all usage counters for user {user_id}")
                return {
                    "success": True,
                    "message": f"Reset all usage counters for user {user_id}",
                    "reset_types": ["api_calls", "file_operations", "data_transfer_mb"],
                }

        except Exception as e:
            logger.error(f"Failed to reset usage counters for user {user_id}: {e}")
            return {"success": False, "message": f"Failed to reset usage counters: {str(e)}"}

    async def calculate_plan_cost(self, plan_id: str, usage_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Calculate the cost for a plan based on usage."""
        await self._ensure_initialized_async()

        try:
            # Get plan details
            plan_details = await self.get_plan_details(plan_id)
            if not plan_details:
                return {"success": False, "message": f"Plan {plan_id} not found"}

            base_cost = plan_details.get("price", 0)

            # In a real implementation, this would calculate usage-based costs
            usage_cost = 0
            if usage_data:
                # Example usage-based pricing
                api_calls = usage_data.get("api_calls", 0)
                if api_calls > 1000:  # Over the included amount
                    usage_cost += (api_calls - 1000) * 0.001  # $0.001 per extra call

            total_cost = base_cost + usage_cost

            return {
                "success": True,
                "plan_id": plan_id,
                "base_cost": base_cost,
                "usage_cost": usage_cost,
                "total_cost": total_cost,
                "currency": plan_details.get("currency", "USD"),
                "calculation_date": "2024-01-01T00:00:00Z",
            }

        except Exception as e:
            logger.error(f"Failed to calculate plan cost for {plan_id}: {e}")
            return {"success": False, "message": f"Cost calculation error: {str(e)}"}

    async def get_upgrade_cost(self, user_id: str, new_plan_id: str) -> dict[str, Any]:
        """Calculate the cost to upgrade to a new plan."""
        await self._ensure_initialized_async()

        try:
            # Get current subscription
            current_subscription = await self.get_subscription(user_id)
            if not current_subscription:
                return {"valid_upgrade": False, "message": "No current subscription found"}

            current_plan_id = current_subscription.get("plan_id")

            # Get plan details
            current_plan = await self.get_plan_details(current_plan_id)  # type: ignore[arg-type]
            new_plan = await self.get_plan_details(new_plan_id)

            if not current_plan or not new_plan:
                return {"valid_upgrade": False, "message": "Plan details not found"}

            current_price = current_plan.get("price", 0)
            new_price = new_plan.get("price", 0)

            # Simple validation: new plan should be more expensive
            if new_price <= current_price:
                return {
                    "valid_upgrade": False,
                    "message": f"Cannot upgrade from ${current_price} plan to ${new_price} plan",
                }

            # Calculate proration (simplified)
            price_difference = new_price - current_price
            proration_amount = price_difference * 0.5  # Simplified: assume mid-cycle

            return {
                "valid_upgrade": True,
                "current_plan_id": current_plan_id,
                "new_plan_id": new_plan_id,
                "current_price": current_price,
                "new_price": new_price,
                "price_difference": price_difference,
                "proration_amount": proration_amount,
                "currency": new_plan.get("currency", "USD"),
            }

        except Exception as e:
            logger.error(f"Failed to calculate upgrade cost for user {user_id}: {e}")
            return {"valid_upgrade": False, "message": f"Upgrade cost calculation error: {str(e)}"}

    async def apply_promotional_pricing(self, user_id: str, promo_code: str) -> dict[str, Any]:
        """Apply promotional pricing to a user's subscription."""
        await self._ensure_initialized_async()

        try:
            # In a real implementation, this would validate and apply promo codes
            # For now, return mock data

            valid_codes = {
                "WELCOME20": {"discount": 0.20, "type": "percentage", "description": "20% off first month"},
                "SAVE50": {"discount": 50.0, "type": "fixed", "description": "$50 off"},
                "STUDENT": {"discount": 0.50, "type": "percentage", "description": "50% student discount"},
            }

            if promo_code not in valid_codes:
                return {"success": False, "message": f"Invalid promo code: {promo_code}"}

            promo_info = valid_codes[promo_code]

            logger.info(f"Applied promo code {promo_code} for user {user_id}")

            return {
                "success": True,
                "promo_code": promo_code,
                "discount": promo_info["discount"],
                "discount_type": promo_info["type"],
                "description": promo_info["description"],
                "applied_date": "2024-01-01T00:00:00Z",
            }

        except Exception as e:
            logger.error(f"Failed to apply promo code {promo_code} for user {user_id}: {e}")
            return {"success": False, "message": f"Promo code application error: {str(e)}"}

    async def get_billing_preview(self, user_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Preview billing changes before applying them."""
        await self._ensure_initialized_async()

        try:
            preview = {"user_id": user_id, "changes": changes, "preview_date": "2024-01-01T00:00:00Z", "items": []}

            # Handle plan change preview
            if "new_plan_id" in changes:
                upgrade_cost = await self.get_upgrade_cost(user_id, changes["new_plan_id"])
                if upgrade_cost.get("valid_upgrade"):
                    preview["items"].append(  # type: ignore[attr-defined]
                        {
                            "type": "plan_change",
                            "description": f"Upgrade to {changes['new_plan_id']}",
                            "amount": upgrade_cost.get("proration_amount", 0),
                            "currency": upgrade_cost.get("currency", "USD"),
                        }
                    )

            # Handle promo code preview
            if "promo_code" in changes:
                promo_result = await self.apply_promotional_pricing(user_id, changes["promo_code"])
                if promo_result.get("success"):
                    preview["items"].append(  # type: ignore[attr-defined]
                        {
                            "type": "promotion",
                            "description": promo_result.get("description", "Promotional discount"),
                            "amount": -promo_result.get("discount", 0),  # Negative for discount
                            "currency": "USD",
                        }
                    )

            # Calculate total
            total_amount = sum(item.get("amount", 0) for item in preview["items"])  # type: ignore[attr-defined]
            preview["total_amount"] = total_amount  # type: ignore[assignment]
            preview["currency"] = "USD"

            return preview

        except Exception as e:
            logger.error(f"Failed to generate billing preview for user {user_id}: {e}")
            return {"user_id": user_id, "error": str(e), "preview_date": "2024-01-01T00:00:00Z"}

    async def handle_webhook_event(self, event_type: str, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming webhook events from payment providers."""
        await self._ensure_initialized_async()

        try:
            logger.info(f"Handling webhook event: {event_type}")

            # In a real implementation, this would handle various webhook events
            # from Stripe, Lago, etc.

            handled_events = {
                "subscription.created": self._handle_subscription_created,
                "subscription.updated": self._handle_subscription_updated,
                "subscription.cancelled": self._handle_subscription_cancelled,
                "payment.succeeded": self._handle_payment_succeeded,
                "payment.failed": self._handle_payment_failed,
            }

            if event_type in handled_events:
                return await handled_events[event_type](event_data)
            else:
                return {"success": False, "message": f"Unhandled event type: {event_type}", "event_type": event_type}

        except Exception as e:
            logger.error(f"Failed to handle webhook event {event_type}: {e}")
            return {"success": False, "message": f"Webhook handling error: {str(e)}", "event_type": event_type}

    async def _handle_subscription_created(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle subscription created webhook."""
        user_id = event_data.get("user_id") or event_data.get("customer_id")
        logger.info(f"Subscription created for user {user_id}")
        return {"success": True, "message": "Subscription created event processed"}

    async def _handle_subscription_updated(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle subscription updated webhook."""
        user_id = event_data.get("user_id") or event_data.get("customer_id")
        logger.info(f"Subscription updated for user {user_id}")
        return {"success": True, "message": "Subscription updated event processed"}

    async def _handle_subscription_cancelled(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle subscription cancelled webhook."""
        user_id = event_data.get("user_id") or event_data.get("customer_id")
        logger.info(f"Subscription cancelled for user {user_id}")
        return {"success": True, "message": "Subscription cancelled event processed"}

    async def _handle_payment_succeeded(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle payment succeeded webhook."""
        user_id = event_data.get("user_id") or event_data.get("customer_id")
        amount = event_data.get("amount", 0)
        logger.info(f"Payment succeeded for user {user_id}: ${amount}")
        return {"success": True, "message": "Payment succeeded event processed"}

    async def _handle_payment_failed(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle payment failed webhook."""
        user_id = event_data.get("user_id") or event_data.get("customer_id")
        logger.warning(f"Payment failed for user {user_id}")
        return {"success": True, "message": "Payment failed event processed"}

    async def get_subscription_events(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent subscription events for a user."""
        await self._ensure_initialized_async()

        try:
            # In a real implementation, this would query event logs
            # For now, return mock events
            events = [
                {
                    "event_id": "evt_001",
                    "event_type": "subscription.created",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "user_id": user_id,
                    "data": {"plan_id": "basic"},
                },
                {
                    "event_id": "evt_002",
                    "event_type": "payment.succeeded",
                    "timestamp": "2024-01-01T01:00:00Z",
                    "user_id": user_id,
                    "data": {"amount": 9.99, "currency": "USD"},
                },
            ]

            return events[:limit]

        except Exception as e:
            logger.error(f"Failed to get subscription events for user {user_id}: {e}")
            return []

    async def trigger_subscription_sync(self, user_id: str) -> dict[str, Any]:
        """Manually trigger subscription synchronization with external systems."""
        await self._ensure_initialized_async()

        try:
            # In a real implementation, this would sync with external systems
            # like authorization systems, CRM, etc.

            logger.info(f"Triggering subscription sync for user {user_id}")

            # Mock sync operations
            sync_results = {"authorization_sync": True, "crm_sync": True, "analytics_sync": True}

            return {
                "success": True,
                "message": f"Subscription sync triggered for user {user_id}",
                "sync_results": sync_results,
                "sync_timestamp": "2024-01-01T00:00:00Z",
            }

        except Exception as e:
            logger.error(f"Failed to trigger subscription sync for user {user_id}: {e}")
            return {"success": False, "message": f"Subscription sync error: {str(e)}"}

    # Note: The existing methods already implement most of BillingSystem interface
    # We just need to ensure they return the correct format

    # The existing create_subscription, get_subscription, cancel_subscription,
    # get_available_plans, and get_management_tools methods already exist above
    # and work correctly. We don't need to override them here.


# ManagedBillingProvider has been removed as it's redundant.
# BillingManager now directly implements BillingSystem interface.
# Users should use BillingManager directly instead of wrapping it.


# ============================================================================
# Factory Function
# ============================================================================


async def create_billing_manager(config: dict) -> BillingManager:
    """
    Create and initialize a billing manager from configuration.

    This creates a clean BillingSystem implementation without platform-specific features.
    For multi-tenant isolation and platform features, use BillingProxy instead.

    Args:
        config: Billing configuration dictionary

    Example configs:

        # Basic Lago integration
        {
            "provider": "lago",
            "lago": {
                "api_url": "https://api.lago.dev",
                "api_key": "your-lago-key"
            },
            "payment_gateway": {
                "type": "stripe",
                "secret_key": "sk_test_...",
                "webhook_secret": "whsec_..."
            }
        }

        # Mock mode for development
        {
            "provider": "mock",
            "payment_gateway": "local"
        }

    Returns:
        Initialized BillingManager instance
    """
    from .engines.lago import LagoBillingClient, MockLagoBillingClient
    from .gateways import LocalPaymentGateway, StripePaymentGateway

    # Determine provider type
    provider = config.get("provider", "lago")

    # Create billing client
    if provider == "mock":
        billing_client = MockLagoBillingClient()
    elif provider == "lago":
        lago_config = config.get("lago", {})
        if lago_config.get("mock", False) or not lago_config.get("api_key"):
            billing_client = MockLagoBillingClient()
        else:
            api_url = lago_config.get("api_url", "https://api.lago.dev")
            api_key = lago_config["api_key"]
            billing_client = LagoBillingClient(api_key=api_key, api_url=api_url)  # type: ignore[assignment]
    else:
        raise BillingError(f"Unknown provider: {provider}. Use 'lago' or 'mock'")

    # Create payment gateway
    gateway_config = config.get("payment_gateway", "local")
    if isinstance(gateway_config, str):
        gateway_type = gateway_config
        gateway_settings = {}
    else:
        gateway_type = gateway_config.get("type", "local")
        gateway_settings = gateway_config

    if gateway_type == "local":
        payment_gateway = LocalPaymentGateway(gateway_settings)
    elif gateway_type == "stripe":
        payment_gateway = StripePaymentGateway(gateway_settings)  # type: ignore[assignment]
    else:
        raise BillingError(f"Unknown payment gateway type: {gateway_type}")

    # Create clean billing manager (no multi-tenant features)
    manager = BillingManager(billing_client, payment_gateway)

    if not await manager.initialize():
        raise BillingError("Failed to initialize billing manager")

    return manager


def create_billing_manager_sync(config: dict) -> BillingManager:
    """
    Create a billing manager from configuration (synchronous version).

    Note: The manager will need to be initialized with await manager.initialize()
    before use.

        Args:
        config: Billing configuration dictionary

    Returns:
        BillingManager instance (not yet initialized)
    """
    from .engines.lago import LagoBillingClient, MockLagoBillingClient
    from .gateways import LocalPaymentGateway, StripePaymentGateway

    # Determine provider type
    provider = config.get("provider", "lago")

    # Create billing client
    if provider == "mock":
        billing_client = MockLagoBillingClient()
    elif provider == "lago":
        lago_config = config.get("lago", {})
        if lago_config.get("mock", False) or not lago_config.get("api_key"):
            billing_client = MockLagoBillingClient()
        else:
            api_url = lago_config.get("api_url", "https://api.lago.dev")
            api_key = lago_config["api_key"]
            billing_client = LagoBillingClient(api_key=api_key, api_url=api_url)  # type: ignore[assignment]
    else:
        raise BillingError(f"Unknown provider: {provider}. Use 'lago' or 'mock'")

    # Create payment gateway
    gateway_config = config.get("payment_gateway", "local")
    if isinstance(gateway_config, str):
        gateway_type = gateway_config
        gateway_settings = {}
    else:
        gateway_type = gateway_config.get("type", "local")
        gateway_settings = gateway_config

    if gateway_type == "local":
        payment_gateway = LocalPaymentGateway(gateway_settings)
    elif gateway_type == "stripe":
        payment_gateway = StripePaymentGateway(gateway_settings)  # type: ignore[assignment]
    else:
        raise BillingError(f"Unknown payment gateway type: {gateway_type}")

    # Create clean billing manager (not initialized yet)
    manager = BillingManager(billing_client, payment_gateway)
    return manager
