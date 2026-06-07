"""
EMS (CCC One) ZIP parser — extracts DBF records and normalizes line items.
"""
import io
import struct
import zipfile
from collections import defaultdict
from typing import Any

from src.parser.base import ParsedEstimate


class EmsParser:
    """Parse CCC One EMS ZIP files (.zip containing .DBF + .PDF)."""

    def parse(self, file_bytes: bytes) -> ParsedEstimate:
        """Parse EMS ZIP bytes into ParsedEstimate."""
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            # Find DBF file
            dbf_name = None
            pdf_name = None
            for name in z.namelist():
                if name.upper().endswith(".DBF"):
                    dbf_name = name
                elif name.upper().endswith(".PDF"):
                    pdf_name = name

            if not dbf_name:
                raise ValueError("No .DBF file found in EMS ZIP")

            dbf_bytes = z.read(dbf_name)
            records = self._parse_dbf(dbf_bytes)
            lines = self._normalize_lines(records)

            # Extract metadata from PDF if present
            metadata: dict[str, Any] = {}
            if pdf_name:
                pdf_bytes = z.read(pdf_name)
                metadata = self._extract_pdf_metadata(pdf_bytes)

            metadata["document_type"] = "ems_zip"
            metadata["ems_filename"] = dbf_name

            panels = self._group_panels(lines)

            return ParsedEstimate(
                lines=lines,
                panels=panels,
                metadata=metadata,
            )

    def _parse_dbf(self, raw_bytes: bytes) -> list[dict[str, str]]:
        """Parse DBF binary into record dictionaries."""
        if len(raw_bytes) < 32:
            return []

        sig = raw_bytes[0]
        if sig not in {0x02, 0x03, 0x30, 0x31, 0x43, 0xCB, 0xF5, 0x83, 0x8B, 0x04}:
            return []

        num_records = struct.unpack("<I", raw_bytes[4:8])[0]
        header_bytes = struct.unpack("<H", raw_bytes[8:10])[0]
        record_bytes = struct.unpack("<H", raw_bytes[10:12])[0]

        # Parse field descriptors
        fields = []
        offset = 32
        record_offset = 1

        while offset < header_bytes:
            if raw_bytes[offset] == 0x0D:
                break

            field_data = raw_bytes[offset : offset + 32]
            if len(field_data) < 32:
                break

            name = field_data[0:11].split(b"\x00")[0].decode("ascii", errors="ignore")
            if not name:
                break

            ftype = chr(field_data[11])
            length = field_data[16]

            fields.append({
                "name": name,
                "type": ftype,
                "length": length,
                "offset": record_offset,
            })

            record_offset += length
            offset += 32

        # Parse records
        records = []
        current_pos = header_bytes

        for _ in range(min(num_records, 5000)):
            if current_pos + record_bytes > len(raw_bytes):
                break

            record_data = raw_bytes[current_pos : current_pos + record_bytes]
            if len(record_data) > 0 and record_data[0] != 0x2A:  # Not deleted
                rec_obj: dict[str, str] = {}
                for f in fields:
                    start = f["offset"]
                    end = start + f["length"]
                    val = record_data[start:end].decode("latin-1", errors="ignore").strip()
                    rec_obj[f["name"]] = val
                records.append(rec_obj)

            current_pos += record_bytes

        return records

    def _normalize_lines(self, records: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Normalize LIN records into flat line items."""
        grouped = defaultdict(dict)

        for row in records:
            line_no = row.get("LINE_NO", "").strip()
            if not line_no:
                line_no = row.get("LINE_SEQ", "").strip()

            desc = row.get("LINE_DESC", "").strip()
            part_no = row.get("OEM_PARTNO", "").strip()

            if not line_no and not desc:
                continue

            key = f"{line_no}_{desc}_{part_no}"

            if key not in grouped:
                grouped[key] = {
                    "line_no": line_no,
                    "description": desc,
                    "part_number": part_no,
                    "operation_code": row.get("OPER_CD", "").strip() or row.get("OPER_DESC", "").strip() or row.get("OPER", "").strip(),
                    "part_type": row.get("PART_TYP", "").strip() or row.get("PART_TYPE", "").strip() or row.get("PRT_TYP", "").strip(),
                    "supplement": row.get("LINE_IND", "").strip(),
                    "labor_hours": 0.0,
                    "labor_amount": 0.0,
                    "part_price": 0.0,
                    "misc_amount": 0.0,
                    "is_sublet": False,
                    "is_included_labor": False,
                    "panel_name": row.get("PANEL_DESC", "").strip() or "Uncategorized",
                }

            # Parse labor hours and amounts
            lbr_ty = row.get("MOD_LBR_TY", "").strip() or row.get("LBR_TYPE", "").strip()  # noqa: F841
            hrs = self._parse_float(row.get("DB_HRS", 0) or row.get("MOD_LB_HRS", 0) or row.get("ACT_LBR_HR", 0) or row.get("EST_LBR_HR", 0) or row.get("LBR_HRS", 0))
            amt = self._parse_float(row.get("ACT_LBR_AM", 0) or row.get("LBR_AMT", 0) or row.get("MOD_LB_AMT", 0))

            grouped[key]["labor_hours"] += hrs
            grouped[key]["labor_amount"] += amt

            # Sublet flag
            misc_sublt = row.get("MISC_SUBLT", "").strip().upper()
            if misc_sublt in {"Y", "TRUE"} or "sublet" in desc.lower() or "subl" in desc.lower():
                grouped[key]["is_sublet"] = True

            # Included labor flag
            lbr_inc = row.get("LBR_INC", "").strip().upper()
            if lbr_inc in {"Y", "TRUE"} and hrs > 0 and amt == 0:
                grouped[key]["is_included_labor"] = True

            # Misc + part amounts
            misc_amt = self._parse_float(row.get("MISC_AMT", 0) or row.get("SUBLET_AMT", 0))
            part_price = self._parse_float(row.get("ACT_PRICE", 0) or row.get("UNIT_PRICE", 0) or row.get("PART_AMT", 0) or row.get("DB_PRICE", 0) or row.get("LIST_PRICE", 0))

            grouped[key]["misc_amount"] = max(grouped[key]["misc_amount"], misc_amt)
            grouped[key]["part_price"] = max(grouped[key]["part_price"], part_price)

        lines = list(grouped.values())

        import contextlib
        with contextlib.suppress(Exception):
            lines.sort(key=lambda x: int(x["line_no"]) if x["line_no"].isdigit() else 9999)

        # Compute totals
        for line in lines:
            line["total"] = round(
                line.get("part_price", 0.0) + line.get("labor_amount", 0.0) + line.get("misc_amount", 0.0),
                2,
            )

        return lines

    def _group_panels(self, lines: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group lines by panel name."""
        panels: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for line in lines:
            panel = line.get("panel_name", "Uncategorized")
            panels[panel].append(line)
        return dict(panels)

    def _extract_pdf_metadata(self, pdf_bytes: bytes) -> dict[str, Any]:
        """Quick metadata extraction from embedded PDF."""
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()

            info: dict[str, Any] = {}
            import re
            m = re.search(r"Claim\s*(?:Number|#)[:\s]+([\w-]+)", text, re.I)
            if m:
                info["claim_number"] = m.group(1).strip()
            m = re.search(r"VIN[:\s]+([A-HJ-NPR-Z0-9]{17})", text, re.I)
            if m:
                info["vin"] = m.group(1).strip()
            return info
        except Exception:
            return {}

    @staticmethod
    def _parse_float(val) -> float:
        try:
            if isinstance(val, str):
                val = val.replace("$", "").replace(",", "").strip()
                if not val:
                    return 0.0
            return float(val)
        except Exception:
            return 0.0
