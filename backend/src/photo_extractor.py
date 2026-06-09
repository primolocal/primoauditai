#!/usr/bin/env python
"""
QC Photo Extractor - Extracts JPEG/PNG images from PDF photo packets.
"""

import io
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image


def extract_photos_from_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extract embedded images from a PDF and return as list of photo dicts.
    
    Returns:
        List of dicts with: page_num, image_index, width, height, format, bytes
    """
    photos = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        # Collect all valid images on this page, pick the LARGEST (skip banners/text overlays)
        candidates = []
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue
            
            image_bytes = base_image.get("image")
            if not image_bytes or len(image_bytes) < 4096:  # Skip tiny images (<4KB)
                continue
            
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            
            # Skip banners/strips (aspect ratio > 4:1 or < 1:4, or too small in either dimension)
            if width < 200 or height < 200:
                continue
            aspect = width / max(height, 1)
            if aspect > 4.0 or aspect < 0.25:
                continue
            
            area = width * height
            candidates.append((area, width, height, base_image.get("ext", "jpg"), image_bytes))
        
        # Take the single largest image per page (the actual photo, not banners)
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            area, width, height, ext, image_bytes = candidates[0]
            photos.append({
                "page_num": page_num + 1,
                "image_index": 1,
                "width": width,
                "height": height,
                "format": ext,
                "bytes": image_bytes,
            })
    
    doc.close()
    return photos


def save_photos_to_disk(photos: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
    """Save extracted photo bytes to disk as individual files.
    
    Returns photos with added 'file_path' key.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    
    for i, photo in enumerate(photos):
        ext = photo.get("format", "jpg")
        if ext == "unknown":
            ext = "jpg"
        fname = f"photo_{i+1:03d}.{ext}"
        fpath = output_dir / fname
        
        with open(fpath, "wb") as f:
            f.write(photo["bytes"])
        
        # Validate with PIL
        try:
            img = Image.open(fpath)
            width, height = img.size
        except Exception:
            width, height = photo.get("width", 0), photo.get("height", 0)
        
        saved.append({
            **photo,
            "file_path": str(fpath),
            "width": width,
            "height": height,
        })
    
    return saved
