"""
Tests for parser layer.
"""
import struct

import pytest

from src.parser.base import ParsedEstimate, extract_state_from_address, extract_zip_from_address
from src.parser.ems_parser import EmsParser
from src.parser.pdf_estimate_parser import PDFEstimateParser

TEST_PDF = "tests/testfiles/TestEstimate.pdf"


# --- Base utilities ---

class TestBaseUtilities:
    def test_extract_zip(self) -> None:
        assert extract_zip_from_address("123 Main St, Houston, TX 77001") == "77001"
        assert extract_zip_from_address("456 Oak Ave, Chicago, IL 60601-1234") == "60601"
        assert extract_zip_from_address("No zip here") is None

    def test_extract_state(self) -> None:
        assert extract_state_from_address("123 Main St, Houston, TX 77001") == "TX"
        assert extract_state_from_address("456 Oak Ave, Chicago, IL 60601") == "IL"
        assert extract_state_from_address("No state here") is None

    def test_parsed_estimate_to_context(self) -> None:
        pe = ParsedEstimate(
            lines=[{"line_no": 1, "description": "Replace fender"}],
            metadata={"claim_number": "CLM-123"},
        )
        ctx = pe.to_audit_context()
        assert ctx.lines[0]["description"] == "Replace fender"
        assert ctx.metadata["claim_number"] == "CLM-123"


# --- PDF metadata extraction ---

