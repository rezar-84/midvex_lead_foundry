from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import boto3
from django.conf import settings


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str


def store_raw(organization_id: object, message_id: str, payload: bytes) -> StoredObject:
    digest = hashlib.sha256(payload).hexdigest()
    key = f"organizations/{organization_id}/messages/{message_id}/{digest}.eml"
    if settings.RAW_STORAGE_BACKEND == "filesystem":
        root = Path(settings.RAW_STORAGE_ROOT).resolve()
        target = (root / key).resolve()
        if root not in target.parents:
            raise ValueError("Unsafe evidence object key")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    elif settings.RAW_STORAGE_BACKEND == "s3":
        if not settings.S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required")
        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        )
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=payload,
            ServerSideEncryption="AES256",
            ContentType="message/rfc822",
        )
    else:
        raise RuntimeError("Unsupported RAW_STORAGE_BACKEND")
    return StoredObject(key=key, sha256=digest)
