"""
MCP Factory Billing System

A comprehensive billing system for MCP Factory servers, supporting
subscription management, usage tracking, and payment processing.

Installation:
    # Basic installation (includes Lago billing)
    pip install mcp-factory

    # With Stripe payment gateway support
    pip install mcp-factory[stripe]

    # With all payment gateways
    pip install mcp-factory[billing-full]

Quick Start:
    # Standard usage - Connect to any Lago instance
    from mcp_factory.billing import create_billing_manager

    # Using Lago Cloud (official service)
    manager = await create_billing_manager({
        "provider": "lago",
        "lago": {"api_key": "your-lago-key"},
        "payment_gateway": "stripe"
    })

    # Using platform's Lago instance
    manager = await create_billing_manager({
        "provider": "lago",
        "lago": {
            "api_key": "platform-assigned-key",
            "api_url": "https://platform-lago-api.com"
        },
        "payment_gateway": "stripe"
    })

    # Self-hosted Lago
    manager = await create_billing_manager({
        "provider": "lago",
        "lago": {
            "api_key": "self-hosted-key",
            "api_url": "https://lago.mycompany.com"
        }
    })

    # Advanced users can implement custom BillingSystem
    from mcp_factory.billing import BaseBillingSystem

    class MyCustomBillingSystem(BaseBillingSystem):
        # Only implement the methods you need
        async def create_subscription(self, user_id, plan_id, email, name=None):
            # Your implementation here
            pass
"""

# Core interfaces and models
from .engines import (
    BillingClient,
    LagoBillingClient,
    MockLagoBillingClient,
    create_lago_client,
)

# Main implementations
from .manager import BillingManager, create_billing_manager, create_billing_manager_sync
from .models import (
    BillingConfig,
    BillingError,
    BillingResult,
    PaymentGateway,
    PricingPlan,
    Subscription,
    SubscriptionStatus,
    UsageEvent,
)
from .system import BaseBillingSystem, BillingSystem

__all__ = [
    # 🎯 Most important APIs (90% of users need these)
    "create_billing_manager",
    "create_billing_manager_sync",
    "BillingManager",
    # 📊 Core models
    "Subscription",
    "SubscriptionStatus",
    "UsageEvent",
    "PricingPlan",
    "BillingResult",
    "BillingError",
    # 🔧 Advanced APIs (for power users)
    "BillingSystem",  # Unified system interface
    "BaseBillingSystem",  # Base class with defaults
    "BillingClient",  # For custom composition
    "BillingConfig",
    "PaymentGateway",
    # 🚀 Billing clients (for experts)
    "LagoBillingClient",
    "MockLagoBillingClient",
    "create_lago_client",
]

__version__ = "1.0.0"
