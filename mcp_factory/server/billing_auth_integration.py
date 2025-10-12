"""
Billing and Authorization Integration Service
This module provides integration logic between billing and authorization systems
for MCP servers, keeping the integration logic separate from the core server.
"""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BillingAuthIntegration:
    """
    Integration service for billing and authorization systems.
    This class handles the coordination between billing and authorization
    without implementing the core logic of either system.
    """

    def __init__(
        self,
        billing_system: Any,
        authorization_manager: Any,
        plan_config: dict[str, Any] | None = None,
        merge_strategy: str = "merge",
    ) -> None:
        """
        Initialize the integration service.
        Args:
            billing_system: BillingSystem instance
            authorization_manager: AuthorizationManager instance
            plan_config: Optional plan configuration dict to override defaults
            merge_strategy: Configuration merge strategy
                - "merge": Field-level override (default, recommended for most cases)
                - "replace": Complete replacement (for advanced users who want full control)
        """
        self.billing = billing_system
        self.auth = authorization_manager
        # Default configuration - simple and clear rules
        default_config = {
            # Default role mapping - all registered users are user role
            "default_role_mapping": {
                # Common user subscription plans
                "free": "user",  # Registered users with free plan
                "basic": "user",  # Registered users with basic paid plan
                "pro": "user",  # Registered users with pro paid plan
                # Users accessing via intermediary
                "proxy": "user",  # Proxy users
            },
            # Default tier mapping - plan to user tier mapping
            "default_tier_mapping": {
                # Tiers corresponding to subscription plans
                "free": "free_tier",  # Free tier
                "basic": "basic_tier",  # Basic tier
                "pro": "pro_tier",  # Pro tier
                # Proxy user tier (accessing via intermediary)
                "proxy": "proxy_tier",  # Proxy user tier
            },
            # Default roles (when plan is not explicitly defined)
            "fallback_roles": {
                "registered_user": "user",  # Any registered user is user role
                "anonymous_visitor": "visitor",  # Only unregistered visitors are visitor role
            },
            # Smart inference (only enabled for custom config)
            "enable_smart_inference": False,  # Smart inference disabled by default
            "role_inference_rules": None,  # No inference rules by default
            # Dynamic plan support
            "dynamic_plans": True,  # Enable dynamic plan loading
            "plan_cache_ttl": 300,  # Plan cache TTL (seconds)
            "auto_load_on_init": False,  # Not auto-load by default (avoid complexity)
        }
        # Apply configuration based on merge strategy
        if plan_config:
            if merge_strategy == "replace":
                # Complete replacement: use only provided configuration
                self._config = plan_config
            elif merge_strategy == "merge":
                # Field-level override: merge provided fields with defaults
                self._config = self._merge_config(default_config, plan_config)
            else:
                raise ValueError(f"Invalid merge_strategy: {merge_strategy}. Must be 'merge' or 'replace'")
        else:
            self._config = default_config
        # Set instance attributes
        self.default_role_mapping = self._config["default_role_mapping"]
        self.default_tier_mapping = self._config["default_tier_mapping"]
        self.fallback_roles = self._config["fallback_roles"]
        self.enable_smart_inference = self._config.get("enable_smart_inference", False)
        self.role_inference_rules = self._config.get("role_inference_rules")
        self.dynamic_plans_enabled = self._config.get("dynamic_plans", True)
        self.plan_cache_ttl = self._config.get("plan_cache_ttl", 300)
        self.auto_load_on_init = self._config.get("auto_load_on_init", False)
        # Dynamic plan registry
        self._plan_registry: dict[str, dict[str, Any]] = {}
        self._plan_cache: dict[str, dict[str, Any]] = {}
        self._cache_timestamp = 0
        logger.info(f"BillingAuthIntegration initialized with dynamic plans: {self.dynamic_plans_enabled}")

        # Auto-load plans (if enabled)
        if self.auto_load_on_init and self.dynamic_plans_enabled:
            # Async initialize plan loading (non-blocking constructor)
            try:
                # Try to schedule loading in event loop
                asyncio.create_task(self._auto_load_plans())
            except RuntimeError:
                # If no event loop, call manually later
                logger.info("No event loop available, plans will be loaded on first access")

    # ========================================================================
    # Dynamic Plan Management (Dynamic Plan Management)
    # ========================================================================
    def register_plan(
        self, plan_id: str, role: str, tier: str | None = None, billing_mode: str = "subscription"
    ) -> None:
        """
        Dynamically register billing plan
        Args:
            plan_id: Plan ID
            role: Corresponding user role
            tier: User tier (optional)
            billing_mode: Billing mode (subscription/pay_per_use/prepaid/free)
        """
        self._plan_registry[plan_id] = {
            "role": role,
            "tier": tier,
            "billing_mode": billing_mode,
            "registered_at": time.time(),
        }
        logger.info(f"Registered plan: {plan_id} -> {role} (tier: {tier}, mode: {billing_mode})")

    async def get_plans_from_billing_system(self) -> dict[str, dict]:
        """Dynamically get available plans from billing system"""
        if not self.billing or not self.dynamic_plans_enabled:
            return {}
        try:
            # Check cache
            current_time = time.time()
            if (current_time - self._cache_timestamp) < self.plan_cache_ttl and self._plan_cache:
                return self._plan_cache
            # Get plans from billing system
            if hasattr(self.billing, "get_available_plans"):
                plans = await self.billing.get_available_plans()
                # Convert to standard format
                formatted_plans = {}
                for plan in plans:
                    plan_id = plan.get("id") or plan.get("plan_id")
                    if plan_id:
                        # Smart mapping: infer role from plan name
                        role = self._infer_role_from_plan(plan_id, plan)
                        formatted_plans[plan_id] = {
                            "role": role,
                            "tier": plan_id,
                            "billing_mode": "subscription",
                            "source": "billing_system",
                        }
                # Update cache
                self._plan_cache = formatted_plans
                self._cache_timestamp = current_time  # type: ignore[assignment]
                logger.info(f"Loaded {len(formatted_plans)} plans from billing system")
                return formatted_plans
        except Exception as e:
            logger.warning(f"Failed to load plans from billing system: {e}")
        return {}

    def _infer_role_from_plan(self, plan_id: str, plan_data: dict) -> str:
        """Infer user role from plan ID and data (only when smart inference is enabled)"""

        # If smart inference not enabled, use simple fallback logic
        if not self.enable_smart_inference or not self.role_inference_rules:
            return self._simple_role_fallback(plan_id, plan_data)

        # Smart inference logic (only for custom configuration)
        plan_id_lower = plan_id.lower()

        # Get inference rules
        free_keywords = self.role_inference_rules.get("free_keywords", ["free", "trial", "demo"])
        proxy_keywords = self.role_inference_rules.get("proxy_keywords", ["proxy", "payg", "pay_per_use"])
        default_free_role = self.role_inference_rules.get("default_free_role", "visitor")
        default_paid_role = self.role_inference_rules.get("default_paid_role", "user")

        # Check for free plan
        if any(keyword in plan_id_lower for keyword in free_keywords):
            return default_free_role  # type: ignore[no-any-return]

        # Check proxy user plan
        if any(keyword in plan_id_lower for keyword in proxy_keywords):
            return default_paid_role  # type: ignore[no-any-return]

        # Check price (if provided)
        price = plan_data.get("price", 0) if plan_data else 0
        if price == 0:
            return default_free_role  # type: ignore[no-any-return]

        # Default paid plan
        return default_paid_role  # type: ignore[no-any-return]

    def _simple_role_fallback(self, plan_id: str, plan_data: dict) -> str:
        """Simple role fallback logic (default mode)"""

        # 1. Check explicit default mapping
        if plan_id in self.default_role_mapping:
            return self.default_role_mapping[plan_id]  # type: ignore[no-any-return]

        # 2. If has billing plan, means registered user
        # Note: being able to query billing plan means user is registered
        if plan_id:  # Having plan ID means registered user
            return self.fallback_roles.get("registered_user", "user")  # type: ignore[no-any-return]
        else:
            # No plan ID, possibly unregistered visitor
            return self.fallback_roles.get("anonymous_visitor", "visitor")  # type: ignore[no-any-return]

    def get_role_by_plan(self, plan_id: str) -> str:
        """Get role corresponding to plan"""
        # 1. Check dynamically registered plans
        if plan_id in self._plan_registry:
            return self._plan_registry[plan_id]["role"]  # type: ignore[no-any-return]
        # 2. Check cached plans
        if plan_id in self._plan_cache:
            return self._plan_cache[plan_id]["role"]  # type: ignore[no-any-return]
        # 3. Use smart inference
        return self._infer_role_from_plan(plan_id, {})

    def get_tier_by_plan(self, plan_id: str) -> str | None:
        """Get user tier corresponding to plan"""
        # 1. Check dynamically registered plans
        if plan_id in self._plan_registry:
            return self._plan_registry[plan_id].get("tier")

        # 2. Check cached plans
        if plan_id in self._plan_cache:
            return self._plan_cache[plan_id].get("tier")

        # 3. Check default tier mapping
        if plan_id in self.default_tier_mapping:
            return self.default_tier_mapping[plan_id]  # type: ignore[no-any-return]

        # 4. Infer tier from plan name
        return self._infer_tier_from_plan(plan_id)

    def _infer_tier_from_plan(self, plan_id: str) -> str | None:
        """Infer tier from plan name"""
        if not plan_id:
            return None

        plan_id_lower = plan_id.lower()

        # Proxy users / intermediary access
        if "proxy" in plan_id_lower:
            return "proxy_tier"

        # Free plan
        if "free" in plan_id_lower or "trial" in plan_id_lower:
            return "free_tier"

        # Basic plan
        if "basic" in plan_id_lower or "starter" in plan_id_lower:
            return "basic_tier"

        # Pro plan
        if "pro" in plan_id_lower or "premium" in plan_id_lower or "professional" in plan_id_lower:
            return "pro_tier"

        # Enterprise plan
        if "enterprise" in plan_id_lower or "business" in plan_id_lower:
            return "enterprise_tier"

        # Default to basic tier
        return "basic_tier"

    def is_pay_per_use_plan(self, plan_id: str) -> bool:
        """Check if pay-per-use billing plan"""
        # Check registry
        if plan_id in self._plan_registry:
            billing_mode = self._plan_registry[plan_id]["billing_mode"]
            return billing_mode in ("pay_per_use", "prepaid")
        # Check cache
        if plan_id in self._plan_cache:
            billing_mode = self._plan_cache[plan_id].get("billing_mode")
            return billing_mode in ("pay_per_use", "prepaid")
        # Default check
        return plan_id in ("proxy", "pay_per_use", "prepaid", "payg")

    async def _auto_load_plans(self) -> None:
        """Auto-load plans (async)"""
        try:
            plans = await self.get_plans_from_billing_system()
            if plans:
                logger.info(f"Auto-loaded {len(plans)} plans from billing system")
            else:
                logger.info("No plans found in billing system")
        except Exception as e:
            logger.warning(f"Failed to auto-load plans: {e}")

    # ========================================================================
    # Backward Compatibility (Backward Compatibility)
    # ========================================================================
    @property
    def billing_role_mapping(self) -> dict[str, str]:
        """Backward compatible: get role mapping for all plans"""
        mapping = self.default_role_mapping.copy()

        # Add dynamically registered plans
        for plan_id, plan_info in self._plan_registry.items():
            mapping[plan_id] = plan_info["role"]

        # Add cached plans
        for plan_id, plan_info in self._plan_cache.items():
            mapping[plan_id] = plan_info["role"]

        return mapping  # type: ignore[no-any-return]

    def _merge_config(self, default_config: dict, custom_config: dict) -> dict:
        """
        Merge configuration with field-level override strategy.
        Strategy: "Field-level override"
        - If developer provides a field, use it completely (replaces the entire field)
        - If developer doesn't provide a field, use the default value
        - This gives developers precise control over individual configuration aspects
        Example:
            default: {"billing_role_mapping": {"free": "visitor", "basic": "user"}}
            custom:  {"billing_role_mapping": {"trial": "visitor", "pro": "user"}}
            result:  {"billing_role_mapping": {"trial": "visitor", "pro": "user"}}
        """
        merged = default_config.copy()
        for key, value in custom_config.items():
            # Complete field-level override - replace entire field value
            merged[key] = value
        return merged

    def get_user_plan(self, user_id: str) -> str:
        """
        Get user's current billing plan (synchronous).

        Note: This is a synchronous wrapper. If you're in an async context,
        consider using get_user_plan_async() instead for better performance.
        """
        if not self.billing:
            return "free"
        try:
            # Try to get user plan from billing system (sync method)
            if hasattr(self.billing, "get_user_plan"):
                plan = self.billing.get_user_plan(user_id)
                if plan:
                    return plan  # type: ignore[no-any-return]
            # Fallback: try to get from subscription
            # Note: We skip async methods in sync context to avoid event loop issues
            return "free"
        except Exception as e:
            logger.error(f"Error getting user plan for {user_id}: {e}")
            return "free"

    async def get_user_plan_async(self, user_id: str) -> str:
        """
        Get user's current billing plan (asynchronous).

        This is the preferred method when in an async context.
        """
        if not self.billing:
            return "free"
        try:
            # Try to get user plan from billing system
            if hasattr(self.billing, "get_user_plan"):
                plan = self.billing.get_user_plan(user_id)
                if plan:
                    return plan  # type: ignore[no-any-return]
            # Fallback: try to get from subscription (async)
            if hasattr(self.billing, "get_user_subscription"):
                subscription = await self.billing.get_user_subscription(user_id)
                if subscription and subscription.get("active"):
                    return subscription.get("plan_id", "free")  # type: ignore[no-any-return]
            return "free"
        except Exception as e:
            logger.error(f"Error getting user plan for {user_id}: {e}")
            return "free"

    def get_user_role_info(self, user_id: str) -> dict:
        """Get comprehensive user role and billing information"""
        if not self.auth:
            return {"role": "visitor", "plan": None, "tier": None}

        try:
            user_role = self.auth.get_user_role(user_id)
            current_plan = self.get_user_plan(user_id)

            # Get role and tier
            if current_plan:
                role = self.get_role_by_plan(current_plan)
                tier = self.get_tier_by_plan(current_plan)
            else:
                role = user_role or "visitor"
                tier = None

            result = {"role": role, "plan": current_plan, "tier": tier}

            return result

        except Exception as e:
            logger.error(f"Error getting user role info: {e}")
            return {"role": "visitor", "plan": None, "tier": None}

    # =========================================================================
    # Role Mapping Methods
    # =========================================================================
    def get_plan_by_role(self, role_name: str) -> str | None:
        """Get billing plan by role name"""
        for plan, role in self.billing_role_mapping.items():
            if role == role_name:
                return plan
        return None

    def get_subscription_roles(self) -> list[str]:
        """Get all subscription-related roles"""
        return list(set(self.billing_role_mapping.values()))
