"""
Stripe payment gateway integration.
"""

import logging
from typing import Any

from ..models import BillingResult, PaymentGateway

logger = logging.getLogger(__name__)


class StripePaymentGateway(PaymentGateway):
    """
    Stripe payment gateway for processing actual payments.

    Integrates with Stripe API to handle real money transactions.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Stripe payment gateway.

        Args:
            config: Stripe configuration including secret_key, webhook_secret, etc.
        """
        self.config = config
        self.secret_key = config["secret_key"]
        self.webhook_secret = config.get("webhook_secret")
        self.publishable_key = config.get("publishable_key")

        # Initialize Stripe SDK
        try:
            import stripe

            stripe.api_key = self.secret_key
            self.stripe = stripe
            logger.info("StripePaymentGateway initialized successfully")
        except ImportError:
            logger.error("Stripe SDK not installed. Run: pip install stripe")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Stripe: {e}")
            raise

    def get_gateway_name(self) -> str:
        """Get the gateway name"""
        return "stripe"

    async def process_payment(
        self, amount: float, currency: str, customer_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Process a one-time payment via Stripe.

        Args:
            amount: Payment amount
            currency: Currency code (e.g., 'USD')
            customer_id: Customer identifier
            metadata: Optional payment metadata

        Returns:
            BillingResult with payment status
        """
        try:
            # Convert amount to cents (Stripe requirement)
            amount_cents = int(amount * 100)

            # Create payment intent
            payment_intent = self.stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True},
            )

            logger.info(f"Stripe payment intent created: {payment_intent.id} for {amount} {currency}")

            return BillingResult.success_result(
                f"Payment intent created for {amount} {currency}",
                {
                    "payment_intent_id": payment_intent.id,
                    "client_secret": payment_intent.client_secret,
                    "amount": amount,
                    "currency": currency,
                    "status": payment_intent.status,
                },
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe payment failed: {e}")
            return BillingResult.error_result(
                f"Payment failed: {str(e)}", error_code=e.code if hasattr(e, "code") else "stripe_error"
            )
        except Exception as e:
            logger.error(f"Unexpected error in Stripe payment: {e}")
            return BillingResult.error_result(f"Payment processing error: {str(e)}")

    async def create_subscription_payment(
        self, customer_id: str, plan_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Set up recurring subscription payment via Stripe.

        Args:
            customer_id: Customer identifier
            plan_id: Subscription plan identifier (should be a Stripe price ID)
            metadata: Optional subscription metadata

        Returns:
            BillingResult with subscription setup status
        """
        try:
            # Create Stripe subscription
            subscription = self.stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": plan_id}],
                metadata=metadata or {},
                expand=["latest_invoice.payment_intent"],
            )

            logger.info(f"Stripe subscription created: {subscription.id} for customer {customer_id}")

            # Extract payment information
            payment_info = {}
            if subscription.latest_invoice and subscription.latest_invoice.payment_intent:
                payment_info = {
                    "payment_intent_id": subscription.latest_invoice.payment_intent.id,
                    "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                }

            return BillingResult.success_result(
                f"Subscription created successfully for plan {plan_id}",
                {
                    "subscription_id": subscription.id,
                    "plan_id": plan_id,
                    "status": subscription.status,
                    "current_period_end": subscription.current_period_end,
                    **payment_info,
                },
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            return BillingResult.error_result(
                f"Subscription creation failed: {str(e)}", error_code=e.code if hasattr(e, "code") else "stripe_error"
            )
        except Exception as e:
            logger.error(f"Unexpected error in Stripe subscription creation: {e}")
            return BillingResult.error_result(f"Subscription creation error: {str(e)}")

    async def cancel_subscription_payment(self, subscription_id: str) -> BillingResult:
        """
        Cancel recurring subscription payment via Stripe.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            BillingResult with cancellation status
        """
        try:
            # Cancel Stripe subscription
            subscription = self.stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)

            logger.info(f"Stripe subscription cancelled: {subscription_id}")

            return BillingResult.success_result(
                f"Subscription {subscription_id} will be cancelled at period end",
                {
                    "subscription_id": subscription_id,
                    "status": subscription.status,
                    "cancel_at_period_end": subscription.cancel_at_period_end,
                    "current_period_end": subscription.current_period_end,
                },
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            return BillingResult.error_result(
                f"Subscription cancellation failed: {str(e)}",
                error_code=e.code if hasattr(e, "code") else "stripe_error",
            )
        except Exception as e:
            logger.error(f"Unexpected error in Stripe subscription cancellation: {e}")
            return BillingResult.error_result(f"Subscription cancellation error: {str(e)}")

    async def get_customer_payment_methods(self, customer_id: str) -> list[dict[str, Any]]:
        """
        Get customer's payment methods from Stripe.

        Args:
            customer_id: Stripe customer ID

        Returns:
            List of payment methods
        """
        try:
            payment_methods = self.stripe.PaymentMethod.list(customer=customer_id, type="card")

            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year,
                    }
                    if pm.card
                    else None,
                }
                for pm in payment_methods.data
            ]

        except Exception as e:
            logger.error(f"Failed to get payment methods for customer {customer_id}: {e}")
            return []

    async def create_customer(
        self, email: str, name: str | None = None, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Create a Stripe customer.

        Args:
            email: Customer email
            name: Optional customer name
            metadata: Optional customer metadata

        Returns:
            BillingResult with customer creation status
        """
        try:
            customer = self.stripe.Customer.create(email=email, name=name, metadata=metadata or {})

            logger.info(f"Stripe customer created: {customer.id} for {email}")

            return BillingResult.success_result(
                f"Customer created successfully for {email}", {"customer_id": customer.id, "email": email, "name": name}
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            return BillingResult.error_result(
                f"Customer creation failed: {str(e)}", error_code=e.code if hasattr(e, "code") else "stripe_error"
            )
        except Exception as e:
            logger.error(f"Unexpected error in Stripe customer creation: {e}")
            return BillingResult.error_result(f"Customer creation error: {str(e)}")

    async def process_withdrawal(
        self, user_id: str, amount: float, destination_account: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Process withdrawal/payout to user's bank account via Stripe.

        Args:
            user_id: User identifier
            amount: Withdrawal amount in USD
            destination_account: Stripe connected account ID or bank account token
            metadata: Optional withdrawal metadata

        Returns:
            BillingResult with withdrawal status
        """
        try:
            # Convert amount to cents (Stripe requirement)
            amount_cents = int(amount * 100)

            # Create transfer to connected account
            transfer = self.stripe.Transfer.create(
                amount=amount_cents,
                currency="usd",
                destination=destination_account,
                metadata={"user_id": user_id, "withdrawal_type": "earnings_payout", **(metadata or {})},
            )

            logger.info(f"Stripe withdrawal processed: {transfer.id} for {amount} USD to user {user_id}")

            return BillingResult.success_result(
                f"Withdrawal of {amount} USD processed successfully",
                {
                    "transfer_id": transfer.id,
                    "amount": amount,
                    "currency": "usd",
                    "destination": destination_account,
                    "status": "completed",
                    "user_id": user_id,
                },
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe withdrawal failed: {e}")
            return BillingResult.error_result(
                f"Withdrawal failed: {str(e)}", error_code=e.code if hasattr(e, "code") else "stripe_error"
            )
        except Exception as e:
            logger.error(f"Unexpected error in Stripe withdrawal: {e}")
            return BillingResult.error_result(f"Withdrawal processing error: {str(e)}")

    async def create_connected_account(
        self, user_id: str, account_info: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Create a Stripe connected account for user payouts.

        Args:
            user_id: User identifier
            account_info: Account details (email, business_type, etc.)
            metadata: Optional account metadata

        Returns:
            BillingResult with connected account creation status
        """
        try:
            account = self.stripe.Account.create(
                type="express",  # Express accounts for quick setup
                country=account_info.get("country", "US"),
                email=account_info.get("email"),
                capabilities={"transfers": {"requested": True}},
                business_type=account_info.get("business_type", "individual"),
                metadata={"user_id": user_id, **(metadata or {})},
            )

            logger.info(f"Stripe connected account created: {account.id} for user {user_id}")

            return BillingResult.success_result(
                f"Connected account created for user {user_id}",
                {
                    "account_id": account.id,
                    "user_id": user_id,
                    "email": account_info.get("email"),
                    "country": account.country,
                    "status": "created",
                },
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe connected account creation failed: {e}")
            return BillingResult.error_result(
                f"Connected account creation failed: {str(e)}",
                error_code=e.code if hasattr(e, "code") else "stripe_error",
            )
        except Exception as e:
            logger.error(f"Unexpected error in connected account creation: {e}")
            return BillingResult.error_result(f"Connected account creation error: {str(e)}")

    async def get_account_balance(self, account_id: str | None = None) -> BillingResult:
        """
        Get Stripe account balance.

        Args:
            account_id: Optional connected account ID (if None, gets platform balance)

        Returns:
            BillingResult with balance information
        """
        try:
            if account_id:
                # Get connected account balance
                balance = self.stripe.Balance.retrieve(stripe_account=account_id)
            else:
                # Get platform account balance
                balance = self.stripe.Balance.retrieve()

            available_balance = sum(item.amount for item in balance.available) / 100  # Convert from cents
            pending_balance = sum(item.amount for item in balance.pending) / 100

            return BillingResult.success_result(
                "Balance retrieved successfully",
                {
                    "available_balance": available_balance,
                    "pending_balance": pending_balance,
                    "currency": balance.available[0].currency if balance.available else "usd",
                    "account_id": account_id,
                },
            )

        except self.stripe.error.StripeError as e:
            logger.error(f"Failed to get Stripe balance: {e}")
            return BillingResult.error_result(
                f"Balance retrieval failed: {str(e)}", error_code=e.code if hasattr(e, "code") else "stripe_error"
            )
        except Exception as e:
            logger.error(f"Unexpected error getting balance: {e}")
            return BillingResult.error_result(f"Balance retrieval error: {str(e)}")


class MockStripeGateway(StripePaymentGateway):
    """
    Mock Stripe gateway for testing without Stripe SDK.

    Simulates Stripe API responses without making actual API calls.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize mock Stripe gateway"""
        self.config = config or {}
        self.mock_customers: dict[str, Any] = {}
        self.mock_subscriptions: dict[str, Any] = {}
        self.mock_payments: dict[str, Any] = {}

        logger.info("MockStripeGateway initialized")

    def get_gateway_name(self) -> str:
        return "mock-stripe"

    async def process_payment(
        self, amount: float, currency: str, customer_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """Mock payment processing"""
        payment_id = f"pi_mock_{len(self.mock_payments) + 1}"

        self.mock_payments[payment_id] = {
            "id": payment_id,
            "amount": amount,
            "currency": currency,
            "customer": customer_id,
            "status": "succeeded",
            "metadata": metadata or {},
        }

        return BillingResult.success_result(
            f"Mock payment of {amount} {currency} processed",
            {"payment_intent_id": payment_id, "amount": amount, "currency": currency, "status": "succeeded"},
        )

    async def create_subscription_payment(
        self, customer_id: str, plan_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """Mock subscription creation"""
        subscription_id = f"sub_mock_{len(self.mock_subscriptions) + 1}"

        self.mock_subscriptions[subscription_id] = {
            "id": subscription_id,
            "customer": customer_id,
            "plan": plan_id,
            "status": "active",
            "metadata": metadata or {},
        }

        return BillingResult.success_result(
            f"Mock subscription created for plan {plan_id}",
            {"subscription_id": subscription_id, "plan_id": plan_id, "status": "active"},
        )

    async def process_withdrawal(
        self, user_id: str, amount: float, destination_account: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """Mock withdrawal processing"""
        transfer_id = f"tr_mock_{len(self.mock_payments) + 1}"

        withdrawal_record = {
            "id": transfer_id,
            "amount": amount,
            "currency": "usd",
            "destination": destination_account,
            "user_id": user_id,
            "status": "completed",
            "metadata": metadata or {},
        }

        self.mock_payments[transfer_id] = withdrawal_record

        return BillingResult.success_result(
            f"Mock withdrawal of {amount} USD processed",
            {
                "transfer_id": transfer_id,
                "amount": amount,
                "currency": "usd",
                "destination": destination_account,
                "status": "completed",
                "user_id": user_id,
            },
        )

    async def create_connected_account(
        self, user_id: str, account_info: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """Mock connected account creation"""
        account_id = f"acct_mock_{len(self.mock_customers) + 1}"

        account_record = {
            "id": account_id,
            "user_id": user_id,
            "email": account_info.get("email"),
            "country": account_info.get("country", "US"),
            "business_type": account_info.get("business_type", "individual"),
            "status": "created",
            "metadata": metadata or {},
        }

        self.mock_customers[account_id] = account_record

        return BillingResult.success_result(
            f"Mock connected account created for user {user_id}",
            {
                "account_id": account_id,
                "user_id": user_id,
                "email": account_info.get("email"),
                "country": account_info.get("country", "US"),
                "status": "created",
            },
        )

    async def get_account_balance(self, account_id: str | None = None) -> BillingResult:
        """Mock balance retrieval"""
        return BillingResult.success_result(
            "Mock balance retrieved",
            {
                "available_balance": 1000.0,  # Mock available balance
                "pending_balance": 50.0,  # Mock pending balance
                "currency": "usd",
                "account_id": account_id,
            },
        )
