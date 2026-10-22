"""Object storage (Cloudflare R2 over the S3 API) behind a small interface."""

from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.config import Config

from app.core.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class Bucket(StrEnum):
    PUBLIC = "public"  # resized WebP variants, served via the CDN domain
    PRIVATE = "private"  # originals, download copies, DB backups


class Storage(Protocol):
    def presign_put(self, bucket: Bucket, key: str, content_type: str, expires: int) -> str: ...
    def presign_get(self, bucket: Bucket, key: str, expires: int) -> str: ...
    def get_bytes(self, bucket: Bucket, key: str) -> bytes: ...
    def put_bytes(
        self,
        bucket: Bucket,
        key: str,
        data: bytes,
        content_type: str,
        cache_control: str | None = None,
    ) -> None: ...
    def delete(self, bucket: Bucket, key: str) -> None: ...
    def exists(self, bucket: Bucket, key: str) -> bool: ...
    def size(self, bucket: Bucket, key: str) -> int: ...
    def list_keys(self, bucket: Bucket, prefix: str) -> list[str]: ...
    def public_url(self, key: str) -> str: ...


class R2Storage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _make_client(self, endpoint: str) -> "S3Client":
        s = self._settings
        return boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=s.r2_access_key,
            aws_secret_access_key=s.r2_secret_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    @cached_property
    def _client(self) -> "S3Client":
        return self._make_client(self._settings.r2_endpoint)

    @cached_property
    def _signer(self) -> "S3Client":
        """Signs links for the browser: the normal endpoint unless R2_PRESIGN_ENDPOINT is set."""
        return self._make_client(self._settings.r2_presign_endpoint or self._settings.r2_endpoint)

    def _name(self, bucket: Bucket) -> str:
        s = self._settings
        return s.r2_public_bucket if bucket is Bucket.PUBLIC else s.r2_private_bucket

    def presign_put(self, bucket: Bucket, key: str, content_type: str, expires: int) -> str:
        return self._signer.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._name(bucket), "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        )

    def presign_get(self, bucket: Bucket, key: str, expires: int) -> str:
        return self._signer.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._name(bucket), "Key": key},
            ExpiresIn=expires,
        )

    def get_bytes(self, bucket: Bucket, key: str) -> bytes:
        return self._client.get_object(Bucket=self._name(bucket), Key=key)["Body"].read()

    def put_bytes(
        self,
        bucket: Bucket,
        key: str,
        data: bytes,
        content_type: str,
        cache_control: str | None = None,
    ) -> None:
        name = self._name(bucket)
        if cache_control:
            self._client.put_object(
                Bucket=name,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl=cache_control,
            )
        else:
            self._client.put_object(Bucket=name, Key=key, Body=data, ContentType=content_type)

    def delete(self, bucket: Bucket, key: str) -> None:
        self._client.delete_object(Bucket=self._name(bucket), Key=key)

    def exists(self, bucket: Bucket, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._name(bucket), Key=key)
        except self._client.exceptions.ClientError:
            return False
        return True

    def size(self, bucket: Bucket, key: str) -> int:
        head = self._client.head_object(Bucket=self._name(bucket), Key=key)
        return int(head["ContentLength"])

    def list_keys(self, bucket: Bucket, prefix: str) -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self._name(bucket), Prefix=prefix)
        return [obj["Key"] for page in pages for obj in page.get("Contents", [])]

    def public_url(self, key: str) -> str:
        return f"{self._settings.cdn_base_url.rstrip('/')}/{key}"
