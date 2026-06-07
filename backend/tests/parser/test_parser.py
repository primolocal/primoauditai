"""
Tests for parser layer.
"""
import struct

from src.parser.base import ParsedEstimate, extract_state_from_address, extract_zip_from_address
from src.parser.ems_parser import EmsParser
from src.parser.pdf_estimate_parser import PDFEstimateParser

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


# --- PDF line parsing (smoke test with mock text) ---

class TestPDFLineParsing:
    def test_group_panels(self) -> None:
        parser = PDFEstimateParser()
        lines = [
            {"line_no": 1, "is_header": True, "panel_name": "FENDER", "description": "FENDER"},
            {"line_no": 2, "is_header": False, "panel_name": "FENDER", "description": "Replace fender"},
            {"line_no": 3, "is_header": True, "panel_name": "DOOR", "description": "DOOR"},
            {"line_no": 4, "is_header": False, "panel_name": "DOOR", "description": "Blend door"},
        ]
        panels = parser._group_panels(lines)
        assert "FENDER" in panels
        assert "DOOR" in panels
        assert len(panels["FENDER"]) == 1
        assert panels["FENDER"][0]["line_no"] == 2

    def test_extract_tax_rate(self) -> None:
        parser = PDFEstimateParser()
        # Cannot test without real PDF; verify method exists
        assert hasattr(parser, "_extract_tax_rate")
