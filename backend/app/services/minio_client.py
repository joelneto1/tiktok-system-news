from datetime import timedelta
from io import BytesIO

from minio import Minio

from app.config import settings
from app.utils.logger import logger


class MinIOClient:
    """Wrapper around the MinIO Python client with convenience methods."""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        self.bucket = settings.MINIO_BUCKET

    def ensure_bucket(self):
        """Create the configured bucket if it does not already exist."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            logger.info(f"Created MinIO bucket: {self.bucket}")
        else:
            logger.info(f"MinIO bucket already exists: {self.bucket}")

    def upload_file(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes to the bucket at *path* and return the object path."""
        stream = BytesIO(data)
        self.client.put_object(
            self.bucket, path, stream, length=len(data), content_type=content_type
        )
        logger.info(f"Uploaded {len(data)} bytes to {self.bucket}/{path}")
        return path

    def upload_from_file(
        self, path: str, file_path: str, content_type: str | None = None
    ) -> str:
        """Upload a local file to the bucket at *path* and return the object path."""
        self.client.fput_object(
            self.bucket, path, file_path, content_type=content_type
        )
        logger.info(f"Uploaded file {file_path} to {self.bucket}/{path}")
        return path

    def download_file(self, path: str) -> bytes:
        """Download an object and return its contents as bytes."""
        response = self.client.get_object(self.bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def presign_url(
        self, path: str, expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate a presigned GET URL for the given object."""
        return self.client.presigned_get_object(self.bucket, path, expires=expires)

    def list_objects(self, prefix: str = "") -> list[dict]:
        """List objects under *prefix* and return a list of metadata dicts."""
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        return [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
            }
            for obj in objects
        ]

    def delete_object(self, path: str):
        """Delete a single object from the bucket."""
        self.client.remove_object(self.bucket, path)
        logger.info(f"Deleted {self.bucket}/{path}")

    def object_exists(self, path: str) -> bool:
        """Check whether an object exists in the bucket."""
        try:
            self.client.stat_object(self.bucket, path)
            return True
        except Exception:
            return False


# Singleton instance
minio_client = MinIOClient()
