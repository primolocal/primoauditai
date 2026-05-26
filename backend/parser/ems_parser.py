import zipfile
import struct
from typing import Dict, List, Any
from collections import defaultdict
from logging_config import get_logger

logger = get_logger("primoaudit.parser")

class EmsParser:
    def __init__(self):
        pass

    def _parse_float(self, val) -> float:
        try:
            if isinstance(val, str):
                val = val.replace('$', '').replace(',', '').strip()
                if not val: return 0.0
            return float(val)
        except:
            return 0.0

    def analyze_dbf(self, raw_bytes: bytes) -> Dict[str, Any]:
        if len(raw_bytes) < 32:
            return {"error": "File too small to evaluate"}
            
        sig = raw_bytes[0]
        if sig not in [0x02, 0x03, 0x30, 0x31, 0x43, 0xCB, 0xF5, 0x83, 0x8B, 0x04]:
            return {"error": f"Invalid signature: {hex(sig)}"}
            
        num_records = struct.unpack('<I', raw_bytes[4:8])[0]
        header_bytes = struct.unpack('<H', raw_bytes[8:10])[0]
        record_bytes = struct.unpack('<H', raw_bytes[10:12])[0]
        
        fields = []
        offset = 32
        record_offset = 1 
        
        while offset < header_bytes:
            if raw_bytes[offset] == 0x0D:
                break
                
            field_data = raw_bytes[offset:offset+32]
            if len(field_data) < 32:
                break
                
            name = field_data[0:11].split(b'\x00')[0].decode('ascii', errors='ignore')
            if not name:
                break
                
            ftype = chr(field_data[11])
            length = field_data[16]
            
            fields.append({
                "name": name,
                "type": ftype,
                "length": length,
                "offset": record_offset
            })
            
            record_offset += length
            offset += 32
            
        records = []
        current_pos = header_bytes
        
        for i in range(min(num_records, 2000)):
            if current_pos + record_bytes > len(raw_bytes):
                break
                
            record_data = raw_bytes[current_pos : current_pos + record_bytes]
            if len(record_data) > 0 and record_data[0] != 0x2A: 
                rec_obj = {}
                for f in fields:
                    start = f["offset"]
                    end = start + f["length"]
                    val = record_data[start:end].decode('latin-1', errors='ignore').strip()
                    rec_obj[f["name"]] = val
                records.append(rec_obj)
                
            current_pos += record_bytes
            
        return {"candidate_values": records}


    def normalize_lin(self, lin_records: List[Dict]) -> Dict[str, Any]:
        grouped = defaultdict(dict)
        
        for row in lin_records:
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
                    "labor_types": {},
                    "flags": {
                        "is_included_labor": False,
                        "is_sublet": False
                    },
                    "labor_hours": {
                        "body": 0.0,
                        "refinish": 0.0,
                        "mechanical": 0.0,
                        "frame": 0.0,
                        "diag": 0.0
                    },
                    "amounts": {
                        "labor_amount_body": 0.0,
                        "labor_amount_refinish": 0.0,
                        "labor_amount_mechanical": 0.0,
                        "labor_amount_frame": 0.0,
                        "labor_amount_diag": 0.0,
                        "misc_amount": 0.0,
                        "part_price": 0.0
                    }
                }
                
            lbr_ty = row.get("MOD_LBR_TY", "").strip()
            if not lbr_ty:
                lbr_ty = row.get("LBR_TYPE", "").strip()

            hrs = self._parse_float(row.get("DB_HRS", 0) or row.get("MOD_LB_HRS", 0) or row.get("ACT_LBR_HR", 0) or row.get("EST_LBR_HR", 0) or row.get("LBR_HRS", 0))
            amt = self._parse_float(row.get("ACT_LBR_AM", 0) or row.get("LBR_AMT", 0) or row.get("MOD_LB_AMT", 0))

            if lbr_ty:
                grouped[key]["labor_types"][lbr_ty] = True
                    
            if lbr_ty == 'LAB':
                grouped[key]["labor_hours"]["body"] += hrs
                grouped[key]["amounts"]["labor_amount_body"] += amt
            elif lbr_ty == 'LAR':
                grouped[key]["labor_hours"]["refinish"] += hrs
                grouped[key]["amounts"]["labor_amount_refinish"] += amt
            elif lbr_ty == 'LAM':
                grouped[key]["labor_hours"]["mechanical"] += hrs
                grouped[key]["amounts"]["labor_amount_mechanical"] += amt
            elif lbr_ty == 'LAF':
                grouped[key]["labor_hours"]["frame"] += hrs
                grouped[key]["amounts"]["labor_amount_frame"] += amt
            elif lbr_ty == 'LAD':
                grouped[key]["labor_hours"]["diag"] += hrs
                grouped[key]["amounts"]["labor_amount_diag"] += amt
            else:
                if hrs > 0:
                    grouped[key]["labor_hours"]["body"] += hrs
                    grouped[key]["amounts"]["labor_amount_body"] += amt
            
            misc_sublt = row.get("MISC_SUBLT", "").strip().upper()
            if misc_sublt == "Y" or misc_sublt == "TRUE" or 'sublet' in desc.lower() or 'subl' in desc.lower():
                grouped[key]["flags"]["is_sublet"] = True

            lbr_inc = row.get("LBR_INC", "").strip().upper()
            if (lbr_inc == "Y" or lbr_inc == "TRUE") and hrs > 0 and amt == 0:
                grouped[key]["flags"]["is_included_labor"] = True
            
            new_misc_amount = self._parse_float(row.get("MISC_AMT", 0) or row.get("SUBLET_AMT", 0))
            new_part_price = self._parse_float(row.get("ACT_PRICE", 0) or row.get("UNIT_PRICE", 0) or row.get("PART_AMT", 0) or row.get("DB_PRICE", 0) or row.get("LIST_PRICE", 0))
            
            grouped[key]["amounts"]["misc_amount"] = max(grouped[key]["amounts"]["misc_amount"], new_misc_amount)
            grouped[key]["amounts"]["part_price"] = max(grouped[key]["amounts"]["part_price"], new_part_price)

        lines = list(grouped.values())
        try:
            lines.sort(key=lambda x: int(x["line_no"]) if x["line_no"].isdigit() else 9999)
        except:
            pass
            
        panels = []
        current_panel = {
            "name": "Uncategorized",
            "rows": []
        }
        panels.append(current_panel)
        
        counts = {
            "header_rows": 0,
            "operation_rows": 0,
            "service_operation_rows": 0,
            "part_only_rows": 0,
            "misc_only_rows": 0,
            "sublet_rows": 0,
            "adjustment_rows": 0,
            "informational_rows": 0,
            "zero_value_rows": 0,
            "included_operation_rows": 0,
            "part_labor_hybrid_rows": 0,
            "part_included_labor_hybrid_rows": 0
        }
        
        for item in lines:
            desc = item["description"]
            hrs_total = sum(item["labor_hours"].values())
            labor_amt_total = item["amounts"]["labor_amount_body"] + item["amounts"]["labor_amount_refinish"] + item["amounts"]["labor_amount_mechanical"] + item["amounts"]["labor_amount_frame"] + item["amounts"]["labor_amount_diag"]
            part_no = item["part_number"]
            part_price = item["amounts"]["part_price"]
            misc_amount = item["amounts"]["misc_amount"]
            
            is_uppercase = (desc == desc.upper() and len(desc) > 0) or desc.startswith('**')
            
            is_header = False
            if is_uppercase and hrs_total == 0 and labor_amt_total == 0 and not part_no and part_price == 0 and misc_amount == 0:
                is_header = True
            
            if desc == "**MISCELLANEOUS**" and hrs_total == 0 and labor_amt_total == 0 and part_price == 0 and misc_amount == 0:
                is_header = True

            has_part_price = part_price > 0
            has_misc_amount = misc_amount > 0
            has_labor_hours = hrs_total > 0
            has_labor_amount = labor_amt_total > 0
            
            ld = desc.lower()
            oper_cd = item.get("operation_code", "").upper()
            pt_typ = item.get("part_type", "").upper()
            
            oper_label = ""
            if oper_cd in ["RPL", "REPLACE"]: oper_label = "Replace"
            elif oper_cd in ["RNI", "R&I", "REMOVE/INSTALL"]: oper_label = "Remove & Install"
            elif oper_cd in ["RPR", "REPAIR"]: oper_label = "Repair"
            elif oper_cd in ["O/H", "OVERHAUL"]: oper_label = "Overhaul"
            elif oper_cd in ["BLK", "BLEND", "BLN"]: oper_label = "Blend"
            elif oper_cd in ["REF", "REFN", "REFINISH"]: oper_label = "Refinish"
            elif oper_cd in ["INC", "INCLUDED"]: oper_label = "Included"
            
            # Text fallbacks if OPER_CD is missing or unrecognized
            if not oper_label:
                if "o/h" in ld or "overhaul" in ld: oper_label = "Overhaul"
                elif "r&i" in ld or ("remove" in ld and "install" in ld): oper_label = "Remove & Install"
                elif "rpr" in ld or "repair" in ld: oper_label = "Repair"
                elif "repl" in ld or "replace" in ld: oper_label = "Replace"
                elif "scan" in ld: oper_label = "Diagnostic Scan"
                elif "aim" in ld or "calibration" in ld: oper_label = "Calibration / Aim"
                elif "blend" in ld: oper_label = "Blend"
                elif "refinish" in ld: oper_label = "Refinish"
                elif oper_cd: oper_label = oper_cd # Assign literal if totally unrecognized
                
            service_subtype = ""
            misc_subtype = ""
            is_scan_related = False
            is_calibration_related = False
            is_hazardous_waste = False
            is_material_charge = False
            
            if "scan" in ld:
                is_scan_related = True
                service_subtype = "scan"
            if "aim" in ld or "calibration" in ld:
                is_calibration_related = True
                service_subtype = "sensor_aim"
            if "haz" in ld and "waste" in ld:
                is_hazardous_waste = True
                misc_subtype = "hazardous_waste"
            if "flex" in ld and "add" in ld:
                is_material_charge = True
                misc_subtype = "flex_additive"

            if has_part_price and has_labor_hours and not has_labor_amount:
                item["flags"]["is_included_labor"] = True
                row_type = "part_included_labor_hybrid"
            elif is_header:
                row_type = "header"
            elif item["flags"]["is_sublet"]:
                row_type = "sublet"
            elif item["flags"]["is_included_labor"]:
                row_type = "included_operation"
            elif has_part_price and (has_labor_hours or has_labor_amount):
                row_type = "part_labor_hybrid"
            elif has_labor_hours or has_labor_amount:
                if is_scan_related or is_calibration_related:
                    row_type = "service_operation"
                else:
                    row_type = "operation"
            elif has_part_price and not has_misc_amount:
                row_type = "part_only"
            elif has_misc_amount and not has_part_price:
                if "adj" in ld or "discount" in ld or "markup" in ld:
                    row_type = "adjustment"
                else:
                    row_type = "misc_only"
            else:
                row_type = "informational"
                
            if hrs_total == 0 and part_price == 0 and misc_amount == 0 and labor_amt_total == 0 and row_type != "header":
                counts["zero_value_rows"] += 1
                
            item["row_type"] = row_type
            item["is_header"] = is_header
            
            count_key = f"{row_type}_rows"
            if count_key in counts:
                counts[count_key] += 1
            else:
                counts[count_key] = 1
                
            out_row = {
                "line_no": item["line_no"],
                "row_type": row_type,
                "is_header": is_header,
                "description": desc,
                "operation_label": oper_label,
                "operation_type": oper_label,
                "operation_code": oper_cd,
                "part_type": pt_typ,
                "has_operation_label": bool(oper_label),
                "has_part_price": has_part_price,
                "has_misc_amount": has_misc_amount,
                "has_labor_hours": has_labor_hours,
                "has_labor_amount": has_labor_amount,
                "is_included_labor": item["flags"]["is_included_labor"],
                "is_sublet": item["flags"]["is_sublet"],
                "is_scan_related": is_scan_related,
                "is_calibration_related": is_calibration_related,
                "is_hazardous_waste": is_hazardous_waste,
                "is_material_charge": is_material_charge,
                "financial_signature": {
                    "part_price": part_price,
                    "misc_amount": misc_amount,
                    "labor_amount_total": labor_amt_total,
                    "labor_hours_total": hrs_total
                }
            }
            
            if service_subtype:
                out_row["service_subtype"] = service_subtype
            if misc_subtype:
                out_row["misc_subtype"] = misc_subtype
            
            if item["supplement"]:
                out_row["supplement"] = item["supplement"]
            if item["labor_types"]:
                out_row["labor_types"] = list(item["labor_types"])
                
            out_row["labor_amount_body"] = item["amounts"]["labor_amount_body"]
            out_row["labor_amount_refinish"] = item["amounts"]["labor_amount_refinish"]
            out_row["labor_amount_mechanical"] = item["amounts"]["labor_amount_mechanical"]
            out_row["labor_amount_frame"] = item["amounts"]["labor_amount_frame"]
            out_row["labor_amount_diag"] = item["amounts"]["labor_amount_diag"]
            out_row["misc_amount"] = misc_amount
            out_row["part_price"] = part_price
            
            if hrs_total > 0:
                out_row["labor_hours"] = item["labor_hours"]
            if part_no:
                out_row["part_number"] = part_no
                
            if is_header:
                current_panel = {
                    "name": item["description"].strip('*').strip(), 
                    "rows": []
                }
                panels.append(current_panel)
            else:
                current_panel["rows"].append(out_row)
                
        clean_panels = [p for p in panels if p["name"] != "Uncategorized" or len(p["rows"]) > 0]
        
        base_output = {
            "claim": {
                "panels": clean_panels,
                "validation": counts
            }
        }
        
        return base_output

    def analyze_zip(self, zip_path_or_bytes) -> Dict[str, Any]:
        lin_records = []
        claim_meta = {
            "claim_number": "UNKNOWN_CLAIM",
            "carrier": "Unknown Carrier",
            "loss_date": None
        }
        carrier_candidates = {}
        shop_info = {}
        
        with zipfile.ZipFile(zip_path_or_bytes, 'r') as z:
            for filename in z.namelist():
                info = z.getinfo(filename)
                if info.is_dir():
                    continue
                    
                ext = filename.split('.')[-1].lower() if '.' in filename else ''
                
                # Handle LIN files
                if ext == 'lin':
                    raw_bytes = z.read(filename)
                    if len(raw_bytes) > 0:
                        dbf_data = self.analyze_dbf(raw_bytes)
                        lin_records.extend(dbf_data.get("candidate_values", []))
                        
                # Handle all other DBF files (.ADJ, .AD1, .AD2, .EST, etc) for metadata sniffing
                elif ext != 'lin':
                    raw_bytes = z.read(filename)
                    if len(raw_bytes) > 0:
                        dbf_data = self.analyze_dbf(raw_bytes)
                        if "error" not in dbf_data:
                            import logging
                            candidates = dbf_data.get("candidate_values", [])
                            if candidates:
                                logger.debug(f"EMS DBF ROW DUMP: {candidates[0]}")
                            for row in dbf_data.get("candidate_values", []):
                                for k, v in row.items():
                                    val = str(v).strip()
                                    if not val: continue
                                    kl = str(k).upper().strip()
                                    # Finding Claim Number
                                    if kl in ["CLM_NO", "CLAIM_NO", "CLAIMNUM", "CLAIM_NUM", "CLAIM_ID", "CLAIMNO"] and claim_meta["claim_number"] == "UNKNOWN_CLAIM":
                                        claim_meta["claim_number"] = val
                                    # Finding Carrier
                                    if "IANET" in val.upper() or "IA NET" in val.upper():
                                        carrier_candidates["tpa"] = val
                                    else:
                                        if kl in ["INS_CO_NM", "INS_CO_NAM", "INS_CMPNY", "INS_CO", "INSCO", "CARRIER", "INS_COMP"]:
                                            carrier_candidates["primary"] = val
                                        elif kl == "COMPANY":
                                            carrier_candidates["secondary"] = val
                                        elif kl == "CLM_OFC_NM":
                                            carrier_candidates["tertiary"] = val
                                    # Finding Loss Date
                                    if kl in ["LOSS_DATE", "LOSSDATE", "DT_OF_LOSS", "DOL", "LOSS_DT"] and not claim_meta["loss_date"]:
                                        if len(val) == 8 and val.isdigit(): # Format from AD1 e.g. 20260303
                                            claim_meta["loss_date"] = f"{val[:4]}-{val[4:6]}-{val[6:]}T00:00:00Z"
                                        else:
                                            claim_meta["loss_date"] = val
                                    # Finding Shop/Location Info
                                    if kl == "LOC_NM":
                                        shop_info["name"] = val
                                    elif kl == "LOC_ADDR1":
                                        shop_info["address"] = val
                                    elif kl in ("LOC_CITY",):
                                        shop_info["city"] = val
                                    elif kl in ("LOC_ST",):
                                        shop_info["state"] = val
                                    elif kl in ("LOC_ZIP",):
                                        shop_info["zip"] = val
                                    elif kl in ("LOC_PH1", "LOC_PH"):
                                        shop_info["phone"] = val

        if "primary" in carrier_candidates: claim_meta["carrier"] = carrier_candidates["primary"]
        elif "secondary" in carrier_candidates: claim_meta["carrier"] = carrier_candidates["secondary"]
        elif "tertiary" in carrier_candidates: claim_meta["carrier"] = carrier_candidates["tertiary"]

        base_output = self.normalize_lin(lin_records)
        base_output["claim_meta"] = claim_meta
        base_output["claim_meta"]["shop"] = shop_info
        return base_output
