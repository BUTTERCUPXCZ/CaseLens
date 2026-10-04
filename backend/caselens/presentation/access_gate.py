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
_wrong_attempts: deque[float] = deque()

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
    while _wrong_attempts and now - _wrong_attempts[0] > 60:
        _wrong_attempts.popleft()
    if len(_wrong_attempts) >= _MAX_WRONG_PER_MINUTE:
        return JSONResponse({"detail": "Too many tries. Wait a minute."}, status_code=429)
    if not hmac.compare_digest(_token(body.code.strip()), _token(code)):
        _wrong_attempts.append(now)
        return JSONResponse({"detail": "That code is not right."}, status_code=401)
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(
        COOKIE, _token(code), max_age=30 * 24 * 3600, httponly=True, samesite="lax", secure=secure, path="/"
    )
    return {"required": True, "granted": True}
