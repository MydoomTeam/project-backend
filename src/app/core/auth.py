from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException, status

from app.core.config import settings


def _sign(payload: bytes) -> str:
    digest = hmac.new(settings.auth_secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def create_access_token(user_id: int) -> str:
    payload = json.dumps({"sub": user_id, "iat": int(time.time())}, separators=(",", ":")).encode()
    encoded_payload = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{encoded_payload}.{_sign(payload)}"


def resolve_user_id(token: str) -> int | None:
    parts = token.split(".")
    if len(parts) != 2:
        return None

    encoded_payload, signature = parts
    padding = "=" * (-len(encoded_payload) % 4)
    try:
        payload = base64.urlsafe_b64decode(encoded_payload + padding)
        expected_signature = _sign(payload)
        if not hmac.compare_digest(signature, expected_signature):
            return None
        data = json.loads(payload.decode())
        user_id = data.get("sub")
        return user_id if isinstance(user_id, int) and user_id > 0 else None
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> int:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )

    token = authorization.removeprefix("Bearer ").strip()
    user_id = resolve_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )
    return user_id


get_current_user_id = get_current_user
