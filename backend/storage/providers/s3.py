import os
import uuid
import tempfile
import boto3
from PIL import Image
from typing import Optional
from .base import StorageProvider

class S3StorageProvider(StorageProvider):
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket = bucket_name
        self.s3_client = boto3.client("s3", region_name=region)
        self.local_cache = tempfile.gettempdir()

    def save_file(self, filename: str, byte_stream: bytes, sub_folder: str = "") -> str:
        ext = os.path.splitext(filename)[1].lower() if filename else ".bin"
        if not ext: ext = ".bin"
        
        base_name = f"{uuid.uuid4().hex}{ext}"
        key = f"uploads/{sub_folder}/{base_name}" if sub_folder else f"storage/{base_name}"
        
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=byte_stream
        )
        return key

    def generate_thumbnail(self, storage_key: str, asset_type: str) -> Optional[str]:
        # Temporarily download to local for PIL / PyMuPDF parsing
        local_path = self.get_file_path(storage_key)
        if not os.path.exists(local_path):
            return None
            
        parts = storage_key.split("/")
        folder_prefix = "/".join(parts[:-1]) if len(parts) > 1 else "storage"
        
        thumb_key = None
        thumb_path = None
        
        try:
            if asset_type == 'image':
                with Image.open(local_path) as img:
                    img.thumbnail((300, 300))
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    thumb_key = f"{folder_prefix}/thumb_{uuid.uuid4().hex}.jpg"
                    thumb_path = os.path.join(self.local_cache, os.path.basename(thumb_key))
                    img.save(thumb_path, "JPEG")
            elif asset_type == 'pdf':
                import fitz
                doc = fitz.open(local_path)
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                    thumb_key = f"{folder_prefix}/thumb_{uuid.uuid4().hex}.png"
                    thumb_path = os.path.join(self.local_cache, os.path.basename(thumb_key))
                    pix.save(thumb_path)
                    
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, "rb") as f:
                    self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=thumb_key,
                        Body=f.read()
                    )
                os.remove(thumb_path)
                return thumb_key
                
        except Exception as e:
            print(f"Failed to generate thumbnail for S3 object {storage_key}: {str(e)}")
            
        return None

    def get_file_path(self, storage_key: str) -> str:
        local_path = os.path.join(self.local_cache, os.path.basename(storage_key))
        if not os.path.exists(local_path):
            try:
                self.s3_client.download_file(self.bucket, storage_key, local_path)
            except Exception as e:
                pass
        return local_path
        
    def get_file_stream(self, storage_key: str):
        response = self.s3_client.get_object(Bucket=self.bucket, Key=storage_key)
        return response['Body']
