from app.services.minio_client import minio_client
from app.utils.logger import logger


class AssetManager:
    """Manages MinIO asset paths and naming conventions for pipeline jobs."""

    @staticmethod
    def get_job_prefix(job_id: str) -> str:
        """Get MinIO prefix for a job's assets."""
        return f"jobs/{job_id}"

    @staticmethod
    def get_stage_path(job_id: str, stage: str, filename: str) -> str:
        """Get full MinIO path for a stage asset."""
        return f"jobs/{job_id}/{stage}/{filename}"

    @staticmethod
    def save_asset(
        job_id: str,
        stage: str,
        filename: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload an asset to MinIO and return the path."""
        path = f"jobs/{job_id}/{stage}/{filename}"
        minio_client.upload_file(path, data, content_type)
        logger.debug(f"Saved asset: {path} ({len(data)} bytes)")
        return path

    @staticmethod
    def save_asset_from_file(
        job_id: str,
        stage: str,
        filename: str,
        local_path: str,
        content_type: str | None = None,
    ) -> str:
        """Upload a local file to MinIO and return the path."""
        path = f"jobs/{job_id}/{stage}/{filename}"
        minio_client.upload_from_file(path, local_path, content_type)
        logger.debug(f"Saved asset from file: {path}")
        return path

    @staticmethod
    def get_asset_url(path: str) -> str:
        """Get presigned URL for an asset."""
        return minio_client.presign_url(path)

    @staticmethod
    def download_asset(path: str) -> bytes:
        """Download an asset from MinIO."""
        return minio_client.download_file(path)

    @staticmethod
    def cleanup_job(job_id: str) -> None:
        """Remove all assets for a job from MinIO."""
        prefix = f"jobs/{job_id}/"
        objects = minio_client.list_objects(prefix)
        for obj in objects:
            minio_client.delete_object(obj["name"])
        logger.info(f"Cleaned up {len(objects)} assets for job {job_id}")

    @staticmethod
    def list_job_assets(job_id: str) -> list[dict]:
        """List all assets for a job."""
        prefix = f"jobs/{job_id}/"
        return minio_client.list_objects(prefix)

    @staticmethod
    def try_download_text(job_id: str, stage: str, filename: str) -> str | None:
        """Try to download a text asset. Returns None if not found."""
        path = f"jobs/{job_id}/{stage}/{filename}"
        try:
            data = minio_client.download_file(path)
            return data.decode("utf-8")
        except Exception:
            return None

    @staticmethod
    def try_get_asset_path(job_id: str, stage: str, filename: str) -> str | None:
        """Check if an asset exists and return its path, or None."""
        path = f"jobs/{job_id}/{stage}/{filename}"
        try:
            minio_client.client.stat_object(minio_client.bucket, path)
            return path
        except Exception:
            return None


# Singleton
asset_manager = AssetManager()
