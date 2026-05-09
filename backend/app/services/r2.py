import asyncio
from functools import lru_cache
from typing import IO

import boto3
from botocore.client import BaseClient
from botocore.response import StreamingBody

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _get_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def _r2_key(session_id: str) -> str:
    return f"tmp/{session_id}/video.mp4"


async def upload_fileobj(file_obj: IO[bytes], session_id: str) -> None:
    settings = get_settings()
    client = _get_client()
    key = _r2_key(session_id)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upload_fileobj(file_obj, settings.r2_bucket_name, key),
    )


async def get_streaming_body(session_id: str) -> StreamingBody:
    settings = get_settings()
    client = _get_client()
    key = _r2_key(session_id)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.get_object(Bucket=settings.r2_bucket_name, Key=key),
    )
    return response["Body"]


async def delete_object(session_id: str) -> None:
    settings = get_settings()
    client = _get_client()
    key = _r2_key(session_id)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.delete_object(Bucket=settings.r2_bucket_name, Key=key),
    )
