import io
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.services import r2


@pytest.fixture(autouse=True)
def clear_r2_cache() -> None:
    r2._get_client.cache_clear()
    yield
    r2._get_client.cache_clear()


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.r2_endpoint_url = "https://test.r2.example.com"
    settings.r2_access_key_id = "test-key-id"
    settings.r2_secret_access_key = "test-secret"
    settings.r2_bucket_name = "test-bucket"
    return settings


async def test_upload_fileobj_calls_boto3_correctly(
    mock_settings: MagicMock,
) -> None:
    file_obj = io.BytesIO(b"test video data")
    mock_client = MagicMock()

    with (
        patch("app.services.r2._get_client", return_value=mock_client),
        patch("app.services.r2.get_settings", return_value=mock_settings),
    ):
        await r2.upload_fileobj(file_obj, "session-123")

    mock_client.upload_fileobj.assert_called_once_with(
        file_obj, "test-bucket", "tmp/session-123/video.mp4"
    )


async def test_get_streaming_body_returns_body(
    mock_settings: MagicMock,
) -> None:
    mock_body = MagicMock()
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": mock_body}

    with (
        patch("app.services.r2._get_client", return_value=mock_client),
        patch("app.services.r2.get_settings", return_value=mock_settings),
    ):
        result = await r2.get_streaming_body("session-456")

    mock_client.get_object.assert_called_once_with(
        Bucket="test-bucket", Key="tmp/session-456/video.mp4"
    )
    assert result is mock_body


async def test_delete_object_calls_boto3_correctly(
    mock_settings: MagicMock,
) -> None:
    mock_client = MagicMock()

    with (
        patch("app.services.r2._get_client", return_value=mock_client),
        patch("app.services.r2.get_settings", return_value=mock_settings),
    ):
        await r2.delete_object("session-789")

    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key="tmp/session-789/video.mp4"
    )


async def test_upload_fileobj_propagates_network_error(
    mock_settings: MagicMock,
) -> None:
    file_obj = io.BytesIO(b"test video data")
    mock_client = MagicMock()
    mock_client.upload_fileobj.side_effect = EndpointConnectionError(
        endpoint_url="https://test.r2.example.com"
    )

    with (
        patch("app.services.r2._get_client", return_value=mock_client),
        patch("app.services.r2.get_settings", return_value=mock_settings),
    ):
        with pytest.raises(EndpointConnectionError):
            await r2.upload_fileobj(file_obj, "session-err")


async def test_get_streaming_body_propagates_no_such_key(
    mock_settings: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}}, "GetObject"
    )

    with (
        patch("app.services.r2._get_client", return_value=mock_client),
        patch("app.services.r2.get_settings", return_value=mock_settings),
    ):
        with pytest.raises(ClientError):
            await r2.get_streaming_body("missing-session")


async def test_delete_object_propagates_access_denied(
    mock_settings: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "DeleteObject"
    )

    with (
        patch("app.services.r2._get_client", return_value=mock_client),
        patch("app.services.r2.get_settings", return_value=mock_settings),
    ):
        with pytest.raises(ClientError):
            await r2.delete_object("session-denied")
