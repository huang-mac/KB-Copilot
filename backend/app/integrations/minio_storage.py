from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.core.config import Settings


class MinioDocumentStorage:
    def __init__(self, settings: Settings) -> None:
        endpoint, secure = self._parse_endpoint(settings.minio_endpoint, settings.minio_secure)
        self.client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=secure,
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket()

    def upload_document(
        self,
        *,
        kb_id: str,
        doc_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        object_name = self.build_object_name(kb_id=kb_id, doc_id=doc_id, filename=filename)
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )
        return object_name

    def download_document(self, *, kb_id: str, doc_id: str, filename: str) -> bytes:
        object_name = self.build_object_name(kb_id=kb_id, doc_id=doc_id, filename=filename)
        response = self.client.get_object(self.bucket_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_document(self, *, kb_id: str, doc_id: str, filename: str) -> None:
        object_name = self.build_object_name(kb_id=kb_id, doc_id=doc_id, filename=filename)
        try:
            self.client.remove_object(self.bucket_name, object_name)
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise

    def build_object_name(self, *, kb_id: str, doc_id: str, filename: str) -> str:
        safe_filename = Path(filename).name or "untitled.txt"
        return f"{kb_id}/{doc_id}/{safe_filename}"

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def _parse_endpoint(self, endpoint: str, secure: bool) -> tuple[str, bool]:
        parsed = urlparse(endpoint)
        if not parsed.scheme:
            return endpoint, secure

        parsed_endpoint = parsed.netloc or parsed.path
        return parsed_endpoint, parsed.scheme == "https"
