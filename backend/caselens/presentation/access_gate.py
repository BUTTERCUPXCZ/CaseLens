"""A shared access code in front of the whole API (only when ACCESS_CODE is set).

The student gives the code to the people who may use the app. A correct code sets a cookie, so the browser
(and a plain download link) is let in without sending the code again. /health stays open for the keep-awake ping.
"""
import hashlib
import hmac
import time
from collections import deque

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caselens.infrastructure.config import get_settings

COOKIE = "caselens_access"
_OPEN_PATHS = ("/health", "/access")
_MAX_WRONG_PER_MINUTE = 10
_MAX_CLIENTS = 1000  # bound on remembered clients, so the table itself cannot be used to fill memory
_wrong_attempts: dict[str, deque[float]] = {}

router = APIRouter(tags=["access"])


def _token(code: str) -> str:
    return hashlib.sha256(f"caselens-access:{code}".encode()).hexdigest()


def _allowed(request: Request) -> bool:
    code = get_settings().access_code
    if code is None:
        return True
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), _token(code))


async def require_access_code(request: Request, call_next):
    if request.url.path in _OPEN_PATHS or _allowed(request):
        return await call_next(request)
    return JSONResponse({"detail": "An access code is needed."}, status_code=401)


def _client_key(request: Request) -> str:
    """Who is guessing: the browser's address as the host's proxy reports it, so one person's wrong tries never
    lock out the others. (A guesser who fakes this header only gets more tries; a long random code still holds.)"""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


class AccessIn(BaseModel):
    code: str


@router.get("/access")
def access_status(request: Request) -> dict:
    return {"required": get_settings().access_code is not None, "granted": _allowed(request)}


@router.post("/access")
def enter_access_code(body: AccessIn, request: Request, response: Response):
    code = get_settings().access_code
    if code is None:
        return {"required": False, "granted": True}
    now = time.monotonic()
    client = _client_key(request)
    tries = _wrong_attempts.setdefault(client, deque())
    while tries and now - tries[0] > 60:
        tries.popleft()
    if len(_wrong_attempts) > _MAX_CLIENTS:  # forget clients with no recent mistakes
        for key in [k for k, v in _wrong_attempts.items() if not v or now - v[-1] > 60]:
            del _wrong_attempts[key]
    if len(tries) >= _MAX_WRONG_PER_MINUTE:
        return JSONResponse({"detail": "Too many tries. Wait a minute."}, status_code=429)
    if not hmac.compare_digest(_token(body.code.strip()), _token(code)):
        tries.append(now)
        return JSONResponse({"detail": "That code is not right."}, status_code=401)
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(
        COOKIE, _token(code), max_age=30 * 24 * 3600, httponly=True, samesite="lax", secure=secure, path="/"
    )
    return {"required": True, "granted": True}
