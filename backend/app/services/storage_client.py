"""Cloudflare R2 / S3-compatible storage client.

Replaces MinIO with Cloudflare R2 using boto3. Since R2 is S3-compatible,
this works with any S3 endpoint (AWS S3, MinIO, R2, etc.).
"""

from datetime import timedelta
from io import BytesIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.utils.logger import logger


class StorageClient:
    """S3-compatible storage client for Cloudflare R2."""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )
        self.bucket = settings.R2_BUCKET
        self.public_url = settings.R2_PUBLIC_URL  # For public access URLs

    def ensure_bucket(self):
        """Create the configured bucket if it does not already exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"R2 bucket already exists: {self.bucket}")
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                self.client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created R2 bucket: {self.bucket}")
            else:
                logger.error(f"R2 bucket check failed: {e}")
                raise

    def upload_file(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes to the bucket at *path* and return the object path."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded {len(data)} bytes to r2://{self.bucket}/{path}")
        return path

    def upload_from_file(
        self, path: str, file_path: str, content_type: str | None = None
    ) -> str:
        """Upload a local file to the bucket at *path*."""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self.client.upload_file(
            file_path, self.bucket, path, ExtraArgs=extra_args if extra_args else None
        )
        logger.info(f"Uploaded file {file_path} to r2://{self.bucket}/{path}")
        return path

    def download_file(self, path: str) -> bytes:
        """Download an object and return its contents as bytes."""
        response = self.client.get_object(Bucket=self.bucket, Key=path)
        return response["Body"].read()

    def download_to_file(self, path: str, local_path: str):
        """Download an object to a local file."""
        self.client.download_file(self.bucket, path, local_path)
        logger.info(f"Downloaded r2://{self.bucket}/{path} to {local_path}")

    def presign_url(
        self, path: str, expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate a presigned GET URL for the given object."""
        # If public URL is configured, use it directly (R2 public bucket)
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{path}"

        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=int(expires.total_seconds()),
        )

    def list_objects(self, prefix: str = "") -> list[dict]:
        """List objects under *prefix* and return a list of metadata dicts."""
        objects = []
        paginator = self.client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                objects.append(
                    {
                        "name": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )

        return objects

    def list_folders(self, prefix: str = "") -> tuple[list[dict], list[dict]]:
        """List folders and files at the given prefix level (non-recursive).

        Returns (folders, files) where folders are common prefixes.
        """
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        response = self.client.list_objects_v2(
            Bucket=self.bucket, Prefix=prefix, Delimiter="/"
        )

        folders = [
            {"name": cp["Prefix"], "is_dir": True}
            for cp in response.get("CommonPrefixes", [])
        ]
        files = [
            {
                "name": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"],
                "is_dir": False,
            }
            for obj in response.get("Contents", [])
            if obj["Key"] != prefix  # Exclude the prefix itself
        ]

        return folders, files

    def delete_object(self, path: str):
        """Delete a single object from the bucket."""
        self.client.delete_object(Bucket=self.bucket, Key=path)
        logger.info(f"Deleted r2://{self.bucket}/{path}")

    def delete_objects(self, paths: list[str]):
        """Delete multiple objects at once."""
        if not paths:
            return
        objects = [{"Key": p} for p in paths]
        self.client.delete_objects(
            Bucket=self.bucket, Delete={"Objects": objects}
        )
        logger.info(f"Deleted {len(paths)} objects from r2://{self.bucket}")

    def object_exists(self, path: str) -> bool:
        """Check whether an object exists in the bucket."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except ClientError:
            return False

    def get_object_info(self, path: str) -> dict | None:
        """Get metadata for an object."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=path)
            return {
                "size": response["ContentLength"],
                "content_type": response.get("ContentType", ""),
                "last_modified": response["LastModified"],
            }
        except ClientError:
            return None


# Singleton — used throughout the app as `storage_client`
storage_client = StorageClient()

# Backward-compatible alias (many modules import minio_client)
minio_client = storage_client
