"""
MCP Factory Billing System

Core billing system abstraction following FastMCP's AuthProvider pattern.
Defines the unified interface for complete billing and payment systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import BillingConfig

# Note: Import models as needed in concrete implementations


class BillingSystem(ABC):
    """
    Abstract base class for complete billing and payment systems.

    Following FastMCP's AuthProvider pattern, this defines the unified interface
    for billing systems that include billing, payments, subscriptions, and permissions.

    Similar to how AuthProvider abstracts authentication, BillingSystem abstracts
    the complete billing and payment functionality.
    """

    def __init__(self, config: BillingConfig | None = None):
        from .models import BillingConfig

        self.config = config or BillingConfig()

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the billing system."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup system resources."""
        pass

    @abstractmethod
    def get_system_name(self) -> str:
        """Get the name of this billing system."""
        pass

    # ========================================================================
    # Billing and Usage Tracking
    # ========================================================================

    @abstractmethod
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
        Record usage for billing purposes.

        This method records usage quantity only. Pricing and revenue calculations
        are handled by the proxy platform or billing provider.

        Args:
            user_id: Direct accessor identifier (end user or proxy platform)
            usage_type: Type of usage being recorded
            quantity: Quantity of usage (default: 1)
            tool_name: Tool name if this is a tool call
            request_id: Unique request identifier from RequestContext
            metadata: Additional usage metadata (flexible, proxy-defined).
                If accessed via proxy, the proxy platform can include any fields
                it needs. Common fields: via_proxy, proxy_name, plus any custom
                tracking fields defined by the proxy

        Returns:
            Dict containing usage recording result:
                - success: Whether recording succeeded
                - transaction_id: Unique transaction identifier
                - user_id: Direct accessor identifier
                - tool_name: Tool name (if applicable)
                - quantity: Usage amount
                - timestamp: Recording timestamp
                - metadata: Full usage context
        """
        pass

    # ========================================================================
    # Subscription Management
    # ========================================================================

    @abstractmethod
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
            Dict containing subscription creation result
        """
        pass

    @abstractmethod
    async def get_subscription(self, user_id: str) -> dict[str, Any] | None:
        """
        Get user's current subscription.

        Args:
            user_id: User identifier

        Returns:
            Dict containing subscription details or None if no subscription
        """
        pass

    @abstractmethod
    async def cancel_subscription(self, user_id: str) -> dict[str, Any]:
        """
        Cancel user's subscription.

        Args:
            user_id: User identifier

        Returns:
            Dict containing cancellation result
        """
        pass

    @abstractmethod
    async def upgrade_subscription(self, user_id: str, new_plan_id: str, prorate: bool = True) -> dict[str, Any]:
        """
        Upgrade user's subscription to a higher tier plan.

        Args:
            user_id: User identifier
            new_plan_id: Target plan ID to upgrade to
            prorate: Whether to prorate the billing (default: True)

        Returns:
            Dict containing upgrade result with billing adjustments
        """
        pass

    @abstractmethod
    async def downgrade_subscription(
        self, user_id: str, new_plan_id: str, effective_date: str | None = None
    ) -> dict[str, Any]:
        """
        Downgrade user's subscription to a lower tier plan.

        Args:
            user_id: User identifier
            new_plan_id: Target plan ID to downgrade to
            effective_date: When the downgrade should take effect (None = immediate)

        Returns:
            Dict containing downgrade result and effective date
        """
        pass

    @abstractmethod
    async def pause_subscription(self, user_id: str, pause_until: str | None = None) -> dict[str, Any]:
        """
        Pause user's subscription temporarily.

        Args:
            user_id: User identifier
            pause_until: When to automatically resume (None = indefinite)

        Returns:
            Dict containing pause result and resume date
        """
        pass

    @abstractmethod
    async def resume_subscription(self, user_id: str) -> dict[str, Any]:
        """
        Resume a paused subscription.

        Args:
            user_id: User identifier

        Returns:
            Dict containing resume result
        """
        pass

    @abstractmethod
    async def get_subscription_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get subscription change history for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of history records to return

        Returns:
            List of subscription change records
        """
        pass

    # ========================================================================
    # Usage Quota Management
    # ========================================================================

    @abstractmethod
    async def get_current_usage(
        self, user_id: str, usage_type: str | None = None, period: str = "current"
    ) -> dict[str, Any]:
        """
        Get current usage statistics for a user.

        Args:
            user_id: User identifier
            usage_type: Specific usage type to query (None = all types)
            period: Time period ("current", "last_month", "last_7_days")

        Returns:
            Dict containing usage statistics
        """
        pass

    @abstractmethod
    async def check_usage_limits(self, user_id: str, usage_type: str, amount: int = 1) -> dict[str, Any]:
        """
        Check if user can perform an operation without exceeding limits.

        Args:
            user_id: User identifier
            usage_type: Type of usage to check
            amount: Amount of usage to check (default: 1)

        Returns:
            Dict containing limit check result and remaining quota
        """
        pass

    @abstractmethod
    async def get_usage_warnings(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get usage warnings for a user (approaching limits).

        Args:
            user_id: User identifier

        Returns:
            List of usage warnings
        """
        pass

    @abstractmethod
    async def reset_usage_counters(self, user_id: str, usage_type: str | None = None) -> dict[str, Any]:
        """
        Reset usage counters for a user (admin operation).

        Args:
            user_id: User identifier
            usage_type: Specific usage type to reset (None = all types)

        Returns:
            Dict containing reset operation result
        """
        pass

    # ========================================================================
    # Payment Processing
    # ========================================================================

    @abstractmethod
    async def process_payment(
        self, user_id: str, amount: float, currency: str = "USD", metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process a payment for a user.

        Args:
            user_id: User identifier
            amount: Payment amount
            currency: Currency code (default: USD)
            metadata: Optional payment metadata

        Returns:
            Dict containing payment processing result
        """
        pass

    @abstractmethod
    async def get_payment_methods(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get available payment methods for a user.

        Args:
            user_id: User identifier

        Returns:
            List of available payment methods
        """
        pass

    @abstractmethod
    async def get_payment_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get payment history for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of records to return

        Returns:
            List of payment history records
        """
        pass

    # ========================================================================
    # Plan Management
    # ========================================================================

    @abstractmethod
    async def get_available_plans(self) -> list[dict[str, Any]]:
        """
        Get all available pricing plans.

        Returns:
            List of available pricing plans
        """
        pass

    @abstractmethod
    async def get_plan_details(self, plan_id: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific plan.

        Args:
            plan_id: Plan identifier

        Returns:
            Dict containing plan details or None if plan not found
        """
        pass

    # ========================================================================
    # Management and Integration
    # ========================================================================

    @abstractmethod
    async def get_management_tools(self) -> list[dict[str, Any]]:
        """
        Get billing management tools for ManagedServer integration.

        Returns:
            List of management tool configurations
        """
        pass

    @abstractmethod
    async def get_usage_stats(self, user_id: str, period: str = "current") -> dict[str, Any]:
        """
        Get usage statistics for a user.

        Args:
            user_id: User identifier
            period: Time period for statistics (current, last_month, etc.)

        Returns:
            Dict containing usage statistics
        """
        pass

    # ========================================================================
    # Billing Rules and Pricing
    # ========================================================================

    @abstractmethod
    async def calculate_plan_cost(self, plan_id: str, usage_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Calculate the cost for a plan based on usage.

        Args:
            plan_id: Plan identifier
            usage_data: Optional usage data for calculation

        Returns:
            Dict containing cost calculation details
        """
        pass

    @abstractmethod
    async def get_upgrade_cost(self, user_id: str, new_plan_id: str) -> dict[str, Any]:
        """
        Calculate the cost to upgrade to a new plan.

        Args:
            user_id: User identifier
            new_plan_id: Target plan ID

        Returns:
            Dict containing upgrade cost and proration details
        """
        pass

    @abstractmethod
    async def apply_promotional_pricing(self, user_id: str, promo_code: str) -> dict[str, Any]:
        """
        Apply promotional pricing to a user's subscription.

        Args:
            user_id: User identifier
            promo_code: Promotional code

        Returns:
            Dict containing promotion application result
        """
        pass

    @abstractmethod
    async def get_billing_preview(self, user_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """
        Preview billing changes before applying them.

        Args:
            user_id: User identifier
            changes: Proposed changes (plan change, usage adjustments, etc.)

        Returns:
            Dict containing billing preview with costs and dates
        """
        pass

    # ========================================================================
    # Event Handling and Webhooks
    # ========================================================================

    @abstractmethod
    async def handle_webhook_event(self, event_type: str, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle incoming webhook events from payment providers.

        Args:
            event_type: Type of webhook event
            event_data: Event payload data

        Returns:
            Dict containing event processing result
        """
        pass

    @abstractmethod
    async def get_subscription_events(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent subscription events for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of events to return

        Returns:
            List of subscription events
        """
        pass

    @abstractmethod
    async def trigger_subscription_sync(self, user_id: str) -> dict[str, Any]:
        """
        Manually trigger subscription synchronization with external systems.

        Args:
            user_id: User identifier

        Returns:
            Dict containing sync operation result
        """
        pass

    # ========================================================================
    # System Status and Health
    # ========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check of the billing system.

        Returns:
            Dict containing health status information
        """
        from datetime import datetime, timezone

        return {
            "system": self.get_system_name(),
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_system_info(self) -> dict[str, Any]:
        """
        Get general information about the billing system.

        Returns:
            Dict containing system information
        """
        # Try to get version from package metadata
        try:
            from importlib.metadata import version

            package_version = version("mcp-factory")
        except Exception:
            package_version = "unknown"

        return {
            "system_name": self.get_system_name(),
            "version": package_version,
            "capabilities": ["billing", "subscriptions", "payments", "permissions"],
        }


class BaseBillingSystem(BillingSystem):
    """
    Base implementation of BillingSystem with sensible defaults.

    This class provides default implementations for all BillingSystem methods,
    allowing users to inherit and override only the methods they need.

    Ideal for:
    - Rapid prototyping of billing systems
    - Gradual implementation of billing features
    - Simple billing systems that don't need all features

    Usage:
        class MyBillingSystem(BaseBillingSystem):
            # Only implement the methods you need
            async def create_subscription(self, user_id, plan_id, email, name=None):
                # Your implementation here
                pass

            # All other methods have default "not supported" implementations
    """

    def __init__(self, config=None):  # type: ignore[no-untyped-def]
        super().__init__(config)
        self._initialized = False

    def get_system_name(self) -> str:
        """Get the name of this billing system."""
        return self.__class__.__name__

    async def initialize(self) -> bool:
        """Initialize the billing system."""
        self._initialized = True
        return True

    async def cleanup(self) -> None:
        """Cleanup system resources."""
        self._initialized = False

    # ========================================================================
    # Core Billing Methods - Override these for basic functionality
    # ========================================================================

    async def record_usage(
        self,
        user_id: str,
        usage_type: str,
        amount: int = 1,
        *,
        tool_name: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record usage - override for actual usage tracking."""
        return {"success": False, "message": "Usage tracking not implemented", "feature": "usage_tracking"}

    async def create_subscription(
        self, user_id: str, plan_id: str, email: str, name: str | None = None
    ) -> dict[str, Any]:
        """Create subscription - override for actual subscription management."""
        # Basic input validation
        if not user_id or not user_id.strip():
            return {"success": False, "message": "Invalid user_id", "error_code": "INVALID_USER_ID"}
        if not plan_id or not plan_id.strip():
            return {"success": False, "message": "Invalid plan_id", "error_code": "INVALID_PLAN_ID"}
        if not email or "@" not in email:
            return {"success": False, "message": "Invalid email address", "error_code": "INVALID_EMAIL"}

        return {
            "success": False,
            "message": "Subscription creation not implemented",
            "feature": "subscription_management",
        }

    async def get_subscription(self, user_id: str) -> dict[str, Any] | None:
        """Get subscription - override for actual subscription retrieval."""
        return None

    async def cancel_subscription(self, user_id: str) -> dict[str, Any]:
        """Cancel subscription - override for actual subscription cancellation."""
        return {
            "success": False,
            "message": "Subscription cancellation not implemented",
            "feature": "subscription_management",
        }

    async def get_available_plans(self) -> list[dict[str, Any]]:
        """Get available plans - override to provide actual plans."""
        return []

    async def get_plan_details(self, plan_id: str) -> dict[str, Any] | None:
        """Get plan details - override for actual plan information."""
        return None

    async def process_payment(
        self, user_id: str, amount: float, currency: str = "USD", metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Process payment - override for actual payment processing."""
        return {"success": False, "message": "Payment processing not implemented", "feature": "payment_processing"}

    async def get_usage_stats(self, user_id: str, period: str = "current") -> dict[str, Any]:
        """Get usage statistics - override for actual usage reporting."""
        return {"user_id": user_id, "period": period, "message": "Usage statistics not available"}

    async def get_management_tools(self) -> list[dict[str, Any]]:
        """Get management tools - override to provide actual tools."""
        return []

    # ========================================================================
    # Advanced Features - Default to "not supported"
    # ========================================================================

    async def upgrade_subscription(self, user_id: str, new_plan_id: str, prorate: bool = True) -> dict[str, Any]:
        """Upgrade subscription - advanced feature."""
        return {"success": False, "message": "Subscription upgrades not supported", "feature": "subscription_lifecycle"}

    async def downgrade_subscription(
        self, user_id: str, new_plan_id: str, effective_date: str | None = None
    ) -> dict[str, Any]:
        """Downgrade subscription - advanced feature."""
        return {
            "success": False,
            "message": "Subscription downgrades not supported",
            "feature": "subscription_lifecycle",
        }

    async def pause_subscription(self, user_id: str, pause_until: str | None = None) -> dict[str, Any]:
        """Pause subscription - advanced feature."""
        return {"success": False, "message": "Subscription pausing not supported", "feature": "subscription_lifecycle"}

    async def resume_subscription(self, user_id: str) -> dict[str, Any]:
        """Resume subscription - advanced feature."""
        return {"success": False, "message": "Subscription resuming not supported", "feature": "subscription_lifecycle"}

    async def get_subscription_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get subscription history - advanced feature."""
        return []

    async def get_current_usage(
        self, user_id: str, usage_type: str | None = None, period: str = "current"
    ) -> dict[str, Any]:
        """Get current usage - advanced feature."""
        return {"user_id": user_id, "period": period, "message": "Current usage tracking not supported"}

    async def check_usage_limits(self, user_id: str, usage_type: str, amount: int = 1) -> dict[str, Any]:
        """Check usage limits - advanced feature."""
        return {"allowed": True, "message": "Usage limit checking not supported", "feature": "usage_limits"}

    async def get_usage_warnings(self, user_id: str) -> list[dict[str, Any]]:
        """Get usage warnings - advanced feature."""
        return []

    async def reset_usage_counters(self, user_id: str, usage_type: str | None = None) -> dict[str, Any]:
        """Reset usage counters - advanced feature."""
        return {"success": False, "message": "Usage counter reset not supported", "feature": "usage_management"}

    async def get_payment_methods(self, user_id: str) -> list[dict[str, Any]]:
        """Get payment methods - advanced feature."""
        return []

    async def get_payment_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get payment history - advanced feature."""
        return []

    async def calculate_plan_cost(self, plan_id: str, usage_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Calculate plan cost - advanced feature."""
        return {"success": False, "message": "Plan cost calculation not supported", "feature": "pricing_engine"}

    async def get_upgrade_cost(self, user_id: str, new_plan_id: str) -> dict[str, Any]:
        """Get upgrade cost - advanced feature."""
        return {"success": False, "message": "Upgrade cost calculation not supported", "feature": "pricing_engine"}

    async def apply_promotional_pricing(self, user_id: str, promo_code: str) -> dict[str, Any]:
        """Apply promotional pricing - advanced feature."""
        return {"success": False, "message": "Promotional pricing not supported", "feature": "promotions"}

    async def get_billing_preview(self, user_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Get billing preview - advanced feature."""
        return {
            "user_id": user_id,
            "changes": changes,
            "message": "Billing preview not supported",
            "feature": "billing_preview",
        }

    async def handle_webhook_event(self, event_type: str, event_data: dict[str, Any]) -> dict[str, Any]:
        """Handle webhook events - advanced feature."""
        return {
            "success": False,
            "message": f"Webhook handling not supported for event type: {event_type}",
            "feature": "webhook_handling",
        }

    async def get_subscription_events(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get subscription events - advanced feature."""
        return []

    async def trigger_subscription_sync(self, user_id: str) -> dict[str, Any]:
        """Trigger subscription sync - advanced feature."""
        return {"success": False, "message": "Subscription synchronization not supported", "feature": "sync_management"}
