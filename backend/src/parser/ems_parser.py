"""
Lightweight CCC EMS ZIP metadata extractor.
Opens EMS ZIP files, parses DBF tables, extracts structured metadata.
Eliminates all PDF extraction issues by reading data directly from CCC.
"""

import struct
import zipfile
from typing import Any


def parse_dbf(raw_bytes: bytes) -> list[dict[str, Any]]:
    """Parse a DBF file from raw bytes. Returns list of record dicts."""
    if len(raw_bytes) < 32:
        return []
    
    sig = raw_bytes[0]
    if sig not in (0x02, 0x03, 0x30, 0x31, 0x43, 0x83, 0x8B, 0xF5):
        return []

    num_records = struct.unpack("<I", raw_bytes[4:8])[0]
    header_bytes = struct.unpack("<H", raw_bytes[8:10])[0]
    record_bytes = struct.unpack("<H", raw_bytes[10:12])[0]

    fields = []
    offset = 32
    rec_offset = 1

    while offset < header_bytes:
        if raw_bytes[offset] == 0x0D:
            break
        field_data = raw_bytes[offset : offset + 32]
        if len(field_data) < 32:
            break
        name = field_data[0:11].split(b"\x00")[0].decode("ascii", errors="ignore")
        if not name:
            break
        length = field_data[16]
        fields.append({"name": name, "length": length, "offset": rec_offset})
        rec_offset += length
        offset += 32

    records = []
    pos = header_bytes
    for _ in range(min(num_records, 5000)):
        if pos + record_bytes > len(raw_bytes):
            break
        record_data = raw_bytes[pos : pos + record_bytes]
        if record_data[0] == 0x2A:  # deleted record
            pos += record_bytes
            continue
        rec = {}
        for f in fields:
            start = f["offset"]
            end = start + f["length"]
            rec[f["name"]] = record_data[start:end].decode("latin-1", errors="ignore").strip()
        records.append(rec)
        pos += record_bytes

    return records


