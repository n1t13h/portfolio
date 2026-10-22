"""End-to-end check of the local docker stack: `docker compose up -d`, then
`uv run python scripts/smoke_local.py`.

It resets the LOCAL admin (new password + 2FA secret each run), logs in, uploads a generated
photo through the presigned-URL flow, publishes it, and reads it back as the public would.
"""

import io
import re
import subprocess
import sys

import httpx
import pyotp
from PIL import Image

API = "http://localhost:8000"
ADMIN = f"{API}/a/local-admin-path-0123456789"
PASSWORD = "local-smoke-password"


def step(message: str) -> None:
    print(f"- {message}")


def reset_admin() -> str:
    """Returns the TOTP secret of a freshly reset local admin."""
    out = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "-m",
            "app.cli",
            "reset-admin",
            "smoke",
        ],
        input=f"{PASSWORD}\n{PASSWORD}\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return re.search(r"secret=([A-Z2-7]+)", out).group(1)  # type: ignore[union-attr]


def main() -> int:
    secret = reset_admin()
    step("admin reset, got a 2FA secret")

    with httpx.Client(headers={"X-CSRF": "1"}, timeout=30) as http:
        r = http.post(
            f"{ADMIN}/auth/login",
            json={"username": "smoke", "password": PASSWORD, "code": "000000"},
        )
        assert r.status_code == 401, r.text
        step("wrong 2FA code refused")

        r = http.post(
            f"{ADMIN}/auth/login",
            json={"username": "smoke", "password": PASSWORD, "code": pyotp.TOTP(secret).now()},
        )
        assert r.status_code == 200, r.text
        # The cookie is Secure, which a plain-http client will not send back; pass it by hand.
        http.headers["Cookie"] = f"portfolio_session={r.cookies['portfolio_session']}"
        assert http.get(f"{ADMIN}/auth/me").json() == {"username": "smoke"}
        step("logged in with password + TOTP")

        ticket = http.post(f"{ADMIN}/photos/upload-url").json()
        buf = io.BytesIO()
        Image.new("RGB", (3000, 2000), (180, 120, 60)).save(buf, "JPEG")
        put_url = ticket["putUrl"].replace("http://s3:9090", "http://localhost:9090")
        put = httpx.put(put_url, content=buf.getvalue(), headers={"Content-Type": "image/jpeg"})
        assert put.status_code in (200, 201), put.text
        step("uploaded a 3000x2000 JPEG straight to the bucket via the presigned URL")

        photo = http.post(f"{ADMIN}/photos/{ticket['photoId']}/confirm").json()
        assert photo["status"] == "draft" and set(photo["variants"]) == {"800", "1600", "2400"}, (
            photo
        )
        step(
            f"confirmed: variants {sorted(photo['variants'])}, aspect ratio {photo['aspectRatio']}"
        )

        assert httpx.get(f"{API}/photos").json() == []
        step("draft is not public")

        http.patch(f"{ADMIN}/photos/{photo['id']}", json={"title": "Smoke test"})
        http.post(f"{ADMIN}/photos/{photo['id']}/publish")
        public = httpx.get(f"{API}/photos")
        [item] = public.json()
        assert item["title"] == "Smoke test" and item["downloadUrl"] is None
        assert public.headers["etag"] and "max-age" in public.headers["cache-control"]
        step("published: now in the public list, with ETag + Cache-Control")

        image = httpx.get(item["variants"]["800"])
        assert image.status_code == 200 and Image.open(io.BytesIO(image.content)).format == "WEBP"
        assert Image.open(io.BytesIO(image.content)).size == (800, 533)
        step("the 800px WebP variant is served from the CDN URL")

        assert (
            httpx.get(f"{API}/photos/{photo['id']}/download", follow_redirects=False).status_code
            == 404
        )
        http.put(f"{ADMIN}/photos/{photo['id']}/allow-download", json={"allow": True})
        dl = httpx.get(f"{API}/photos/{photo['id']}/download", follow_redirects=False)
        assert dl.status_code == 302, dl.text
        step("download is 404 until enabled, then redirects")

        http.delete(f"{ADMIN}/photos/{photo['id']}")
        assert httpx.get(f"{API}/photos").json() == []
        step("deleted: gone from the public list")

        assert (
            httpx.post(
                f"{API}/contact", json={"name": "A", "email": "a@b.co", "message": "hi"}
            ).status_code
            == 202
        )
        step("contact form accepted (Telegram is not configured locally, so it stays queued)")

    print("\nAll good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
