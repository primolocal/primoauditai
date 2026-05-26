import os
import uuid
from PIL import Image
from typing import Optional
from .base import StorageProvider
from logging_config import get_logger

logger = get_logger("primoaudit.storage")

class LocalStorageProvider(StorageProvider):
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(os.path.join(self.data_dir, "storage"), exist_ok=True)

    def save_file(self, filename: str, byte_stream: bytes, sub_folder: str = "") -> str:
        ext = os.path.splitext(filename)[1].lower()
        if not ext:
            ext = ".bin"
            
        base_name = f"{uuid.uuid4().hex}{ext}"
        if sub_folder:
            key = f"uploads/{sub_folder}/{base_name}"
        else:
            key = f"storage/{base_name}"
            
        path = os.path.join(self.data_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "wb") as f:
            f.write(byte_stream)
        return key

    def generate_thumbnail(self, storage_key: str, asset_type: str) -> Optional[str]:
        source_path = os.path.join(self.data_dir, storage_key)
        if not os.path.exists(source_path):
            return None
            
        parts = storage_key.split("/")
        folder_prefix = "/".join(parts[:-1]) if len(parts) > 1 else "storage"
            
        try:
            if asset_type == 'image':
                with Image.open(source_path) as img:
                    img.thumbnail((300, 300))
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    thumb_key = f"{folder_prefix}/thumb_{uuid.uuid4().hex}.jpg"
                    thumb_path = os.path.join(self.data_dir, thumb_key)
                    img.save(thumb_path, "JPEG")
                return thumb_key
            elif asset_type == 'pdf':
                import fitz # PyMuPDF
                doc = fitz.open(source_path)
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                    thumb_key = f"{folder_prefix}/thumb_{uuid.uuid4().hex}.png"
                    thumb_path = os.path.join(self.data_dir, thumb_key)
                    pix.save(thumb_path)
                    return thumb_key
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail for {storage_key}: {e}")
            
        return None

    def get_file_path(self, storage_key: str) -> str:
        return os.path.join(self.data_dir, storage_key)

    def get_file_stream(self, storage_key: str):
        path = self.get_file_path(storage_key)
        return open(path, "rb")

    def read_file_bytes(self, storage_key: str) -> Optional[bytes]:
        path = self.get_file_path(storage_key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()
