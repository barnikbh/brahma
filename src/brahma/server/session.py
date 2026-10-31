"""A signed session cookie middleware (security-design.md NFR7.2, BR4.2).

The session (only the signed-in ``profileId``) is JSON, base64url-encoded and signed with
HMAC-SHA256 under ``BRAHMA_SESSION_SECRET``. The cookie is HttpOnly and SameSite=Lax and
expires after 8 hours. A cookie with a bad signature or an old timestamp is ignored, so
the request is simply signed out. Standard library only: Starlette's own
``SessionMiddleware`` needs ``itsdangerous``, which this project does not install.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

COOKIE_NAME = "brahma_session"
MAX_AGE_SECONDS = 8 * 3600


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class SessionSigner:
    """Signs and verifies session payloads."""

    def __init__(
        self, secret: str, max_age: int = MAX_AGE_SECONDS, clock: Callable[[], float] = time.time
    ) -> None:
        self._key = secret.encode("utf-8")
        self._max_age = max_age
        self._clock = clock

    def _sign(self, payload: str) -> str:
        return hmac.new(self._key, payload.encode("ascii"), hashlib.sha256).hexdigest()

    def dumps(self, session: dict[str, Any]) -> str:
        """The cookie value for a session."""
        body = json.dumps({"data": session, "iat": int(self._clock())}, separators=(",", ":"))
        payload = _b64(body.encode("utf-8"))
        return f"{payload}.{self._sign(payload)}"

    def loads(self, value: str | None) -> dict[str, Any]:
        """The session in a cookie, or an empty session when it is missing, forged or old."""
        if not value or "." not in value:
            return {}
        payload, signature = value.rsplit(".", 1)
        if not hmac.compare_digest(self._sign(payload), signature):
            return {}
        try:
            body = json.loads(_unb64(payload))
        except (ValueError, binascii.Error):
            return {}
        issued = body.get("iat")
        data = body.get("data")
        if not isinstance(issued, int) or not isinstance(data, dict):
            return {}
        if self._clock() - issued > self._max_age:
            return {}
        return data


class SignedCookieSession:
    """ASGI middleware that provides ``request.session`` from a signed cookie."""

    def __init__(self, app: ASGIApp, secret: str, max_age: int = MAX_AGE_SECONDS) -> None:
        self.app = app
        self.signer = SessionSigner(secret, max_age)
        self.max_age = max_age

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        initial = self.signer.loads(HTTPConnection(scope).cookies.get(COOKIE_NAME))
        scope["session"] = dict(initial)

        async def send_with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start" and scope["session"] != initial:
                headers = MutableHeaders(scope=message)
                headers.append("Set-Cookie", self._cookie(scope["session"]))
            await send(message)

        await self.app(scope, receive, send_with_cookie)

    def _cookie(self, session: dict[str, Any]) -> str:
        attributes = "Path=/; HttpOnly; SameSite=Lax"
        if not session:
            return f"{COOKIE_NAME}=; {attributes}; Max-Age=0"
        return f"{COOKIE_NAME}={self.signer.dumps(session)}; {attributes}; Max-Age={self.max_age}"
