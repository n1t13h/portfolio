"""ETag + Cache-Control for public JSON so Cloudflare can serve most requests itself."""

import hashlib
import json
from typing import Any

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder

CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=600"


def cached_json(request: Request, payload: Any) -> Response:
    body = json.dumps(
        jsonable_encoder(payload, by_alias=True), separators=(",", ":"), ensure_ascii=False
    ).encode()
    etag = f'"{hashlib.sha256(body).hexdigest()[:32]}"'
    headers = {"ETag": etag, "Cache-Control": CACHE_CONTROL}
    sent = [
        t.strip().removeprefix("W/") for t in request.headers.get("if-none-match", "").split(",")
    ]
    if etag in sent:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)
