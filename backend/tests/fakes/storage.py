"""In-memory stand-ins: FakeStorage."""

from app.integrations.storage import Bucket


class FakeStorage:
    """Implements the `Storage` protocol with dicts."""

    def __init__(self, cdn_base_url: str = "https://cdn.test") -> None:
        self.cdn_base_url = cdn_base_url
        self.objects: dict[tuple[Bucket, str], tuple[bytes, str]] = {}

    def presign_put(self, bucket: Bucket, key: str, content_type: str, expires: int) -> str:
        return f"https://fake-r2/{bucket.value}/{key}?put&expires={expires}"

    def presign_get(self, bucket: Bucket, key: str, expires: int) -> str:
        return f"https://fake-r2/{bucket.value}/{key}?get&expires={expires}"

    def get_bytes(self, bucket: Bucket, key: str) -> bytes:
        return self.objects[(bucket, key)][0]

    def put_bytes(
        self,
        bucket: Bucket,
        key: str,
        data: bytes,
        content_type: str,
        cache_control: str | None = None,
    ) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    def delete(self, bucket: Bucket, key: str) -> None:
        self.objects.pop((bucket, key), None)

    def exists(self, bucket: Bucket, key: str) -> bool:
        return (bucket, key) in self.objects

    def size(self, bucket: Bucket, key: str) -> int:
        return len(self.objects[(bucket, key)][0])

    def list_keys(self, bucket: Bucket, prefix: str) -> list[str]:
        return [k for (b, k) in self.objects if b is bucket and k.startswith(prefix)]

    def public_url(self, key: str) -> str:
        return f"{self.cdn_base_url}/{key}"
