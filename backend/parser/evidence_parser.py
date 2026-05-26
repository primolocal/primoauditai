"""
Evidence Parser — extracts assets from CCC ZIP files and supporting uploads.
Handles PDFs with embedded photos (CCC export format) via PyMuPDF.
"""
from typing import List, Dict
import zipfile
import io
import uuid
import os
from datetime import datetime, timezone
from storage_service import StorageService
from logging_config import get_logger

logger = get_logger("primoaudit.evidence")

# Image extensions that can be extracted from PDFs
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}


class EvidenceParser:
    """Extracts and classifies evidence assets from CCC ZIP exports."""

    @staticmethod
    def _extract_images_from_pdf(
        pdf_bytes: bytes,
        pdf_filename: str,
        base_url: str,
        audit_id: str,
        source_kind: str = "extracted_from_zip",
    ) -> List[Dict]:
        """
        Extract embedded images from a PDF using PyMuPDF.
        Each extracted image becomes a separate asset with its own URL.
        The original PDF is NOT included here — caller handles that.
        """
        import fitz  # PyMuPDF

        extracted = []
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            logger.warning(f"Failed to open PDF for image extraction: {pdf_filename} — {e}")
            return extracted

        page_count = len(doc)
        logger.info(f"Extracting images from PDF: {pdf_filename} ({page_count} pages)")

        for page_num in range(page_count):
            try:
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]  # xref number
                    try:
                        base_image = doc.extract_image(xref)
                        img_bytes = base_image["image"]
                        img_ext = base_image["ext"]  # e.g. 'jpeg', 'png'

                        # Skip tiny images (thumbnails, icons)
                        if len(img_bytes) < 1024:
                            continue

                        # Build a descriptive filename
                        base_name = os.path.splitext(pdf_filename)[0]
                        img_filename = f"{base_name}_p{page_num+1}_img{img_index+1}.{img_ext}"

                        # Store the extracted image
                        storage_key = StorageService.save_file(
                            img_filename, img_bytes, sub_folder=audit_id
                        )
                        thumb_key = StorageService.generate_thumbnail(storage_key, "image")

                        asset_id = f"asset_{uuid.uuid4().hex[:8]}"
                        record = {
                            "id": asset_id,
                            "filename": img_filename,
                            "storage_key": storage_key,
                            "source_url": f"{base_url}/assets/{storage_key}",
                            "thumbnail_url": f"{base_url}/assets/thumbs/{thumb_key}" if thumb_key else None,
                            "is_mock": False,
                            "source_kind": source_kind,
                            "pdf_source": pdf_filename,
                            "pdf_page": page_num + 1,
                            "ingested_at": now_str,
                            "extraction_method": "pdf_image_extraction",
                            "reason": f"Extracted from PDF page {page_num + 1}",
                            "processing_status": "preview_ready",
                        }
                        extracted.append(record)

                    except Exception as e:
                        logger.warning(
                            f"Failed to extract image xref={xref} from {pdf_filename} page {page_num}: {e}"
                        )

            except Exception as e:
                logger.warning(f"Failed to process page {page_num} of {pdf_filename}: {e}")

        doc.close()
        logger.info(f"Extracted {len(extracted)} images from {pdf_filename}")
        return extracted

    @staticmethod
    def _store_asset(
        filename: str,
        file_data: bytes,
        base_url: str,
        audit_id: str,
        source_kind: str,
        extraction_method: str,
        parent_pdf: str = None,
    ) -> Dict:
        """Store a single file asset and return its record."""
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        lower_name = filename.lower()

        asset_type = "pdf" if lower_name.endswith(".pdf") else "image"
        storage_key = StorageService.save_file(filename, file_data, sub_folder=audit_id)
        thumb_key = StorageService.generate_thumbnail(storage_key, asset_type)

        record = {
            "id": f"asset_{uuid.uuid4().hex[:8]}",
            "filename": os.path.basename(filename),
            "storage_key": storage_key,
            "source_url": f"{base_url}/assets/{storage_key}",
            "thumbnail_url": f"{base_url}/assets/thumbs/{thumb_key}" if thumb_key else None,
            "is_mock": False,
            "source_kind": source_kind,
            "ingested_at": now_str,
            "extraction_method": extraction_method,
            "reason": f"Direct extraction from {source_kind}",
            "processing_status": "preview_ready",
        }
        if parent_pdf:
            record["pdf_source"] = parent_pdf

        return record

    @staticmethod
    def _process_zip_contents(
        z: zipfile.ZipFile,
        base_url: str,
        audit_id: str,
        now_str: str,
    ) -> List[Dict]:
        """Process all extractable files from a ZIP archive."""
        extracted = []

        for filename in z.namelist():
            if filename.endswith("/"):
                continue

            lower_name = filename.lower()
            is_image = any(lower_name.endswith(ext) for ext in IMAGE_EXTS)
            is_pdf = lower_name.endswith(".pdf")

            if not (is_image or is_pdf):
                continue

            file_data = z.read(filename)

            if is_pdf:
                # Store the PDF itself as a document asset
                pdf_record = EvidenceParser._store_asset(
                    filename, file_data, base_url, audit_id,
                    source_kind="extracted_from_zip",
                    extraction_method="zip_unpacker",
                )
                extracted.append(pdf_record)

                # Extract embedded images from the PDF
                pdf_images = EvidenceParser._extract_images_from_pdf(
                    file_data, filename, base_url, audit_id,
                    source_kind="extracted_from_zip",
                )
                extracted.extend(pdf_images)

            elif is_image:
                record = EvidenceParser._store_asset(
                    filename, file_data, base_url, audit_id,
                    source_kind="extracted_from_zip",
                    extraction_method="zip_unpacker",
                )
                extracted.append(record)

        return extracted

    @staticmethod
    def _process_supporting_files(
        supporting_files: list,
        base_url: str,
        audit_id: str,
        now_str: str,
    ) -> List[Dict]:
        """Process manually uploaded supporting files."""
        extracted = []

        for sf_name, sf_bytes in supporting_files:
            try:
                lower_name = sf_name.lower()
                is_image = any(lower_name.endswith(ext) for ext in IMAGE_EXTS)
                is_pdf = lower_name.endswith(".pdf")

                if not (is_image or is_pdf):
                    continue

                if is_pdf:
                    # Store the PDF
                    pdf_record = EvidenceParser._store_asset(
                        sf_name, sf_bytes, base_url, audit_id,
                        source_kind="manual_upload",
                        extraction_method="multipart_form",
                    )
                    extracted.append(pdf_record)

                    # Extract images from PDF
                    pdf_images = EvidenceParser._extract_images_from_pdf(
                        sf_bytes, sf_name, base_url, audit_id,
                        source_kind="manual_upload",
                    )
                    extracted.extend(pdf_images)

                elif is_image:
                    record = EvidenceParser._store_asset(
                        sf_name, sf_bytes, base_url, audit_id,
                        source_kind="manual_upload",
                        extraction_method="multipart_form",
                    )
                    extracted.append(record)

            except Exception as e:
                logger.error(f"Error processing supporting file {sf_name}: {e}")

        return extracted

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def extract_assets(zip_path_or_bytes) -> List[Dict[str, str]]:
        """Mock extraction returning static unsplash URLs (dev/demo only)."""
        mock_assets = [
            {
                "id": "asset_001",
                "filename": "SmithShop_SubletInvoice_1211.pdf",
                "source_url": "https://images.unsplash.com/photo-1620714223084-8fcacc6dfd8d?w=800&fit=crop",
                "thumbnail_url": "https://images.unsplash.com/photo-1620714223084-8fcacc6dfd8d?w=200&h=200&fit=crop",
            },
            {
                "id": "asset_002",
                "filename": "IMG_RightFrontBumper_Tear.jpg",
                "source_url": "https://images.unsplash.com/photo-1605557202138-097824c3e0ec?w=800&fit=crop",
                "thumbnail_url": "https://images.unsplash.com/photo-1605557202138-097824c3e0ec?w=200&h=200&fit=crop",
            },
            {
                "id": "asset_003",
                "filename": "IMG_Vin_Plate.jpg",
                "source_url": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=800&fit=crop",
                "thumbnail_url": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=200&h=200&fit=crop",
            },
        ]
        return mock_assets

    @staticmethod
    def extract_assets_live(
        zip_bytes: io.BytesIO,
        base_url: str,
        with_fixtures: bool = False,
        supporting_files: list = None,
        audit_id: str = "",
    ) -> List[Dict[str, str]]:
        """
        Extract images/PDFs from uploaded ZIP and external files.
        PDFs are unpacked: embedded images extracted as separate photo assets
        while the PDF is retained as a document asset.
        """
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        extracted_assets = []

        # 1. Process ZIP contents (CCC export)
        if zip_bytes:
            try:
                with zipfile.ZipFile(zip_bytes) as z:
                    extracted_assets = EvidenceParser._process_zip_contents(
                        z, base_url, audit_id, now_str
                    )
            except zipfile.BadZipFile:
                logger.error("Invalid or corrupted ZIP file")
            except Exception as e:
                logger.error(f"Error extracting assets from ZIP: {e}")

        # 2. Process external supporting files
        if supporting_files:
            supporting_assets = EvidenceParser._process_supporting_files(
                supporting_files, base_url, audit_id, now_str
            )
            extracted_assets.extend(supporting_assets)

        # 3. Fallback fixture if nothing was extracted
        if not extracted_assets and with_fixtures:
            logger.warning("No valid images/PDFs found. Spooling fallback placeholder.")
            fallback_img = (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00d\x00\x00\x00d'
                b'\x08\x02\x00\x00\x00\xfcL]\x82\x00\x00\x00\x1fIDATx\x9c\xed\xc1'
                b'\x01\x01\x00\x00\x00\x82 \xff\xafnM\x07\x04\x00\x00\x00\x00\x00'
                b'\x00\x80\xa7\x01\x05 \x00\x01\x19[\x02v\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            storage_key = StorageService.save_file("placeholder.png", fallback_img)
            thumb_key = StorageService.generate_thumbnail(storage_key, "image")

            extracted_assets.append({
                "id": f"asset_{uuid.uuid4().hex[:8]}",
                "filename": "IMG_RightFrontBumper_Fallback.jpg",
                "storage_key": storage_key,
                "source_url": f"{base_url}/assets/{storage_key}",
                "thumbnail_url": f"{base_url}/assets/thumbs/{thumb_key}" if thumb_key else None,
                "is_mock": True,
                "source_kind": "generated_fixture",
                "ingested_at": now_str,
                "extraction_method": "fixture_generator",
                "reason": "Fallback fixture — no assets found in upload",
                "processing_status": "preview_ready",
            })

        return extracted_assets
