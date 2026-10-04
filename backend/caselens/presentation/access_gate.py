"""A shared access code in front of the whole API (only when ACCESS_CODE is set).

The student gives the code to the people who may use the app. A correct code sets a cookie, so the browser
(and a plain download link) is let in without sending the code again. /health stays open for the keep-awake ping.
"""
import hashlib
import hmac
import threading
import time
from collections import deque

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caselens.infrastructure.config import get_settings

COOKIE = "caselens_access"
_OPEN_PATHS = ("/health", "/access")
_MAX_WRONG_PER_MINUTE = 10
_MAX_WRONG_PER_MINUTE_ALL = 60  # all clients together: a guesser who fakes addresses still cannot go faster than this
_MAX_CLIENTS = 1000  # bound on remembered clients; past it, newcomers share one bucket, so memory cannot be filled
_OVERFLOW = "overflow"
_wrong_attempts: dict[str, deque[float]] = {}
_all_wrong: deque[float] = deque()
_lock = threading.Lock()  # the endpoint runs on several threads at once

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
    """Who is guessing: the browser's address as the host's proxy reports it, so one person's wrong tries do not
    lock out the others. A client can fake this header, so it is only a convenience: the limit for all clients
    together (`_MAX_WRONG_PER_MINUTE_ALL`) and the cap on remembered clients are what hold against a guesser."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


class AccessIn(BaseModel):
    code: str


@router.get("/access")
def access_status(request: Request) -> dict:
    return {"required": get_settings().access_code is not None, "granted": _allowed(request)}


def _reserve_try(request: Request) -> tuple[deque[float], float] | None:
    """Count this try now, before the code is compared, all under one lock: parallel guesses are each counted
    before any of them is judged, so a burst cannot slip past the limit. None means the limit is reached."""
    with _lock:
        now = time.monotonic()
        while _all_wrong and now - _all_wrong[0] > 60:
            _all_wrong.popleft()
        for key in [k for k, v in _wrong_attempts.items() if not v or now - v[-1] > 60]:
            del _wrong_attempts[key]  # forget clients with no recent tries
        client = _client_key(request)
        if client not in _wrong_attempts and len(_wrong_attempts) >= _MAX_CLIENTS:
            client = _OVERFLOW
        tries = _wrong_attempts.setdefault(client, deque())
        while tries and now - tries[0] > 60:
            tries.popleft()
        if len(tries) >= _MAX_WRONG_PER_MINUTE or len(_all_wrong) >= _MAX_WRONG_PER_MINUTE_ALL:
            return None
        tries.append(now)
        _all_wrong.append(now)
        return tries, now


def _forgive(tries: deque[float], stamp: float) -> None:
    """The code was right, so that try was not a mistake."""
    with _lock:
        for line in (tries, _all_wrong):
            try:
                line.remove(stamp)
            except ValueError:
                pass  # already aged out


@router.post("/access")
def enter_access_code(body: AccessIn, request: Request, response: Response):
    code = get_settings().access_code
    if code is None:
        return {"required": False, "granted": True}
    reserved = _reserve_try(request)
    if reserved is None:
        return JSONResponse({"detail": "Too many tries. Wait a minute."}, status_code=429)
    if not hmac.compare_digest(_token(body.code.strip()), _token(code)):
        return JSONResponse({"detail": "That code is not right."}, status_code=401)
    _forgive(*reserved)
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(
        COOKIE, _token(code), max_age=30 * 24 * 3600, httponly=True, samesite="lax", secure=secure, path="/"
    )
    return {"required": True, "granted": True}
