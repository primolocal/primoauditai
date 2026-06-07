"""
PDF Estimate Parser v2 — block-per-row extraction using PyMuPDF.
Parses CCC printout PDFs into ParsedEstimate for rules engine consumption.
"""
import re
from typing import Any

import fitz  # PyMuPDF

from src.parser.base import ParsedEstimate, extract_state_from_address

# Skip keywords for non-line blocks
SKIP_KW = {"SUBTOTALS", "SUBTOTAL", "TOTALS", "PREVIOUS", "CATEGORY", "BASIS", "RATE", "COST $"}

# Panel header keywords for grouping
HEADER_KW = [
    "FRONT BUMPER", "FRONT LAMPS", "HOOD", "FENDER", "ELECTRICAL",
    "WINDSHIELD", "CAB", "FRONT DOOR", "REAR DOOR", "BACK GLASS",
    "PICK UP BOX", "TAIL GATE", "REAR LAMPS", "ROOF", "QUARTER",
    "DECK LID", "LIFTGATE", "GRILLE", "RADIATOR", "COOLING",
    "HEADLAMP", "MIRROR", "BUMPER", "DOOR", "FLOOR", "DASH", "TRUNK", "GATE", "LAMP", "PANEL",
]

# Operation code mapping
OP_MAP = {
    "R&I": "Remove & Install",
    "Repl": "Replace",
    "PDR": "PDR",
    "Rpr": "Repair",
    "Blend": "Blend",
    "O/H": "Overhaul",
    "Incl": "Included",
    "Incl.": "Included",
}


