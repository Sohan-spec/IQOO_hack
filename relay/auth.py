"""HMAC device tokens: `{merchant_id}.{hex(hmac_sha256(secret, merchant_id))}`."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import uuid

_MERCHANT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


class AuthError(Exception):
    pass


class DeviceAuth:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise AuthError("RELAY_SECRET is empty")
        self._secret = secret.encode("utf-8")

    def issue(self, merchant_id: str | None = None) -> tuple[str, str]:
        mid = merchant_id or str(uuid.uuid4())
        if not _MERCHANT_RE.match(mid):
            raise AuthError("merchant_id must be a UUID")
        return mid, f"{mid}.{self._mac(mid)}"

    def verify(self, token: str) -> str:
        if not token or "." not in token:
            raise AuthError("invalid token")
        merchant_id, _, provided = token.partition(".")
        if not _MERCHANT_RE.match(merchant_id) or not provided:
            raise AuthError("invalid token")
        expected = self._mac(merchant_id)
        if not hmac.compare_digest(expected, provided):
            raise AuthError("invalid token")
        return merchant_id

    def _mac(self, merchant_id: str) -> str:
        return hmac.new(self._secret, merchant_id.encode("utf-8"), hashlib.sha256).hexdigest()


def secret_from_env() -> str:
    value = os.environ.get("RELAY_SECRET", "").strip()
    if not value:
        raise AuthError("RELAY_SECRET is required")
    return value


def new_correlation_id() -> str:
    return secrets.token_hex(8)
