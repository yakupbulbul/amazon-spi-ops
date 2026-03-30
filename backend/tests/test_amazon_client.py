from app.core.config import Settings
from app.services.amazon.client import AmazonSpApiClient


class RecordingHttpClient:
    def __init__(self) -> None:
        self.post_calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object):
        self.post_calls.append({"url": url, **kwargs})
        return type("Response", (), {"is_error": False, "status_code": 204, "text": ""})()


def build_settings() -> Settings:
    return Settings(
        APP_ENV="test",
        SECRET_KEY="secret",
        DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",
        LWA_CLIENT_ID="lwa-client",
        LWA_CLIENT_SECRET="lwa-secret",
        AWS_ACCESS_KEY_ID="aws-key",
        AWS_SECRET_ACCESS_KEY="aws-secret",
        LWA_REFRESH_TOKEN="refresh-token",
        MARKETPLACE_ID="A1PA6795UKMFR9",
        SELLER_ID="A2PPR7BXWKCBTV",
    )


def test_upload_to_destination_drops_query_duplicate_form_fields() -> None:
    http_client = RecordingHttpClient()
    client = AmazonSpApiClient(build_settings(), http_client=http_client)

    client.upload_to_destination(
        url="https://uploads.example.com/content?acl=bucket-owner-full-control&policy=signed-policy",
        form_fields={
            "acl": "bucket-owner-full-control",
            "policy": "signed-policy",
            "key": "aplus/asset.jpg",
            "x-amz-meta-origin": "studio",
        },
        file_name="asset.jpg",
        content=b"binary-image",
        content_type="image/jpeg",
    )

    assert len(http_client.post_calls) == 1
    payload = http_client.post_calls[0]
    assert payload["data"] == {
        "key": "aplus/asset.jpg",
        "x-amz-meta-origin": "studio",
    }
