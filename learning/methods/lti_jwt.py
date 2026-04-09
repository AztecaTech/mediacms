"""LTI 1.3 OIDC id_token verification (RS256 + platform JWKS)."""

from __future__ import annotations

from typing import Any

import jwt
from jwt import PyJWKClient


class LtiIdTokenValidationError(ValueError):
    """Raised when id_token signature or claims fail validation."""


class LtiIdTokenVerifier:
    """Resolve signing key from JWKS and verify standard OIDC + nonce checks."""

    def __init__(self, jwks_uri: str):
        self._jwks_uri = (jwks_uri or "").strip()
        if not self._jwks_uri:
            raise LtiIdTokenValidationError("jwks_uri is required.")

    def verify(
        self,
        id_token: str,
        *,
        issuer: str,
        audience: str,
        nonce: str,
        leeway_seconds: int = 60,
    ) -> dict[str, Any]:
        try:
            jwks_client = PyJWKClient(self._jwks_uri, cache_keys=True)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        except Exception as exc:
            raise LtiIdTokenValidationError(f"JWKS resolution failed: {exc}") from exc
        try:
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
                leeway=int(leeway_seconds),
                options={"require": ["exp", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            raise LtiIdTokenValidationError(str(exc)) from exc
        token_nonce = claims.get("nonce")
        if not nonce or token_nonce != nonce:
            raise LtiIdTokenValidationError("nonce mismatch")
        return claims


class LtiClaimsExtractor:
    """Pull namespaced LTI 1.3 claims into a short dict for API responses."""

    _PREFIX = "https://purl.imsglobal.org/spec/lti/claim/"

    @classmethod
    def extract(cls, claims: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in claims.items():
            if isinstance(key, str) and key.startswith(cls._PREFIX):
                out[key[len(cls._PREFIX) :]] = value
        return out
