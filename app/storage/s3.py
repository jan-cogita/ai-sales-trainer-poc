import boto3
from botocore.exceptions import ClientError

from app.storage.base import StorageBackend


class S3Storage(StorageBackend):
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region: str = "us-east-1", #TODO change
        prefix: str = "",
    ):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

    def _get_key(self, path: str) -> str:
        """Get full S3 key with prefix."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path

    async def save(self, path: str, content: bytes) -> str:
        """Save content to S3."""
        key = self._get_key(path)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
        )
        return f"s3://{self.bucket_name}/{key}"

    async def load(self, path: str) -> bytes:
        """Load content from S3."""
        key = self._get_key(path)
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {path}")
            raise

    async def delete(self, path: str) -> None:
        """Delete file from S3."""
        key = self._get_key(path)
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

    async def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        key = self._get_key(path)
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def list_files(self, prefix: str = "") -> list[str]:
        """List files in S3 with optional prefix."""
        search_prefix = self._get_key(prefix) if prefix else self.prefix
        files = []

        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=search_prefix)

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Remove prefix to get relative path
                if self.prefix and key.startswith(self.prefix + "/"):
                    key = key[len(self.prefix) + 1 :]
                files.append(key)

        return files
