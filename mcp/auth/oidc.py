"""Verify OIDC JWT từ Keycloak + extract scopes + tenant claim."""
from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient


@dataclass(frozen=True)
class Caller:
    sub: str
    scopes: frozenset[str]
    tenant_merchant_id: str | None
    raw: dict


class AuthError(PermissionError):
    pass


class OidcVerifier:
    def __init__(self, jwks_url: str | None = None, audience: str | None = None) -> None:
        self._jwks_url = jwks_url or os.environ["OIDC_JWKS_URL"]
        self._audience = audience or os.environ.get("OIDC_AUDIENCE", "semantic-platform")
        self._jwks = PyJWKClient(self._jwks_url)

    def verify(self, token: str) -> Caller:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token).key
            decoded = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                audience=self._audience,
            )
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e
        scope_claim = decoded.get("scope") or decoded.get("scp") or ""
        scopes = frozenset(scope_claim.split() if isinstance(scope_claim, str) else list(scope_claim))
        return Caller(
            sub=str(decoded.get("sub", "")),
            scopes=scopes,
            tenant_merchant_id=decoded.get("merchant_id"),
            raw=decoded,
        )


def require_scopes(caller: Caller, required: tuple[str, ...]) -> None:
    if "public" in required:
        return
    if not all(s in caller.scopes for s in required):
        raise AuthError(f"missing scopes: required={required}, have={sorted(caller.scopes)}")
