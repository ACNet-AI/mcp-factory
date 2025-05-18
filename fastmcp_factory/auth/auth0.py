"""Auth0 service provider module, implementing OAuth authentication based on Auth0.

This module provides an authentication service provider that integrates with Auth0,
for use with FastMCP's authentication mechanism.
"""

from typing import Any, Dict, List, Optional

import httpx
from mcp.server.auth.provider import OAuthAuthorizationServerProvider


class Auth0Provider(OAuthAuthorizationServerProvider[Any, Any, Any]):
    """Auth0Provider implements the fastmcp OAuthAuthorizationServerProvider interface.

    Used for OAuth2 authentication via Auth0.
    """

    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str,
        audience: Optional[str] = None,
    ) -> None:
        """Initialize the Auth0 authentication provider.

        Args:
            domain: Auth0 domain
            client_id: Auth0 client ID
            client_secret: Auth0 client secret
            audience: Auth0 target audience, defaults to API v2 endpoint
        """
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience or f"https://{domain}/api/v2/"
        self.token_url = f"https://{domain}/oauth/token"
        self.userinfo_url = f"https://{domain}/userinfo"

    async def get_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for token.

        Args:
            code: Authorization code
            redirect_uri: Redirect URI

        Returns:
            Dictionary containing access_token and other information
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "audience": self.audience,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Get user information using access token.

        Args:
            access_token: Access token

        Returns:
            User information
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.userinfo_url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def validate_token(self, access_token: str) -> bool:
        """Validate token validity (usually successful userinfo fetch indicates valid token).

        Args:
            access_token: Access token to validate

        Returns:
            Validation result, True for valid, False for invalid
        """
        try:
            await self.get_userinfo(access_token)
            return True
        except Exception:
            return False

    async def get_user_for_token(self, access_token: str) -> Dict[str, Any]:
        """Return user information (dict) based on access_token.

        Extracts key user data and processes role permission information, supporting
        FastMCP's role-based permission control.

        Note: The location of role information depends on Auth0 configuration,
        and may need to be adjusted based on your specific setup.

        Args:
            access_token: User's access token

        Returns:
            User information with roles and admin status
        """
        try:
            user_info = await self.get_userinfo(access_token)

            # Get role information from Auth0 - typically in metadata or namespace
            # 1. Get roles from namespace (recommended, default in newer Auth0 versions)
            roles: List[str] = user_info.get("https://your-domain.com/roles", [])

            # Alternative namespace formats that might be used:
            # roles = user_info.get(f"https://{self.domain}/roles", [])

            # 2. Get roles from app_metadata (common in older versions)
            # roles = user_info.get("app_metadata", {}).get("roles", [])

            # 3. Get from permissions (when using RBAC)
            # roles = user_info.get("permissions", [])

            return {
                "id": user_info.get("sub"),
                "name": user_info.get("name"),
                "email": user_info.get("email"),
                "roles": roles,  # Add role information
                "is_admin": "admin" in roles,  # For easier permission checks
                "raw": user_info,  # Keep original data for reference
            }
        except Exception as e:
            return {"error": str(e), "roles": [], "is_admin": False}
