from collections.abc import Iterator

from fastapi.testclient import TestClient

VALID = {"name": "Asha", "email": "asha@example.com", "message": "hello"}


def test_oversized_declared_body_is_refused_before_it_is_read(client: TestClient) -> None:
    resp = client.post(
        "/contact", content=b"x" * 2_000_000, headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 413


def test_oversized_streamed_body_is_refused_too(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(40):
            yield b"x" * 50_000

    resp = client.post("/contact", content=chunks(), headers={"Content-Type": "application/json"})
    assert resp.status_code == 413


def test_normal_requests_are_unaffected(client: TestClient) -> None:
    assert client.post("/contact", json=VALID).status_code == 202
