import pytest
import zipfile
import io
import json
import struct
from parser.ems_parser import EmsParser
from adapter import build_audit_run

def create_mock_dbf() -> bytes:
    """Creates a very basic dummy DBF byte stream representing one .LIN record."""
    header = bytearray(32)
    header[0] = 0x03 # signature
    header[4:8] = struct.pack('<I', 1) # num records
    header[8:10] = struct.pack('<H', 64) # header bytes (32 + 32)
    header[10:12] = struct.pack('<H', 21) # record bytes (1 byte deleted flag + 20 chars)
    
    # 1 field
    field = bytearray(32)
    field[0:11] = b'LINE_DESC\x00\x00'
    field[11] = ord('C')
    field[16] = 20 # length
    
    # End of fields
    eoh = bytearray(1)
    eoh[0] = 0x0D
    
    # Record data
    record = bytearray(21)
    record[0] = 0x20 # not deleted
    record[1:21] = b'Test Bumper Part    '
    
    return bytes(header + field + eoh + record)

def create_mock_zip() -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('TEST.LIN', create_mock_dbf())
    buf.seek(0)
    return buf

def test_parser_emits_valid_schema():
    # Arrange
    zf = create_mock_zip()
    parser = EmsParser()
    from rules_engine import RulesEngine
    engine = RulesEngine()
    
    # Act
    parsed_data = parser.analyze_zip(zf)
    
    # EmsParser output structure
    assert "claim" in parsed_data
    
    raw_result = engine.evaluate_estimate(parsed_data)
    assert "audit" in raw_result
    
    # Convert directly through the adapter (this will raise Pydantic validation errors if misaligned)
    strict_result = build_audit_run(raw_result)
    
    # Assert
    assert strict_result["status"] == "not_started"
    assert strict_result["scorecard"]["overall_score"] >= 0
    assert strict_result["claim_package"]["claim_number"] == "UNKNOWN_CLAIM"
    assert "findings" in strict_result
    
    # Verify the line item got plucked
    assert len(strict_result["estimate_lines"]["items"]) == 1
    assert strict_result["estimate_lines"]["items"][0]["description"] == "Test Bumper Part"
