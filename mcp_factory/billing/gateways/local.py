"""
Local payment gateway for testing and development.
"""

import logging
from typing import Any

from ..models import BillingResult, PaymentGateway

logger = logging.getLogger(__name__)


class LocalPaymentGateway(PaymentGateway):
    """
    Local payment gateway for testing and development.

    Simulates payment processing without actual money transactions.
    All payments are automatically successful.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize local payment gateway.

        Args:
            config: Optional configuration (not used for local gateway)
        """
        self.config = config or {}
        self.payment_records: dict[str, list] = {}
        self.subscription_records: dict[str, dict] = {}

        logger.info("LocalPaymentGateway initialized")

    def get_gateway_name(self) -> str:
        """Get the gateway name"""
        return "local"

    async def process_payment(
        self, amount: float, currency: str, customer_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Process a one-time payment (mock implementation).

        Args:
            amount: Payment amount
            currency: Currency code
            customer_id: Customer identifier
            metadata: Optional payment metadata

        Returns:
            BillingResult with payment status (always successful)
        """
        try:
            # Record the payment
            if customer_id not in self.payment_records:
                self.payment_records[customer_id] = []

            payment_record = {
                "amount": amount,
                "currency": currency,
                "customer_id": customer_id,
                "metadata": metadata or {},
                "timestamp": "2024-01-01T00:00:00Z",
                "payment_id": f"local_payment_{len(self.payment_records[customer_id]) + 1}",
                "status": "completed",
            }

            self.payment_records[customer_id].append(payment_record)

            logger.info(f"Local payment processed: {amount} {currency} for customer {customer_id}")

            return BillingResult.success_result(
                f"Payment of {amount} {currency} processed successfully",
                {
                    "payment_id": payment_record["payment_id"],
                    "amount": amount,
                    "currency": currency,
                    "status": "completed",
                },
            )

        except Exception as e:
            logger.error(f"Local payment processing failed: {e}")
            return BillingResult.error_result(f"Payment processing failed: {str(e)}")

    async def create_subscription_payment(
        self, customer_id: str, plan_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Set up recurring subscription payment (mock implementation).

        Args:
            customer_id: Customer identifier
            plan_id: Subscription plan identifier
            metadata: Optional subscription metadata

        Returns:
            BillingResult with subscription payment setup status
        """
        try:
            subscription_payment = {
                "customer_id": customer_id,
                "plan_id": plan_id,
                "metadata": metadata or {},
                "subscription_id": f"local_sub_{customer_id}_{plan_id}",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
            }

            self.subscription_records[customer_id] = subscription_payment

            logger.info(f"Local subscription payment setup: {plan_id} for customer {customer_id}")

            return BillingResult.success_result(
                f"Subscription payment setup successfully for plan {plan_id}",
                {"subscription_id": subscription_payment["subscription_id"], "plan_id": plan_id, "status": "active"},
            )

        except Exception as e:
            logger.error(f"Local subscription payment setup failed: {e}")
            return BillingResult.error_result(f"Subscription payment setup failed: {str(e)}")

    async def cancel_subscription_payment(self, subscription_id: str) -> BillingResult:
        """
        Cancel recurring subscription payment (mock implementation).

        Args:
            subscription_id: Subscription identifier

        Returns:
            BillingResult with cancellation status
        """
        try:
            # Find and cancel the subscription
            for sub_record in self.subscription_records.values():
                if sub_record.get("subscription_id") == subscription_id:
                    sub_record["status"] = "cancelled"

                    logger.info(f"Local subscription cancelled: {subscription_id}")

                    return BillingResult.success_result(
                        f"Subscription {subscription_id} cancelled successfully",
                        {"subscription_id": subscription_id, "status": "cancelled"},
                    )

            return BillingResult.error_result(f"Subscription {subscription_id} not found")

        except Exception as e:
            logger.error(f"Local subscription cancellation failed: {e}")
            return BillingResult.error_result(f"Subscription cancellation failed: {str(e)}")

    def get_payment_history(self, customer_id: str) -> list[dict[str, Any]]:
        """
        Get payment history for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            List of payment records
        """
        return self.payment_records.get(customer_id, [])

    def get_subscription_info(self, customer_id: str) -> dict[str, Any] | None:
        """
        Get subscription payment information.

        Args:
            customer_id: Customer identifier

        Returns:
            Subscription payment info or None
        """
        return self.subscription_records.get(customer_id)
