"""Rejects oversized request bodies before they are read into memory."""

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class _TooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    """Pure ASGI middleware: 413 for a body over `max_bytes`, declared or streamed."""

    def __init__(
        self, app: Callable[[Scope, Receive, Send], Awaitable[None]], max_bytes: int
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send)
            return

        received = 0
        exceeded = False
        responded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise _TooLarge
            return message

        async def guarded_send(message: Message) -> None:
            # Whatever the app makes of the aborted read (FastAPI turns it into a 400), the
            # client is told 413. Only the first response message triggers it; the rest are dropped.
            nonlocal responded
            if not exceeded:
                await send(message)
            elif not responded:
                responded = True
                await self._reject(send)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _TooLarge:
            if not responded:
                await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"request body too large"}'
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        await send({"type": "http.response.start", "status": 413, "headers": headers})
        await send({"type": "http.response.body", "body": body})
