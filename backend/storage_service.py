import os
from typing import Optional
from storage.providers.base import StorageProvider
from storage.providers.local import LocalStorageProvider

def build_provider() -> StorageProvider:
    provider = os.environ.get("STORAGE_PROVIDER", "local").lower()
    
    if provider == "s3":
        from storage.providers.s3 import S3StorageProvider
        bucket = os.environ.get("S3_BUCKET_NAME", "primoaudit-assets")
        region = os.environ.get("AWS_REGION", "us-east-1")
        return S3StorageProvider(bucket, region)
    
    # Default to Local
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    return LocalStorageProvider(data_dir)

# Singleton instance exported as StorageService for backward compatibility semantics
StorageService = build_provider()