def extract_ems_metadata(zip_data: bytes) -> dict[str, Any]:
    """Extract all QC-relevant metadata from a CCC EMS ZIP file."""
    import io
    
    metadata: dict[str, Any] = {
        "document_type": "ems_zip",
        "claim_number": None,
        "insurance_company": None,
        "shop_name": None,
        "shop_address": None,
        "shop_phone": None,
        "shop_of_choice": False,
        "vin": None,
        "vehicle_year": None,
        "vehicle_make": None,
        "vehicle_model": None,
        "odometer": None,
        "deductible": None,
        "license_plate": None,
        "labor_rate": None,
        "tax_rate": None,
        "state": None,
        "zip_code": None,
        "loss_date": None,
        "loss_description": None,
        "is_supplement": False,
        "supplement_version": 0,
        "parsed_lines": [],
    }

    carrier_candidates = {}

    with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zf:
        for filename in zf.namelist():
            if filename.endswith("/"):
                continue
            
            ext = filename.split(".")[-1].lower() if "." in filename else ""
            
            try:
                raw = zf.read(filename)
                if not raw:
                    continue
            except Exception:
                continue

            records = parse_dbf(raw)
            if not records:
                continue

            for row in records:
                for k, v in row.items():
                    val = str(v).strip()
                    if not val:
                        continue
                    kl = k.upper().strip()

                    # ── Claim number ──
                    if kl in ("CLM_NO", "CLAIM_NO", "CLAIMNUM", "CLAIM_NUM", "CLAIM_ID") and not metadata["claim_number"]:
                        metadata["claim_number"] = val

                    # ── Insurance / Carrier ──
                    if kl in ("INS_CO_NM", "INS_CO_NAM", "INS_CMPNY", "INSCO", "CARRIER", "INS_COMP"):
                        carrier_candidates["primary"] = val
                    elif kl == "COMPANY":
                        carrier_candidates["secondary"] = val
                    elif kl == "CLM_OFC_NM":
                        carrier_candidates["tertiary"] = val

                    # ── Shop info ──
                    if kl == "LOC_NM" and not metadata["shop_name"]:
                        metadata["shop_name"] = val
                    elif kl == "LOC_ADDR1" and not metadata["shop_address"]:
                        metadata["shop_address"] = val
                    elif kl == "LOC_CITY":
                        addr = metadata.get("shop_address", "") or ""
                        if val not in addr:
                            metadata["shop_address"] = (addr + " " + val).strip()
                    elif kl == "LOC_ST":
                        metadata["state"] = val
                        addr = metadata.get("shop_address", "") or ""
                        if val not in addr:
                            metadata["shop_address"] = (addr + ", " + val).strip()
                    elif kl == "LOC_ZIP":
                        metadata["zip_code"] = val
                        addr = metadata.get("shop_address", "") or ""
                        if val not in addr:
                            metadata["shop_address"] = (addr + " " + val).strip()
                    elif kl in ("LOC_PH1", "LOC_PH") and not metadata["shop_phone"]:
                        metadata["shop_phone"] = val

                    # ── Shop of Choice ──
                    if kl in ("SHOP_CHOICE", "REPAIR_FACILITY_TYPE", "SHOP_TYPE"):
                        val_lower = val.lower()
                        if any(kw in val_lower for kw in ("choice", "owner", "customer", "claimant")):
                            metadata["shop_of_choice"] = True

                    # ── Vehicle ──
                    if kl in ("VIN_NO", "VIN", "VEH_VIN") and not metadata["vin"]:
                        metadata["vin"] = val
                    if kl in ("MODEL_YR", "VEH_YEAR", "YEAR") and not metadata["vehicle_year"]:
                        try:
                            metadata["vehicle_year"] = int(val)
                        except ValueError:
                            pass
                    if kl in ("MAKE", "VEH_MAKE", "VEHICLE_MAKE") and not metadata["vehicle_make"]:
                        metadata["vehicle_make"] = val
                    if kl in ("MODEL", "VEH_MODEL", "VEHICLE_MODEL") and not metadata["vehicle_model"]:
                        metadata["vehicle_model"] = val[:80]
                    if kl in ("ODOMETER", "ODOMTR", "ODO", "MILEAGE") and not metadata["odometer"]:
                        try:
                            metadata["odometer"] = int(val.replace(",", ""))
                        except ValueError:
                            pass

                    # ── Deductible ──
                    if kl in ("DEDUCTIBLE", "DEDUCT", "DED_AMT", "DED_AMOUNT") and not metadata["deductible"]:
                        try:
                            metadata["deductible"] = float(val.replace("$", "").replace(",", ""))
                        except ValueError:
                            pass

                    # ── License plate ──
                    if kl in ("LIC_PLATE", "LICENSE", "LICENSE_PLATE", "LIC_NO", "TAG") and not metadata["license_plate"]:
                        metadata["license_plate"] = val

                    # ── Labor/Tax rates ──
                    if kl in ("LABOR_RATE", "BODY_RATE", "LBR_RT") and not metadata["labor_rate"]:
                        try:
                            metadata["labor_rate"] = float(val.replace("$", "").replace(",", ""))
                        except ValueError:
                            pass
                    if kl in ("TAX_RATE", "SALES_TAX", "TAX_PCT") and not metadata["tax_rate"]:
                        try:
                            metadata["tax_rate"] = float(val.replace("%", "")) / 100 if "%" in val else float(val)
                        except ValueError:
                            pass

                    # ── Loss info ──
                    if kl in ("LOSS_DATE", "LOSSDATE", "DT_OF_LOSS", "DOL", "LOSS_DT") and not metadata["loss_date"]:
                        if len(val) == 8 and val.isdigit():
                            metadata["loss_date"] = f"{val[:4]}-{val[4:6]}-{val[6:]}"
                        else:
                            metadata["loss_date"] = val
                    if kl in ("LOSS_TYPE", "TYPE_OF_LOSS", "LOSS_DESC", "CAUSE_OF_LOSS") and not metadata["loss_description"]:
                        metadata["loss_description"] = val

                    # ── State from vehicle ──
                    if kl in ("VEH_STATE", "VEH_ST", "GARAGE_ST", "STATE") and not metadata["state"]:
                        metadata["state"] = val

    # Resolve carrier
    if carrier_candidates.get("primary"):
        metadata["insurance_company"] = carrier_candidates["primary"]
    elif carrier_candidates.get("secondary"):
        metadata["insurance_company"] = carrier_candidates["secondary"]
    elif carrier_candidates.get("tertiary"):
        metadata["insurance_company"] = carrier_candidates["tertiary"]

    return metadata
