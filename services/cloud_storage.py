import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("athena.cloud")

class CloudStorageService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CloudStorageService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.bucket_name = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = None
        self.bucket = None
        
        if self.bucket_name:
            try:
                # Assuming credentials are set via GOOGLE_APPLICATION_CREDENTIALS or gcloud auth
                self.client = storage.Client(project=self.project_id)
                self.bucket = self.client.bucket(self.bucket_name)
                self.initialized = True
            except Exception as e:
                logger.warning(f"Cloud Storage init failed: {e}")

    def upload_text(self, content: str, destination_blob_name: str) -> bool:
        """Upload text content to a file in the bucket."""
        if not self.initialized or not self.bucket:
            return False
            
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_string(content)
            return True
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False

    def upload_json(self, data: Any, destination_blob_name: str) -> bool:
        """Upload JSON data to a file in the bucket."""
        return self.upload_text(json.dumps(data, indent=2), destination_blob_name)

    def upload_file(self, source_file_path: str, destination_blob_name: str) -> bool:
        """Upload a local file to the bucket."""
        if not self.initialized or not self.bucket:
            return False
            
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_path)
            return True
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False

    def list_files(self, prefix: str = None) -> list[str]:
        """List files in the bucket with an optional prefix."""
        if not self.initialized or not self.bucket:
            return []
            
        try:
            blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"List files failed: {e}")
            return []

_cloud_instance = None

def get_cloud_storage():
    global _cloud_instance
    if _cloud_instance is None:
        _cloud_instance = CloudStorageService()
    return _cloud_instance