class TestPDFMetadata:
    def test_parse_vehicle_info(self) -> None:
        parser = PDFEstimateParser()
        text = """
Claim Number: ABC-12345
VIN: 1HGCM82633A123456
Odometer: 45,230
State: TX
Production Date: 2023-01-15
Type of Loss: Hail
VEHICLE
2022 HOND Accord Sport
Repair Facility:
Levanders Body Shop
123 Main St, Houston, TX 77001
(713) 555-1234
"""
        meta = parser._parse_metadata(text)
        assert meta["claim_number"] == "ABC-12345"
        assert meta["vin"] == "1HGCM82633A123456"
        assert meta["odometer"] == 45230
        assert meta["vehicle_state"] == "TX"
        assert meta["vehicle_year"] == 2022
        assert meta["vehicle_make"] == "HOND"
        assert meta["shop_name"] == "Levanders Body Shop"
        assert meta.get("shop_phone") == "(713) 555-1234"

    def test_parse_no_vehicle_match(self) -> None:
        parser = PDFEstimateParser()
        text = "Some random text without vehicle info"
        meta = parser._parse_metadata(text)
        assert meta.get("claim_number") is None
        assert meta.get("vin") is None

    def test_parse_real_pdf_metadata(self) -> None:
        """Parse the test PDF and verify metadata."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())
        meta = result.metadata
        assert meta["claim_number"] == "260479295-1"
        assert meta["vin"] == "5TFKB5DB1TX376956"
        assert meta["odometer"] == 12950
        assert meta["vehicle_state"] == "CO"
        assert meta["vehicle_year"] == 2026
        assert meta["vehicle_make"] == "TOYO"
        assert meta["shop_name"] == "Maaco Collision Repair  Auto Paint"
        assert meta["document_type"] == "pdf_estimate"


# --- PDF line parsing (real file) ---

class TestPDFLineParsing:
    def test_parse_real_pdf_lines(self) -> None:
        """Parse test PDF and verify line structure."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        assert len(result.lines) > 0
        # Headers should be present
        headers = [l for l in result.lines if l.get("is_header")]
        assert len(headers) > 0
        # Non-header lines should have line_no
        items = [l for l in result.lines if not l.get("is_header")]
        assert len(items) > 0
        assert all(l["line_no"] != "" for l in items)

    def test_labor_only_lines(self) -> None:
        """Lines with operation but no part number have labor hours, not price."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 2: "2 * R&I RT Side cover ... 0.2" → labor=0.2, no part
        line2 = [l for l in result.lines if l.get("line_no") == "2" and not l.get("is_header")][0]
        assert line2["operation"] == "R&I"
        assert line2["labor_hours"] == 0.2
        assert line2["part_price"] == 0.0
        assert line2["part_number"] == ""

        # Line 10: "10 Aim headlamps 0.5" → labor=0.5
        line10 = [l for l in result.lines if l.get("line_no") == "10" and not l.get("is_header")][0]
        assert line10["description"] == "Aim headlamps"
        assert line10["labor_hours"] == 0.5

    def test_part_with_paint(self) -> None:
        """Replace lines with part number have price + paint hours."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 5: "5 Repl Upper support 531130C060 1 117.08 0.2"
        line5 = [l for l in result.lines if l.get("line_no") == "5" and not l.get("is_header")][0]
        assert line5["operation"] == "Repl"
        assert line5["part_number"] == "531130C060"
        assert line5["part_price"] == 117.08
        assert line5["labor_hours"] == 0.2
        assert line5["paint_hours"] == 0.0  # This file's line 5 has no paint

        # Line 19: "19 Repl Hood w/o molding (ALU) 533010C070 1 884.89 1.6 3.0"
        line19 = [l for l in result.lines if l.get("line_no") == "19" and not l.get("is_header")][0]
        assert line19["part_number"] == "533010C070"
        assert line19["part_price"] == 884.89
        assert line19["labor_hours"] == 1.6
        assert line19["paint_hours"] == 3.0

    def test_paint_only_lines(self) -> None:
        """Lines like 'Add for Clear Coat' have paint hours, not price."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 4: "4 Add for Clear Coat 0.7"
        line4 = [l for l in result.lines if l.get("line_no") == "4" and not l.get("is_header")][0]
        assert line4["description"] == "Add for Clear Coat"
        assert line4["paint_hours"] == 0.7
        assert line4["part_price"] == 0.0
        assert line4["labor_hours"] == 0.0

    def test_flag_and_supplement(self) -> None:
        """Flags (*, #) and supplement codes parsed correctly."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 2 has * flag
        line2 = [l for l in result.lines if l.get("line_no") == "2" and not l.get("is_header")][0]
        assert line2["flag"] == "*"

        # Line 55 has # flag
        line55 = [l for l in result.lines if l.get("line_no") == "55" and not l.get("is_header")][0]
        assert line55["flag"] == "#"

    def test_mechanical_labor_suffix(self) -> None:
        """Labor type suffix 'M' marks mechanical labor."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 44: "44 Bleed brake system four wheel m 1.7 M"
        line44 = [l for l in result.lines if l.get("line_no") == "44" and not l.get("is_header")][0]
        assert "bleed" in line44["description"].lower()
        assert line44["labor_hours"] == 1.7
        assert line44["labor_type"] == "mechanical"

    def test_frame_labor_suffix(self) -> None:
        """Labor type suffix 'F' marks frame labor."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 57: "57 # Rpr Rough Pull 1.0 F"
        line57 = [l for l in result.lines if l.get("line_no") == "57" and not l.get("is_header")][0]
        assert line57["labor_hours"] == 1.0
        assert line57["labor_type"] == "frame"

    def test_all_digit_part_number(self) -> None:
        """All-digit part numbers like 0446534050 parse correctly."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 45: "45 Repl Brake pads from 05/2025 0446534050 1 144.52 Incl."
        line45 = [l for l in result.lines if l.get("line_no") == "45" and not l.get("is_header")][0]
        assert line45["part_number"] == "0446534050"
        assert line45["part_price"] == 144.52
        assert line45["is_included_labor"] is True

    def test_sublet_line(self) -> None:
        """Sublet lines with price but no labor."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 56: "56 # Subl Four wheel alignment 1 99.95"
        line56 = [l for l in result.lines if l.get("line_no") == "56" and not l.get("is_header")][0]
        assert line56["operation"] == "Subl"
        assert line56["part_price"] == 99.95
        assert line56["labor_hours"] == 0.0

    def test_cover_car_misc(self) -> None:
        """Misc line with price + labor."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 55: "55 # Cover Car 1 5.00 0.2"
        line55 = [l for l in result.lines if l.get("line_no") == "55" and not l.get("is_header")][0]
        assert line55["description"] == "Cover Car"
        assert line55["part_price"] == 5.0
        assert line55["labor_hours"] == 0.2

    def test_included_labor(self) -> None:
        """Lines with trailing 'Incl.' have is_included_labor=True."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        # Line 16: "16 Repl Upper tie bar 532050C070 1 134.05 0.3 Incl."
        line16 = [l for l in result.lines if l.get("line_no") == "16" and not l.get("is_header")][0]
        assert line16["is_included_labor"] is True
        assert line16["labor_hours"] == 0.3
        assert line16["paint_hours"] == 0.0

    def test_panel_grouping(self) -> None:
        """Lines grouped under correct panel headers."""
        parser = PDFEstimateParser()
        with open(TEST_PDF, "rb") as f:
            result = parser.parse(f.read())

        assert "FRONT BUMPER" in result.panels
        assert "HOOD" in result.panels
        assert "FENDER" in result.panels
        # FRONT BUMPER should have non-header lines
        bumper_lines = result.panels["FRONT BUMPER"]
        assert len(bumper_lines) > 0
        assert all(l["panel_name"] == "FRONT BUMPER" for l in bumper_lines)


# --- EMS DBF parser ---

class TestEmsParser:
    def test_parse_minimal_dbf(self) -> None:
        """Create a minimal valid DBF file and parse it."""
        # Build a minimal DBF v3 file
        # Header: 32 bytes + field descriptors + 0x0D terminator
        # Record: 1 byte flag + field data
        fields = [
            (b"LINE_NO\x00\x00\x00\x00", b"C", 10),
            (b"LINE_DESC\x00\x00", b"C", 50),
            (b"OPER_CD\x00\x00\x00\x00", b"C", 10),
            (b"DB_HRS\x00\x00\x00\x00\x00", b"N", 8),
            (b"ACT_PRICE\x00\x00", b"N", 10),
        ]

        header_size = 32 + len(fields) * 32 + 1  # +1 for terminator
        record_size = 1 + sum(f[2] for f in fields)
        num_records = 2

        header = bytearray(32)
        header[0] = 0x03  # DBF v3
        header[4:8] = struct.pack("<I", num_records)
        header[8:10] = struct.pack("<H", header_size)
        header[10:12] = struct.pack("<H", record_size)

        # Field descriptors
        field_bytes = bytearray()
        for name, ftype, length in fields:
            fd = bytearray(32)
            fd[0:11] = name
            fd[11] = ord(ftype)
            fd[16] = length
            field_bytes.extend(fd)

        # Terminator
        field_bytes.append(0x0D)

        # Records
        records = bytearray()
        # Build properly padded record strings (exact field widths)
        rec1 = (
            b"1         "  # LINE_NO (10)
            + b"Replace fender".ljust(50)  # LINE_DESC (50)
            + b"Repl      "  # OPER_CD (10)
            + b"2.50    "  # DB_HRS (8)
            + b"125.00    "  # ACT_PRICE (10)
        )
        rec2 = (
            b"2         "
            + b"Blend door".ljust(50)
            + b"Blend     "
            + b"1.00    "
            + b"0.00      "
        )

        for rec in [rec1, rec2]:
            records.append(0x20)  # Not deleted
            records.extend(rec.ljust(record_size - 1)[:record_size - 1])

        # End of file marker
        eof = b"\x1A"

        dbf_bytes = bytes(header) + bytes(field_bytes) + bytes(records) + eof

        # Parse
        parser = EmsParser()
        records = parser._parse_dbf(dbf_bytes)
        assert len(records) == 2
        assert records[0]["LINE_NO"] == "1"
        assert records[0]["LINE_DESC"] == "Replace fender"

    def test_normalize_lines(self) -> None:
        parser = EmsParser()
        raw = [
            {"LINE_NO": "1", "LINE_DESC": "Replace fender", "OPER_CD": "Repl", "DB_HRS": "2.5", "ACT_PRICE": "125.00", "PANEL_DESC": "FENDER"},
            {"LINE_NO": "2", "LINE_DESC": "Blend door", "OPER_CD": "Blend", "DB_HRS": "1.0", "ACT_PRICE": "0.00", "PANEL_DESC": "DOOR"},
        ]
        lines = parser._normalize_lines(raw)
        assert len(lines) == 2
        assert lines[0]["line_no"] == "1"
        assert lines[0]["labor_hours"] == 2.5
        assert lines[0]["part_price"] == 125.0
        assert lines[0]["panel_name"] == "FENDER"
        assert lines[1]["operation_code"] == "Blend"

    def test_parse_float(self) -> None:
        assert EmsParser._parse_float("$1,250.50") == 1250.50
        assert EmsParser._parse_float("") == 0.0
        assert EmsParser._parse_float(None) == 0.0
        assert EmsParser._parse_float("abc") == 0.0
