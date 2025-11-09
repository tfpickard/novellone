from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from config import AppSettings, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    ok: bool
    username: str
    expires_in: int


class LogoutResponse(BaseModel):
    ok: bool


@dataclass(slots=True)
class AdminSession:
    username: str
    roles: tuple[str, ...]
    expires_at: int

    def has_role(self, role: str) -> bool:
        return role in self.roles


class AuthError(Exception):
    """Raised when session tokens are invalid or expired."""


def hash_password(password: str) -> str:
    """Return a bcrypt hash suitable for storing in configuration."""
    return pwd_context.hash(password)


def verify_password(candidate: str, hashed: str) -> bool:
    """Verify that the provided password matches the stored hash."""
    try:
        return pwd_context.verify(candidate, hashed)
    except ValueError:
        # Raised when the hash is malformed or unsupported
        return False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_session_token(
    *, username: str, roles: Iterable[str], secret: str, ttl_seconds: int
) -> str:
    expires_at = int(time.time()) + ttl_seconds
    payload = {
        "sub": username,
        "roles": list(dict.fromkeys(roles)),
        "exp": expires_at,
    }
    payload_bytes = _canonical_json(payload)
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_b64encode(payload_bytes)}.{_b64encode(signature)}"


def parse_session_token(token: str, *, secret: str) -> AdminSession:
    try:
        payload_b64, signature_b64 = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise AuthError("Malformed session token") from exc

    payload_bytes = _b64decode(payload_b64)
    provided_signature = _b64decode(signature_b64)
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).digest()

    if not hmac.compare_digest(provided_signature, expected_signature):
        raise AuthError("Invalid session signature")

    try:
        payload: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthError("Unable to decode session payload") from exc

    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(time.time()):
        raise AuthError("Session expired")

    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        raise AuthError("Invalid session payload")

    raw_roles = payload.get("roles", [])
    if not isinstance(raw_roles, list) or not all(isinstance(r, str) for r in raw_roles):
        raise AuthError("Invalid session payload")

    roles_tuple = tuple(dict.fromkeys(raw_roles))
    return AdminSession(username=username, roles=roles_tuple, expires_at=expires_at)


def _cookie_kwargs(settings: AppSettings) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": settings.session_cookie_samesite.lower(),
        "max_age": settings.session_ttl_seconds,
        "path": "/",
    }
    if settings.session_cookie_domain:
        kwargs["domain"] = settings.session_cookie_domain
    return kwargs


def set_session_cookie(response: Response, token: str, settings: AppSettings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        **_cookie_kwargs(settings),
    )


def clear_session_cookie(response: Response, settings: AppSettings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
    )


async def require_admin(request: Request, settings: AppSettings = Depends(get_settings)) -> AdminSession:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        session = parse_session_token(token, secret=settings.session_secret)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if not session.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return session


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response, settings: AppSettings = Depends(get_settings)) -> LoginResponse:
    if payload.username != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not verify_password(payload.password, settings.admin_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_session_token(
        username=settings.admin_username,
        roles=("admin",),
        secret=settings.session_secret,
        ttl_seconds=settings.session_ttl_seconds,
    )
    set_session_cookie(response, token, settings)

    ttl = settings.session_ttl_seconds
    return LoginResponse(ok=True, username=settings.admin_username, expires_in=ttl)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response, settings: AppSettings = Depends(get_settings)) -> LogoutResponse:
    clear_session_cookie(response, settings)
    return LogoutResponse(ok=True)


def _usage() -> int:
    print("Usage:", file=sys.stderr)
    print("  python -m backend.auth hash-password <plaintext>", file=sys.stderr)
    return 1


def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        return _usage()
    command = argv[1]
    if command == "hash-password":
        if len(argv) != 3:
            return _usage()
        print(hash_password(argv[2]))
        return 0
    return _usage()


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))


__all__ = [
    "AdminSession",
    "AuthError",
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
    "clear_session_cookie",
    "create_session_token",
    "hash_password",
    "login",
    "logout",
    "parse_session_token",
    "require_admin",
    "router",
    "set_session_cookie",
    "verify_password",
]

