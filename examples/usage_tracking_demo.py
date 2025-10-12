"""
Usage Tracking Demo - Conceptual Example

This is a conceptual demonstration showing the architecture design.
For a working example with mock billing, see production_ready.py.

This example demonstrates:
1. Automatic usage tracking for tool calls
2. Proxy access with usage recording
3. RequestContext integration
4. Clear separation of concerns: developer server vs proxy platform

Key Architecture Principles:
- Developer's server: Records usage quantity and metadata ONLY
- Proxy platform: Handles pricing, billing, and revenue sharing
- No cost or revenue_share in developer's code - that's by design!

This conceptual example requires real Lago API credentials to run.
It serves as a reference for understanding the architecture and API usage.
"""

import asyncio

from mcp_factory import ManagedServer
from mcp_factory.authorization import AuthorizedProxies, ProxyConfig


async def main():
    print("=" * 70)
    print("Usage Tracking Demo")
    print("=" * 70)

    # Create server with billing and authorized proxies
    server = ManagedServer(
        name="weather-service",
        billing={
            "provider": "lago",
            "lago": {
                "api_key": "your-lago-key",
                "api_url": "https://api.getlago.com"
            }
        },
        authorization={
            "authorized_proxies": AuthorizedProxies(
                proxies={
                    "mcp-factory": ProxyConfig(
                        name="mcp-factory",
                        api_key="platform_key_abc123",
                        rate_limit_per_hour=10000,
                        metadata={
                            "contract_id": "CT-2024-001",
                            "contact_email": "dev@mcp-factory.com"
                        }
                    )
                },
                assigns_tier="proxy_tier"
            )
        }
    )

    # Define a tool
    @server.tool()
    async def get_weather(city: str) -> dict:
        """Get weather for a city"""
        # Simulate weather service
        return {
            "city": city,
            "temperature": 25,
            "weather": "sunny"
        }

    print("\n" + "-" * 70)
    print("Scenario 1: Direct User Access")
    print("-" * 70)

    # Simulate direct user access
    print("\n1. Direct user 'alice' calls get_weather")
    usage_result = await server.record_tool_usage(
        tool_name="get_weather",
        user_id="alice"
    )

    if usage_result:
        print("\n✅ Usage recorded:")
        print(f"   Transaction ID: {usage_result.get('transaction_id')}")
        print(f"   User: {usage_result.get('user_id')}")
        print(f"   Tool: {usage_result.get('tool_name')}")
        print(f"   Quantity: {usage_result.get('quantity')}")
        print(f"   Via Proxy: {usage_result.get('via_proxy', False)}")

    print("\n" + "-" * 70)
    print("Scenario 2: Proxy Access")
    print("-" * 70)

    # Simulate proxy access
    print("\n1. Verify proxy API key")
    proxy_info = server.verify_proxy_access("platform_key_abc123")

    if proxy_info:
        print(f"✅ Proxy authorized: {proxy_info['proxy_name']}")
        print(f"   Assigns tier: {proxy_info['tier_id']}")
        print(f"   Rate limit: {proxy_info.get('rate_limit', 'unlimited')}/hour")

        print("\n2. End user 'bob' calls get_weather via proxy")

        # Proxy provides its own metadata structure
        # Different proxies can include different fields
        proxy_info_with_context = {
            "proxy_name": proxy_info["proxy_name"],
            # Proxy decides what information to include:
            "platform_user_id": "bob",           # User on the platform
            "proxy_server_id": "shared_proxy_1", # Which proxy server
            "session_id": "sess_abc123"          # Session tracking
        }

        usage_result = await server.record_tool_usage(
            tool_name="get_weather",
            user_id=proxy_info["proxy_name"],  # Proxy is the "customer"
            proxy_info=proxy_info_with_context
        )

        if usage_result:
            print("\n✅ Usage recorded:")
            print(f"   Transaction ID: {usage_result.get('transaction_id')}")
            print(f"   Customer (Proxy): {usage_result.get('user_id')}")
            print(f"   Tool: {usage_result.get('tool_name')}")
            print(f"   Quantity: {usage_result.get('quantity')}")
            print(f"   Via Proxy: {usage_result.get('via_proxy')}")
            # All proxy-provided fields are returned
            print(f"   Platform User: {usage_result.get('platform_user_id')}")
            print(f"   Proxy Server: {usage_result.get('proxy_server_id')}")
            print(f"   Session: {usage_result.get('session_id')}")

    print("\n" + "-" * 70)
    print("Scenario 3: Proxy Platform Handles Pricing")
    print("-" * 70)

    print("\nThe proxy platform receives usage information and handles:")
    print("1. Pricing: Query its pricing database")
    print("   Example: get_weather = $0.01 per call")
    print("\n2. Charging: Charge end user 'bob'")
    print("   Example: charge(bob, $0.01)")
    print("\n3. Revenue Sharing: Based on commercial agreement")
    print("   Example: 70% to developer, 30% to platform")
    print("\n4. Settlement: Record payables and revenues")
    print("   Example: payable_to_developer($0.007), platform_revenue($0.003)")

    print("\n" + "=" * 70)
    print("Key Points:")
    print("=" * 70)
    print("✅ Developer's server: Records usage quantity and metadata")
    print("✅ Proxy platform: Handles pricing, billing, and revenue sharing")
    print("✅ Clear separation of concerns!")

    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
