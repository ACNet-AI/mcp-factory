"""
Billing Engines

This module provides different billing client implementations for MCP Factory.

Billing Clients (Billing Clients):
- LagoBillingClient: Lago official SDK client
- MockLagoBillingClient: Lago mock client (for testing)

Users can choose:
1. Use BillingManager + LagoBillingClient (recommended) - official reference implementation
2. Use BillingProxy - platform hosted service
3. Implement custom BillingSystem - full control, enterprise integration

Note: BillingProxy is not a billing engine, it is a platform proxy service
Import from: mcp_factory.billing.billing_proxy
"""

from abc import ABC, abstractmethod
from typing import Any

from ..models import BillingResult, PricingPlan, Subscription, UsageEvent


class BillingClient(ABC):
    """
    Abstract interface for billing clients.

    This interface allows BillingManager to work with different billing
    providers (Lago, Stripe, custom implementations) without tight coupling.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the billing client."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up client resources."""
        pass

    # Customer Management
    @abstractmethod
    async def create_customer(self, customer_id: str, email: str, name: str) -> BillingResult:
        """Create a customer in the billing system."""
        pass

    @abstractmethod
    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get customer information."""
        pass

    # Subscription Management
    @abstractmethod
    async def create_subscription(self, customer_id: str, plan_id: str) -> BillingResult:
        """Create a subscription for a customer."""
        pass

    @abstractmethod
    async def get_subscription(self, customer_id: str) -> Subscription | None:
        """Get customer's active subscription."""
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> BillingResult:
        """Cancel a subscription."""
        pass

    # Usage Tracking
    @abstractmethod
    async def record_usage_event(self, event: UsageEvent) -> BillingResult:
        """Record a usage event."""
        pass

    # Plan Management
    @abstractmethod
    async def get_plans(self) -> list[PricingPlan]:
        """Get available pricing plans."""
        pass


# Import Lago implementations after BillingClient is defined
from .lago import LagoBillingClient, MockLagoBillingClient, create_lago_client  # noqa: E402

__all__ = [
    # Base classes
    "BillingClient",
    # Lago implementations
    "LagoBillingClient",
    "MockLagoBillingClient",
    "create_lago_client",
]
