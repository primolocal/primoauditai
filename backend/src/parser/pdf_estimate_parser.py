"""
PDF Estimate Parser v2 — block-per-row extraction using PyMuPDF.
Parses CCC printout PDFs into ParsedEstimate for rules engine consumption.

Field order per CCC block:
  line_no | [flag */#] | [supplement S01] | [operation] | description... |
  [part_no] | [qty] | [price] | [labor] | [paint] | [Incl.]

Operations: R&I, Repl, PDR, Rpr, Blend, O/H, Incl, Blnd, Ref, Subl
Labor suffixes: M=mechanical, F=frame (stripped, stored as labor_type)
Price suffixes: m, M stripped
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
    "SUSPENSION", "MISCELLANEOUS", "FRAME", "ALIGNMENT",
]

# Operation code mapping
OP_MAP = {
    "R&I": "Remove & Install",
    "Repl": "Replace",
    "PDR": "PDR",
    "Rpr": "Repair",
    "Blend": "Blend",
    "Blnd": "Blend",
    "O/H": "Overhaul",
    "Incl": "Included",
    "Incl.": "Included",
    "Ref": "Refinish",
    "Refn": "Refinish",
    "Subl": "Sublet",
}

# Known operation codes
OP_CODES = {
    "R&I", "Repl", "PDR", "Rpr", "Blend", "Blnd", "O/H", "Incl", "Incl.",
    "Ref", "Refn", "Subl", "RPL", "REPLACE", "RNI", "REMOVE/INSTALL",
    "RPR", "REPAIR", "BLK", "BLN", "REFINISH", "INC", "INCLUDED",
}

# Labor type suffixes
LBR_SUFFIX = {"M": "mechanical", "F": "frame", "R": "refinish", "B": "body", "D": "diag"}


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

        # Date of loss
        m = re.search(r"Date of Loss[:\s]+(\S+)", text, re.I)
        if m:
            info["loss_date"] = m.group(1).strip()

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
                if any(kw in line.upper() for kw in ["BODY SHOP", "AUTO", "REPAIR", "COLLISION", "PDR", "SMART", "MOTORS", "GARAGE", "MAACO"]):
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

                # Panel headers — CCC panel headers always have exactly 2 fields:
                # line number + panel name (e.g. "6\nGRILLE")
                if first.isdigit() and len(fields) == 2:
                    second = fields[1]
                    if any(kw in second.upper() for kw in HEADER_KW):
                        current_panel = second.strip()
                        items.append({
                            "line_no": first,
                            "is_header": True,
                            "panel_name": current_panel,
                            "description": second,
                        })
                        continue

                # Standalone header-only lines (no line number)
                if any(kw in text.upper() for kw in HEADER_KW) and not first[0].isdigit():
                    current_panel = text.strip()
                    continue

                # --- Line item parsing ---
                if not first.isdigit():
                    continue

                line_no = first
                fi = 1
                flag = ""
                supplement = ""
                operation = ""
                labor_type = ""
                is_included = False

                # Flag (*, #)
                if fi < len(fields) and fields[fi] in ("*", "#"):
                    flag = fields[fi]
                    fi += 1

                # Supplement (S01, S02, ...)
                if fi < len(fields) and re.match(r"^S\d{2}$", fields[fi]):
                    supplement = fields[fi]
                    fi += 1

                # Skip placeholder fields like "<>"
                while fi < len(fields) and fields[fi] == "<>":
                    fi += 1

                # Operation code
                if fi < len(fields) and fields[fi].upper() in {c.upper() for c in OP_CODES}:
                    operation = fields[fi]
                    fi += 1

                # Description — consume until number or part number
                desc_parts = []
                while fi < len(fields):
                    f = fields[fi]
                    # Break on numeric values (price, labor, paint)
                    if self._is_numeric_field(f):
                        break
                    # Break on part numbers (alphanumeric 6-20)
                    if self._is_part_number(f):
                        break
                    # Skip "X" qty markers
                    if f == "X":
                        fi += 1
                        continue
                    desc_parts.append(f)
                    fi += 1
                description = " ".join(desc_parts)

                # Extract part type from description prefix (A/M, LKQ, RECON)
                part_type = ""
                desc_text = " ".join(desc_parts)
                desc_upper = desc_text.upper()
                for prefix, pt_label in [("A/M", "A/M"), ("LKQ", "LKQ"), ("RECON", "RECON"), ("RECY", "REC"), ("USED", "USED")]:
                    # Check if the prefix appears standalone in the description text
                    pat = r"(?:^|\s)" + re.escape(prefix) + r"(?:\s|[-])"
                    if re.search(pat, desc_upper):
                        part_type = pt_label
                        # Remove the prefix (and potentially following CAPA) from description
                        # Find the actual occurrence and strip it + following tokens
                        desc_remaining = []
                        skip_next = False
                        for i_word, w in enumerate(desc_parts):
                            w_upper = w.upper()
                            if w_upper == prefix or w_upper.startswith(prefix + "-"):
                                skip_next = False
                                if i_word + 1 < len(desc_parts) and desc_parts[i_word + 1].upper() == "CAPA":
                                    skip_next = True
                                continue
                            if skip_next:
                                skip_next = False
                                continue
                            desc_remaining.append(w)
                        desc_text = " ".join(desc_remaining)
                        break

                # If description still starts with "CAPA " after stripping the type, strip that too
                if desc_text.upper().startswith("CAPA "):
                    desc_text = desc_text[5:].strip()

                description = desc_text

                # --- Determine how to interpret remaining numeric fields ---
                part_no = ""
                if fi < len(fields) and self._is_part_number(fields[fi]):
                    part_no = fields[fi]
                    fi += 1

                has_part_no = part_no != ""
                desc_lower = description.lower()
                is_labor_only = operation in {"R&I", "Rpr", "Blend", "Blnd", "PDR", "O/H", "Ref", "Refn", "Incl", "Incl."}
                is_paint_line = any(word in desc_lower for word in {"clear coat", "edging", "refinish components", "refinish", "paint", "blend", "underside"})
                is_service_line = any(word in desc_lower for word in {"aim", "calibration", "scan", "diagnostic", "bleed", "flush"})
                is_deduction = "deduct" in desc_lower or "overlap" in desc_lower

                qty = 1
                price = 0.0
                labor_hours = 0.0
                paint_hours = 0.0

                if not has_part_no and (is_labor_only or is_paint_line or is_service_line or is_deduction):
                    # Labor/paint/service/deduction lines without parts:
                    # numbers are labor/paint, not price.
                    if fi < len(fields) and re.match(r"^\d{1,2}$", fields[fi]):
                        fi += 1

                    # First numeric field
                    if fi < len(fields):
                        val, fi, suffix = self._parse_number_with_suffix(fields, fi)
                        if is_paint_line:
                            paint_hours = val
                        else:
                            labor_hours = val
                        if suffix in LBR_SUFFIX:
                            labor_type = LBR_SUFFIX[suffix]

                    # Second numeric field (paint for body ops, labor for paint ops)
                    if fi < len(fields) and fields[fi].lower() not in ("incl", "incl."):
                        val, fi, suffix = self._parse_number_with_suffix(fields, fi)
                        if is_paint_line:
                            labor_hours = val
                        else:
                            paint_hours = val
                else:
                    # Standard part / sublet / misc parsing:
                    # qty → price → labor → paint
                    if fi < len(fields) and re.match(r"^\d{1,2}$", fields[fi]):
                        qty = int(fields[fi])
                        fi += 1

                    if fi < len(fields):
                        val, fi, suffix = self._parse_number_with_suffix(fields, fi)
                        price = val

                    if fi < len(fields) and fields[fi].lower() not in ("incl", "incl."):
                        val, fi, suffix = self._parse_number_with_suffix(fields, fi)
                        labor_hours = val
                        if suffix in LBR_SUFFIX:
                            labor_type = LBR_SUFFIX[suffix]

                    if fi < len(fields) and fields[fi].lower() not in ("incl", "incl."):
                        val, fi, _suffix = self._parse_number_with_suffix(fields, fi)
                        paint_hours = val

                # Trailing "Incl." marker
                if fi < len(fields) and fields[fi].lower() in ("incl", "incl."):
                    is_included = True
                    fi += 1

                # Map operation label
                operation_label = OP_MAP.get(operation, operation)

                # Compute total (use a dummy $50 rate for labor/paint when no part price)
                total = price * qty
                if labor_hours > 0:
                    total += labor_hours * 50.0
                if paint_hours > 0:
                    total += paint_hours * 50.0

                items.append({
                    "line_no": line_no,
                    "flag": flag,
                    "supplement": supplement,
                    "operation": operation,
                    "operation_label": operation_label,
                    "description": description,
                    "part_number": part_no,
                    "quantity": qty,
                    "part_price": price,
                    "labor_hours": labor_hours,
                    "paint_hours": paint_hours,
                    "labor_type": labor_type,
                    "part_type": part_type,
                    "is_included_labor": is_included,
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

    # --- Field parsing helpers ---

    @staticmethod
    def _is_numeric_field(val: str) -> bool:
        """Check if value is a numeric field (price/labor/paint)."""
        clean = val.replace("$", "").replace(",", "").replace("m", "").replace("M", "").replace("F", "").strip()
        return bool(re.match(r"^-?\d+\.?\d*$", clean))

    @staticmethod
    def _is_part_number(val: str) -> bool:
        """Check if value looks like a part number."""
        # Part numbers: alphanumeric with optional dashes, typically 6-20 chars
        if len(val) < 5 or len(val) > 25:
            return False
        if not re.match(r"^[A-Z0-9-]+$", val, re.I):
            return False
        # Exclude dates (MM/YYYY)
        if re.match(r"^\d{2}/\d{4}$", val):
            return False
        # All-digit strings of length 6-20 are valid part numbers (e.g., 0446534050)
        if val.isdigit():
            return 6 <= len(val) <= 20
        return True

    @staticmethod
    def _parse_number_field(fields: list[str], fi: int) -> tuple[float, int]:
        """Parse a numeric field, return (value, next_index)."""
        if fi >= len(fields):
            return 0.0, fi
        f = fields[fi]
        clean = f.replace("$", "").replace(",", "").replace("m", "").replace("M", "").strip()
        try:
            val = float(clean)
            return val, fi + 1
        except ValueError:
            return 0.0, fi

    @staticmethod
    def _parse_number_with_suffix(fields: list[str], fi: int) -> tuple[float, int, str]:
        """Parse a numeric field with optional labor type suffix."""
        if fi >= len(fields):
            return 0.0, fi, ""
        f = fields[fi]
        # Check for suffix
        suffix = ""
        clean = f.replace("$", "").replace(",", "").strip()
        if clean.endswith(("M", "m", "F", "R", "B", "D")) and len(clean) > 1:
            suffix = clean[-1].upper()
            clean = clean[:-1].strip()
        try:
            val = float(clean)
            return val, fi + 1, suffix
        except ValueError:
            return 0.0, fi, ""


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
