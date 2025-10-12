"""
Billing system data models.

Core data structures for the MCP Factory billing system.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class BillingConfig:
    """Billing configuration for providers."""

    customer_prefix: str | None = None
    lago_config: dict[str, Any] | None = None
    payment_gateway_config: dict[str, Any] | None = None

    # Dual wallet configuration (enabled by default)
    enable_burn_tracking: bool = True  # Credit burn tracking
    burn_reason_prefix: str = "platform_fee"
    enable_wallet_transfer: bool = True  # Support wallet-to-wallet transfers
    consumer_wallet_suffix: str = "_consumer"
    provider_wallet_suffix: str = "_provider"

    # Transfer and withdrawal restrictions
    allow_reverse_transfer: bool = False  # Prohibit reverse transfers (consumer → provider)
    allow_cross_user_transfer: bool = False  # Prohibit cross-user transfers

    # Withdrawal policy
    consumer_wallet_withdrawal: bool = False  # Consumer wallet cannot withdraw
    provider_wallet_withdrawal: bool = True  # Provider wallet can withdraw
    min_withdrawal_amount: float = 10.0  # Minimum withdrawal amount
    withdrawal_fee_rate: float = 0.02  # Withdrawal fee rate (2%)


# ============================================================================
# Enums
# ============================================================================


class SubscriptionStatus(Enum):
    """Subscription status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class PaymentStatus(Enum):
    """Payment status enumeration"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class Subscription:
    """User subscription information"""

    user_id: str
    plan_id: str
    status: SubscriptionStatus
    started_at: datetime
    expires_at: datetime | None = None
    features: list[str] = field(default_factory=list)
    usage_limits: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status != SubscriptionStatus.ACTIVE:
            return False

        if self.expires_at:
            # Handle timezone-aware vs timezone-naive datetime comparison
            now = datetime.now()
            if self.expires_at.tzinfo is not None and now.tzinfo is None:
                # expires_at is timezone-aware, now is naive - make now UTC
                from datetime import timezone

                now = now.replace(tzinfo=timezone.utc)
            elif self.expires_at.tzinfo is None and now.tzinfo is not None:
                # expires_at is naive, now is timezone-aware - make expires_at UTC
                from datetime import timezone

                expires_at = self.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = self.expires_at

            if now > (expires_at if "expires_at" in locals() else self.expires_at):
                return False

        return True

    def has_feature(self, feature: str) -> bool:
        """Check if subscription includes a specific feature"""
        return feature in self.features

    def get_usage_limit(self, metric: str) -> int:
        """Get usage limit for a specific metric (-1 means unlimited)"""
        return self.usage_limits.get(metric, -1)

    @classmethod
    def from_lago(cls, lago_data: dict[str, Any]) -> "Subscription":
        """Create Subscription from Lago API response"""
        return cls(
            user_id=lago_data.get("external_customer_id", ""),
            plan_id=lago_data.get("plan", {}).get("code", ""),
            status=SubscriptionStatus(lago_data.get("status", "inactive")),
            started_at=datetime.fromisoformat(lago_data.get("started_at", datetime.now().isoformat())),
            expires_at=datetime.fromisoformat(lago_data["ending_at"]) if lago_data.get("ending_at") else None,
            metadata={"lago_subscription_id": lago_data.get("lago_id")},
        )


@dataclass
class UsageEvent:
    """Usage event for billing purposes"""

    user_id: str
    event_type: str
    quantity: int = 1
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_lago_event(self) -> dict[str, Any]:
        """Convert to Lago event format"""
        # Ensure timestamp is not None (should be set in __post_init__)
        timestamp = self.timestamp or datetime.now()
        return {
            "external_customer_id": self.user_id,
            "transaction_id": f"{self.user_id}_{int(timestamp.timestamp())}",
            "code": self.event_type,
            "timestamp": int(timestamp.timestamp()),
            "properties": {"quantity": self.quantity, **self.metadata},
        }


@dataclass
class PricingPlan:
    """Pricing plan definition"""

    plan_id: str
    name: str
    description: str
    price: float
    currency: str = "USD"
    billing_cycle: str = "monthly"
    features: list[str] = field(default_factory=list)
    usage_limits: dict[str, int] = field(default_factory=dict)

    def to_lago_plan(self) -> dict[str, Any]:
        """Convert to Lago plan format"""
        return {
            "code": self.plan_id,
            "name": self.name,
            "description": self.description,
            "amount_cents": int(self.price * 100),
            "amount_currency": self.currency,
            "interval": self.billing_cycle,
        }


@dataclass
class BillingResult:
    """Result of a billing operation"""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error_code: str | None = None

    @classmethod
    def success_result(cls, message: str, data: dict[str, Any] | None = None) -> "BillingResult":
        """Create a success result"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_result(cls, message: str, error_code: str | None = None) -> "BillingResult":
        """Create an error result"""
        return cls(success=False, message=message, error_code=error_code)


