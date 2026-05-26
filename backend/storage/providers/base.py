import abc
from typing import Optional

class StorageProvider(abc.ABC):
    """Abstract interface for storing and retrieving evidence assets."""
    
    @abc.abstractmethod
    def save_file(self, filename: str, byte_stream: bytes, sub_folder: str = "") -> str:
        """Saves a file and returns its tracking storage key."""
        pass
        
    @abc.abstractmethod
    def generate_thumbnail(self, storage_key: str, asset_type: str) -> Optional[str]:
        """Generates a compressed thumbnail representation of a file and returns its storage key."""
        pass
        
    @abc.abstractmethod
    def get_file_path(self, storage_key: str) -> str:
        """
        Returns a local file system path pointing to the file.
        For cloud providers (S3), this should transparently pull the file into a temporary 
        directory and return the temp path.
        """
        pass
        
    @abc.abstractmethod
    def get_file_stream(self, storage_key: str):
        """
        Returns a byte stream or file object for reading.
        """
        pass
