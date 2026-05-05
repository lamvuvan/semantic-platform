"""Layer 4 auth — verify JWT của AI agent + extract scopes + merchant.

Trust model:
- Agent có 1 JWT do internal IdP (Keycloak) cấp.
- JWT claims yêu cầu: `sub` (agent_id), `merchant_id`, `scope` (space-separated).
- MCP server verify chữ ký bằng JWKS cache, sau đó chèn header trusted khi gọi
  Layer 3 Domain Service qua mTLS — tham khảo `mcp_server/domain_client.py`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient


class AuthError(PermissionError):
    pass


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    merchant_id: str
    scopes: frozenset[str]
    raw: dict


class JwtVerifier:
    def __init__(self, jwks_url: str | None = None, audience: str | None = None) -> None:
        self._jwks_url = jwks_url or os.environ["MCP_JWKS_URL"]
        self._audience = audience or os.environ.get("MCP_AUDIENCE", "semantic-platform-mcp")
        self._jwks = PyJWKClient(self._jwks_url, cache_keys=True, max_cached_keys=16)

    def verify(self, token: str) -> AgentIdentity:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token).key
            decoded = jwt.decode(token, key=signing_key, algorithms=["RS256"], audience=self._audience)
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e

        agent_id = decoded.get("sub")
        merchant_id = decoded.get("merchant_id")
        if not agent_id or not merchant_id:
            raise AuthError("missing sub or merchant_id in JWT")

        scope_claim = decoded.get("scope") or decoded.get("scp") or ""
        scopes = frozenset(scope_claim.split() if isinstance(scope_claim, str) else list(scope_claim))
        return AgentIdentity(
            agent_id=agent_id,
            merchant_id=merchant_id,
            scopes=scopes,
            raw=decoded,
        )


def require_scopes(identity: AgentIdentity, required: tuple[str, ...]) -> None:
    if "public" in required:
        return
    if not all(s in identity.scopes for s in required):
        raise AuthError(f"missing scopes: required={required}, have={sorted(identity.scopes)}")