# ============================================================================
# Payment Gateway Interface
# ============================================================================


class PaymentGateway(ABC):
    """
    Abstract base class for payment gateways.

    Payment gateways handle the actual money transactions,
    while billing providers handle subscription logic.
    """

    @abstractmethod
    def get_gateway_name(self) -> str:
        """Get the name of this payment gateway"""
        pass

    @abstractmethod
    async def process_payment(
        self, amount: float, currency: str, customer_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Process a one-time payment.

        Args:
            amount: Payment amount
            currency: Currency code (e.g., 'USD')
            customer_id: Customer identifier
            metadata: Optional payment metadata

        Returns:
            BillingResult with payment information
        """
        pass

    @abstractmethod
    async def create_subscription_payment(
        self, customer_id: str, plan_id: str, metadata: dict[str, Any] | None = None
    ) -> BillingResult:
        """
        Set up recurring subscription payment.

        Args:
            customer_id: Customer identifier
            plan_id: Subscription plan identifier
            metadata: Optional subscription metadata

        Returns:
            BillingResult with subscription payment information
        """
        pass


# ============================================================================
# Exceptions
# ============================================================================


class BillingError(Exception):
    """Base exception for billing-related errors"""

    def __init__(self, message: str, error_code: str | None = None, provider: str | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.provider = provider


# ============================================================================
# Credit burn related models (for proxy mode only)
# ============================================================================


@dataclass
class BurnRecord:
    """Credit burn record (for proxy mode only)"""

    burn_id: str
    transaction_id: str
    user_id: str
    developer_id: str | None  # None when withdrawal burn
    burned_amount: float
    original_amount: float
    burn_rate: float | None  # None when withdrawal burn
    burn_reason: str  # "platform_fee" | "withdrawal" | "refund" | "consumption"
    withdrawal_info: dict[str, Any] | None  # Withdrawal related info
    timestamp: datetime
    metadata: dict[str, Any] | None = None


@dataclass
class BurnResult:
    """Burn operation result (for proxy mode only)"""

    success: bool
    burn_record: BurnRecord | None = None
    message: str = ""
    data: dict[str, Any] | None = None


@dataclass
class DualWalletInfo:
    """Dual wallet info (for proxy mode only)"""

    user_id: str
    consumer_wallet_id: str
    provider_wallet_id: str
    consumer_balance: float
    provider_balance: float
    total_consumed: float
    total_earned: float
    total_withdrawn: float
    created_at: datetime
    updated_at: datetime


class SubscriptionError(BillingError):
    """Exception raised when subscription operations fail"""

    pass


class UsageTrackingError(BillingError):
    """Exception raised when usage tracking fails"""

    pass


class PaymentError(BillingError):
    """Exception raised when payment operations fail"""

    pass


class ConfigurationError(BillingError):
    """Exception raised when billing configuration is invalid"""

    pass