class PDFEstimateParser:
    """Parse CCC printout PDFs into structured estimate data."""

    def parse(self, file_bytes: bytes) -> ParsedEstimate:
        """Parse PDF bytes into ParsedEstimate."""
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # Extract all text for metadata parsing
        all_text = ""
        for page in doc:
            all_text += page.get_text("text") + "\n"

        metadata = self._parse_metadata(all_text)
        lines = self._parse_lines(doc)
        panels = self._group_panels(lines)
        tax_rate = self._extract_tax_rate(doc)

        doc.close()

        metadata["estimate_tax_rate"] = tax_rate
        metadata["document_type"] = "pdf_estimate"

        # Derive state from shop ZIP if available
        shop_addr = metadata.get("shop_address", "")
        if shop_addr:
            zips = re.findall(r"\b(\d{5})\b", shop_addr)
            for z in zips:
                if int(z) > 10000:
                    metadata["shop_state_derived"] = extract_state_from_address(shop_addr) or ""
                    metadata["shop_zip"] = z
                    break

        return ParsedEstimate(
            lines=lines,
            panels=panels,
            metadata=metadata,
        )

    def _parse_metadata(self, text: str) -> dict[str, Any]:
        """Extract vehicle, claim, and shop metadata from PDF text."""
        info: dict[str, Any] = {}

        # Claim number
        m = re.search(r"Claim\s*(?:Number|#)[:\s]+([\w-]+)", text, re.I)
        if m:
            info["claim_number"] = m.group(1).strip()

        # VIN
        m = re.search(r"VIN[:\s]+([A-HJ-NPR-Z0-9]{17})", text, re.I)
        if m:
            info["vin"] = m.group(1).strip()

        # Odometer
        m = re.search(r"Odometer[:\s]+([\d,]+)", text, re.I)
        if m:
            info["odometer"] = int(m.group(1).replace(",", ""))

        # State (vehicle registration)
        m = re.search(r"State[:\s]+([A-Z]{2})", text, re.I)
        if m:
            info["vehicle_state"] = m.group(1).strip()

        # Production date
        m = re.search(r"Production Date[:\s]+(\S+)", text, re.I)
        if m:
            info["production_date"] = m.group(1).strip()

        # Loss type
        m = re.search(r"Type of Loss[:\s]+(\S+)", text, re.I)
        if m:
            info["loss_description"] = m.group(1).strip()

        # Vehicle year/make/model
        m = re.search(r"VEHICLE\s*\n(\d{4})\s+([A-Z]{3,})\s+(.+?)(?:\n|VIN)", text, re.I)
        if not m:
            m = re.search(r"(\d{4})\s+(LEXU|TOYO|HOND|FORD|CHEV|JEEP|DODG|NISS|BMW|AUDI|MERZ)\s+(.+?)(?:\n|VIN)", text, re.I)
        if not m:
            m = re.search(r"(\d{4})\s+([A-Z]{3,})\s+(.+?)(?:\n|VIN)", text, re.I)
        if m:
            info["vehicle_year"] = int(m.group(1))
            info["vehicle_make"] = m.group(2).strip()
            info["vehicle_model"] = m.group(3).strip()[:80]

        # Shop info from Repair Facility section
        rf_match = re.search(
            r"Repair Facility:\s*\n(.+?)(?:\n(?:Inspection Location|Owner:|VEHICLE\s*\n|Repair Facility\s*\n|$))",
            text,
            re.DOTALL,
        )
        if rf_match:
            rf_text = rf_match.group(1).strip()
            rf_lines = [ln.strip() for ln in rf_text.split("\n") if ln.strip()]
            deduped = []
            for ln in rf_lines:
                if not deduped or ln != deduped[-1]:
                    deduped.append(ln)

            shop_name = ""
            shop_addr_parts = []
            for i, line in enumerate(deduped):
                if any(kw in line.upper() for kw in ["BODY SHOP", "AUTO", "REPAIR", "COLLISION", "PDR", "SMART", "MOTORS", "GARAGE"]):
                    shop_name = line
                    shop_addr_parts = [ln for ln in deduped[i + 1 :] if not re.match(r"^\(?\d{3}\)?", ln)][:3]
                    break
            if not shop_name and len(deduped) >= 2:
                shop_name = deduped[1] if len(deduped) > 1 else deduped[0]
                shop_addr_parts = deduped[2:5] if len(deduped) > 2 else []

            if shop_name:
                info["shop_name"] = shop_name[:50]
                info["shop_address"] = " ".join(shop_addr_parts)[:80] if shop_addr_parts else ""

            phone_m = re.search(r"\(?\d{3}\)?\s*\d{3}[-.]?\d{4}", rf_text)
            if phone_m:
                info["shop_phone"] = phone_m.group(0)

        return info

    def _parse_lines(self, doc: fitz.Document) -> list[dict[str, Any]]:
        """Block-per-row parsing of estimate lines."""
        items: list[dict[str, Any]] = []
        current_panel = "Uncategorized"

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")

            for b in blocks:
                if len(b) < 5:
                    continue
                text = str(b[4]).strip()
                if not text:
                    continue

                x0 = b[0]

                # Skip non-line blocks
                if any(kw in text.upper() for kw in SKIP_KW):
                    continue
                if re.search(r"\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}", text):
                    continue

                fields = [f.strip() for f in text.split("\n") if f.strip()]
                if not fields:
                    continue

                first = fields[0]

                # Note lines (indented, attached to previous line)
                if x0 > 100 and first.startswith("Note:"):
                    if items and not items[-1].get("is_header"):
                        items[-1]["description"] += " [" + first + "]"
                    continue

                # Panel headers
                if first.isdigit() and len(fields) >= 2:
                    second = fields[1]
                    if any(kw in second.upper() for kw in HEADER_KW):
                        current_panel = second.strip()
                        items.append({
                            "line_no": int(first),
                            "is_header": True,
                            "panel_name": current_panel,
                            "description": second,
                        })
                        continue

                # Skip standalone header-only lines
                if any(kw in text.upper() for kw in HEADER_KW) and not first[0].isdigit():
                    current_panel = text.strip()
                    continue

                # Line items — first field should be a line number
                if not first.isdigit():
                    continue

                line_no = int(first)
                operation = fields[1] if len(fields) > 1 else ""
                description = fields[2] if len(fields) > 2 else ""

                # Try to parse remaining numeric fields
                part_no = ""
                qty = 0
                price = 0.0
                labor_hours = 0.0
                paint_hours = 0.0

                # Numeric fields start from index 3 or 4
                numeric_vals = []
                for f in fields[3:]:
                    # Clean currency/number strings
                    clean = f.replace("$", "").replace(",", "").strip()
                    if re.match(r"^-?\d+\.?\d*$", clean):
                        numeric_vals.append(float(clean))
                    elif re.match(r"^-?\d+$", clean):
                        numeric_vals.append(int(clean))

                # Heuristic assignment: [part_no?], qty, price, labor, paint
                if len(fields) > 3 and not re.match(r"^-?\d", fields[3].replace("$", "").replace(",", "")):
                    part_no = fields[3]
                    numeric_vals = numeric_vals[1:] if len(numeric_vals) > 1 else numeric_vals

                if len(numeric_vals) >= 1:
                    qty = numeric_vals[0]
                if len(numeric_vals) >= 2:
                    price = numeric_vals[1]
                if len(numeric_vals) >= 3:
                    labor_hours = numeric_vals[2]
                if len(numeric_vals) >= 4:
                    paint_hours = numeric_vals[3]

                # Map operation code
                operation_label = OP_MAP.get(operation, operation)

                total = price * qty
                if labor_hours > 0:
                    total += labor_hours * 50.0  # Assume $50/hr for body labor
                if paint_hours > 0:
                    total += paint_hours * 50.0

                items.append({
                    "line_no": line_no,
                    "operation": operation,
                    "operation_label": operation_label,
                    "description": description,
                    "part_number": part_no,
                    "quantity": qty,
                    "part_price": price,
                    "labor_hours": labor_hours,
                    "paint_hours": paint_hours,
                    "total": round(total, 2),
                    "panel_name": current_panel,
                    "is_header": False,
                })

        return items

    def _group_panels(self, lines: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group line items by panel name."""
        panels: dict[str, list[dict[str, Any]]] = {}
        current = "Uncategorized"

        for line in lines:
            if line.get("is_header"):
                current = line.get("panel_name", "Uncategorized")
                continue
            if current not in panels:
                panels[current] = []
            panels[current].append(line)

        return panels

    def _extract_tax_rate(self, doc: fitz.Document) -> float | None:
        """Extract sales tax rate from estimate totals page."""
        for page in doc:
            text = page.get_text()
            m = re.search(r"Sales Tax\s+([\d.]+)\s*%", text)
            if m:
                return float(m.group(1))
        return None


# --- Photo extraction ---

class PDFPhotoExtractor:
    """Extract embedded JPEG images from PDFs."""

    def extract(self, file_bytes: bytes) -> list[dict[str, Any]]:
        """Extract all embedded images from PDF, return as base64 data URLs."""
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        photos = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            img_list = page.get_images(full=True)

            for img_index, img in enumerate(img_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]

                if ext.lower() in ("jpg", "jpeg", "png"):
                    import base64
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                    mime = "image/jpeg" if ext.lower() in ("jpg", "jpeg") else "image/png"
                    photos.append({
                        "filename": f"page{page_num + 1}_img{img_index}_{xref}.{ext}",
                        "data_url": f"data:{mime};base64,{b64}",
                        "page": page_num + 1,
                    })

        doc.close()
        return photos
