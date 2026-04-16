import hashlib
import secrets

from fastapi import HTTPException, Request, status

ADMIN_SESSION_KEY = "admin_authenticated"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"aim_{secrets.token_urlsafe(24)}"


def sign_in_admin_session(request: Request) -> None:
    request.session[ADMIN_SESSION_KEY] = True


def clear_admin_session(request: Request) -> None:
    request.session.clear()


def has_admin_session(request: Request) -> bool:
    return bool(request.session.get(ADMIN_SESSION_KEY))


def require_admin_session(request: Request) -> None:
    if has_admin_session(request):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin sign-in required")
