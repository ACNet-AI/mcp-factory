"""
Custom Payment Gateway Template

Template for users to implement their own payment gateways
following the PaymentGateway interface.

This file provides ONLY the base template. Users should implement
specific payment providers (Alipay, WeChat Pay, etc.) in their own code
or use third-party libraries.
"""

import logging
from typing import Any

from ..models import BillingResult, PaymentGateway

logger = logging.getLogger(__name__)


class CustomPaymentGateway(PaymentGateway):
    """
    Template for custom payment gateway implementations.

    Users can inherit from this class to integrate with:
    - Regional payment providers (Alipay, WeChat Pay, etc.)
    - Enterprise payment systems
    - Cryptocurrency payment processors
    - Bank transfer systems
    - Custom payment workflows

    Example use cases:
    - Alipay/WeChat Pay for Chinese market
    - PayPal for international payments
    - Bank transfers for B2B payments
    - Cryptocurrency payments (Bitcoin, USDC, etc.)
    - Internal credit systems
    - Gift card/voucher systems
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize custom payment gateway.

        Args:
            config: Custom payment gateway configuration
        """
        self.config = config
        self.gateway_name = config.get("name", "CustomPaymentGateway")
        self.api_url = config.get("api_url")
        self.api_key = config.get("api_key")
        self.webhook_secret = config.get("webhook_secret")

        # Custom configuration examples
        self.currency = config.get("currency", "USD")
        self.timeout = config.get("timeout", 30)
        self.retry_count = config.get("retry_count", 3)

    def get_gateway_name(self) -> str:
        """Get the name of this payment gateway."""
        return "custom"

    async def process_payment(
        self, amount: float, currency: str, customer_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Process payment using custom payment system.

        Implement your custom payment processing logic here:
        - Call payment provider API
        - Handle authentication
        - Process payment request
        - Handle responses and errors
        """
        try:
            logger.info(f"Processing payment: {amount} {currency} for customer {customer_id}")

            # TODO: Implement your custom payment processing logic
            # Examples:

            # 1. API-based payment processing
            # payment_data = {
            #     "amount": int(amount * 100),  # Convert to cents
            #     "currency": currency,
            #     "customer_id": customer_id,
            #     "metadata": metadata or {}
            # }
            # response = await self._api_client.post("/payments", payment_data)
            # return self._handle_payment_response(response)

            # 2. Cryptocurrency payment
            # wallet_address = await self._generate_payment_address(customer_id)
            # return BillingResult(
            #     success=True,
            #     message=f"Send {amount} {currency} to {wallet_address}",
            #     data={"wallet_address": wallet_address, "amount": amount}
            # )

            # 3. Bank transfer
            # transfer_info = await self._generate_transfer_info(amount, currency, customer_id)
            # return BillingResult(
            #     success=True,
            #     message="Bank transfer initiated",
            #     data=transfer_info
            # )

            # Placeholder implementation
            return BillingResult(
                success=True,
                message=f"Custom payment processed: {amount} {currency}",
                data={
                    "gateway": self.gateway_name,
                    "amount": amount,
                    "currency": currency,
                    "customer_id": customer_id,
                    "transaction_id": f"custom_{customer_id}_{amount}",
                    "status": "completed",
                },
            )

        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return BillingResult(
                success=False, message=f"Payment failed: {str(e)}", data={"error": str(e), "gateway": self.gateway_name}
            )

    async def refund_payment(
        self, transaction_id: str, amount: float | None = None, reason: str | None = None
    ) -> BillingResult:
        """
        Process refund using custom payment system.

        Implement your custom refund logic here:
        - Validate transaction
        - Process refund request
        - Handle partial/full refunds
        - Update transaction status
        """
        try:
            logger.info(f"Processing refund for transaction {transaction_id}")

            # TODO: Implement your custom refund logic
            # Examples:

            # 1. API-based refund
            # refund_data = {
            #     "transaction_id": transaction_id,
            #     "amount": amount,
            #     "reason": reason
            # }
            # response = await self._api_client.post("/refunds", refund_data)
            # return self._handle_refund_response(response)

            # 2. Manual refund process
            # refund_request = await self._create_refund_request(transaction_id, amount, reason)
            # await self._notify_admin(refund_request)
            # return BillingResult(success=True, message="Refund request created")

            # Placeholder implementation
            return BillingResult(
                success=True,
                message=f"Refund processed for transaction {transaction_id}",
                data={
                    "gateway": self.gateway_name,
                    "transaction_id": transaction_id,
                    "refund_amount": amount,
                    "refund_id": f"refund_{transaction_id}",
                    "status": "completed",
                },
            )

        except Exception as e:
            logger.error(f"Refund processing failed: {e}")
            return BillingResult(
                success=False, message=f"Refund failed: {str(e)}", data={"error": str(e), "gateway": self.gateway_name}
            )

    async def get_payment_status(self, transaction_id: str) -> dict[str, Any]:
        """
        Get payment status from custom payment system.

        Implement your custom status checking logic here:
        - Query payment provider API
        - Return current payment status
        - Handle different status types
        """
        try:
            logger.info(f"Checking payment status for transaction {transaction_id}")

            # TODO: Implement your custom status checking logic
            # Examples:

            # 1. API-based status check
            # response = await self._api_client.get(f"/payments/{transaction_id}")
            # return self._parse_payment_status(response)

            # 2. Database-based status check
            # status = await self._db.get_payment_status(transaction_id)
            # return {"status": status, "transaction_id": transaction_id}

            # Placeholder implementation
            return {
                "transaction_id": transaction_id,
                "status": "completed",
                "gateway": self.gateway_name,
                "last_updated": "2024-01-01T00:00:00Z",
            }

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {"transaction_id": transaction_id, "status": "error", "error": str(e), "gateway": self.gateway_name}


# Example usage documentation (not actual implementations)
"""
Example implementations that users can create in their own code:

# 1. Alipay Gateway Example
class AlipayGateway(CustomPaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        self.app_id = config["app_id"]
        # Use alipay-sdk-python library

    async def process_payment(self, amount, currency, customer_id, metadata=None):
        # Implement using alipay-sdk-python
        pass

# 2. WeChat Pay Gateway Example
class WeChatPayGateway(CustomPaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        self.mch_id = config["mch_id"]
        # Use wechatpay-python library

    async def process_payment(self, amount, currency, customer_id, metadata=None):
        # Implement using wechatpay-python
        pass

# 3. Crypto Gateway Example
class CryptoPaymentGateway(CustomPaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        self.wallet_addresses = config["wallet_addresses"]
        # Use web3.py or similar library

    async def process_payment(self, amount, currency, customer_id, metadata=None):
        # Implement crypto payment logic
        pass

# Usage:
proxy = create_billing_proxy(
    payment_gateway_type="custom",
    payment_gateway_config={
        "gateway_class": AlipayGateway,  # User's implementation
        "app_id": "your_app_id",
        "private_key": "your_private_key"
    }
)
"""
