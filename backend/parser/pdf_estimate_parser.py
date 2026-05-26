"""
PDF Estimate Parser v4 — block-per-row extraction.
Each text block = one estimate row. Columns newline-separated within block.
Format: Line# | [Supp] | Oper | Description | [Part#] | [Qty] | [Price] | [Labor] | [Paint]
"""
import re
from typing import Dict, List, Any
import fitz
from logging_config import get_logger

logger = get_logger("primoaudit.pdf_parser")

SKIP_KW = {"SUBTOTALS","SUBTOTAL","TOTALS","PREVIOUS","CATEGORY","BASIS","RATE","COST $"}

HEADER_KW = ["FRONT BUMPER","FRONT LAMPS","HOOD","FENDER","ELECTRICAL",
    "WINDSHIELD","CAB","FRONT DOOR","REAR DOOR","BACK GLASS",
    "PICK UP BOX","TAIL GATE","REAR LAMPS","ROOF","QUARTER",
    "DECK LID","LIFTGATE","GRILLE","RADIATOR","COOLING",
    "HEADLAMP","MIRROR","BUMPER","DOOR","FLOOR","DASH","TRUNK","GATE","LAMP","PANEL"]

OP_MAP = {"R&I":"Remove & Install","Repl":"Replace","PDR":"PDR","Rpr":"Repair",
          "Blend":"Blend","O/H":"Overhaul","Incl":"Included","Incl.":"Included"}


class PDFEstimateParser:
    """Parses CCC printouts using block-per-row extraction."""

    def parse_pdf(self, pdf_path_or_bytes):
        if isinstance(pdf_path_or_bytes, str):
            doc = fitz.open(pdf_path_or_bytes)
        else:
            doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")

        all_text = ""
        for page in doc:
            all_text += page.get_text("text") + "\n"
        doc.close()

        vehicle = self._parse_vehicle(all_text)
        line_items = self._parse_lines(pdf_path_or_bytes)
        panels = self._group_panels(line_items)

        # Extract tax rate and totals from the PDF
        tax_rate = self._extract_tax_rate(pdf_path_or_bytes)

        logger.info("PDF v4: %d lines", len(line_items))

        # Use shop ZIP to determine correct state for tax/rate rules
        shop_state = vehicle.get("state", "")
        shop_addr = vehicle.get("shop_address", "")
        if shop_addr:
            import re
            zips = re.findall(r'\b(\d{5})\b', shop_addr)
            for z in zips:
                if int(z) > 10000:
                    try:
                        from tax_labor_lookup import lookup_tax
                        tax = lookup_tax(z)
                        if tax and tax.get("state"):
                            shop_state = tax["state"]
                    except Exception:
                        pass
                    break

        return {
            "claim": {"panels": panels, "validation": {}},
            "claim_meta": {
                "claim_number": vehicle.get("claim_number", "PDF_ESTIMATE"),
                "carrier": "NATIONAL GENERAL",
                "type_of_loss": vehicle.get("type_of_loss", ""),
                "estimate_tax_rate": tax_rate,
                "vehicle": {
                    "year": vehicle.get("year"), "make": vehicle.get("make"),
                    "model": vehicle.get("model"), "mileage": vehicle.get("mileage"),
                    "vin": vehicle.get("vin"),
                },
                "tax_rate_estimate": tax_rate,
                "shop": {
                    "name": vehicle.get("shop_name", ""),
                    "state": shop_state,
                    "address": vehicle.get("shop_address", ""),
                    "phone": vehicle.get("shop_phone", ""),
                },
            },
            "evidence_matrix": {"processing_status": "pdf_parsed_v4", "documents": [], "photos": []},
        }

    def _parse_vehicle(self, text):
        info = {}
        m = re.search(r'Claim\s*(?:Number|#)[:\s]+([\w-]+)', text, re.I)
        if m: info["claim_number"] = m.group(1).strip()
        m = re.search(r'VIN[:\s]+([A-HJ-NPR-Z0-9]{17})', text, re.I)
        if m: info["vin"] = m.group(1).strip()
        m = re.search(r'Odometer[:\s]+([\d,]+)', text, re.I)
        if m: info["mileage"] = int(m.group(1).replace(",",""))
        m = re.search(r'State[:\s]+([A-Z]{2})', text, re.I)
        if m: info["state"] = m.group(1).strip()
        m = re.search(r'Production Date[:\s]+(\S+)', text, re.I)
        if m: info["production_date"] = m.group(1).strip()
        # Loss type and date
        m = re.search(r'Type of Loss[:\s]+(\S+)', text, re.I)
        if m: info["type_of_loss"] = m.group(1).strip()
        m = re.search(r'Date of Loss[:\s]+(\S+)', text, re.I)
        if m: info["loss_date"] = m.group(1).strip()
        m = re.search(r'VEHICLE\s*\n(\d{4})\s+([A-Z]{3,})\s+(.+?)(?:\n|VIN)', text, re.I)
        if not m:
            m = re.search(r'(\d{4})\s+(LEXU|TOYO|HOND|FORD|CHEV|JEEP|DODG|NISS|BMW|AUDI|MERZ)\s+(.+?)(?:\n|VIN)', text, re.I)
        if not m:
            m = re.search(r'(\d{4})\s+([A-Z]{3,})\s+(.+?)(?:\n|VIN)', text, re.I)
        if m:
            info["year"] = int(m.group(1))
            info["make"] = m.group(2).strip()
            info["model"] = m.group(3).strip()[:80]
        m = re.search(r'(LEVANDERS[^\n]{5,50}|CAPITAL[^\n]{5,50})', text)
        if m: info["shop_name"] = m.group(1).strip()[:50]

        # Extract from Repair Facility section — capture until next section header or end of page 1-2 text
        rf_match = re.search(r'Repair Facility:\s*\n(.+?)(?:\n(?:Inspection Location|Owner:|VEHICLE\s*\n|Repair Facility\s*\n))', text, re.DOTALL)
        if rf_match:
            rf_text = rf_match.group(1).strip()
            rf_lines = [l.strip() for l in rf_text.split('\n') if l.strip()]
            deduped = []
            for l in rf_lines:
                if not deduped or l != deduped[-1]:
                    deduped.append(l)
            shop_name = ""
            shop_addr_parts = []
            for i, line in enumerate(deduped):
                if any(kw in line.upper() for kw in ['BODY SHOP','AUTO','REPAIR','COLLISION','PDR','SMART','MOTORS','GARAGE']):
                    shop_name = line
                    shop_addr_parts = [l for l in deduped[i+1:] if not re.match(r'^\(?\d{3}\)?', l)][:3]
                    break
            if not shop_name and len(deduped) >= 2:
                shop_name = deduped[1] if len(deduped) > 1 else deduped[0]
                shop_addr_parts = deduped[2:5] if len(deduped) > 2 else []
            
            if shop_name:
                info["shop_name"] = shop_name[:50]
                info["shop_address"] = ' '.join(shop_addr_parts)[:80] if shop_addr_parts else ""
            phone_m = re.search(r'\(?\d{3}\)?\s*\d{3}[-.]?\d{4}', rf_text)
            if phone_m:
                info["shop_phone"] = phone_m.group(0)

        return info

    def _extract_tax_rate(self, pdf_path_or_bytes):
        """Extract sales tax rate from estimate totals page."""
        if isinstance(pdf_path_or_bytes, str):
            doc = fitz.open(pdf_path_or_bytes)
        else:
            doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
        for page in doc:
            text = page.get_text()
            m = re.search(r'Sales Tax\s+([\d.]+)\s*%', text)
            if m:
                doc.close()
                return float(m.group(1))
        doc.close()
        return None

    def _parse_lines(self, pdf_path_or_bytes):
        """Block-per-row parsing."""
        if isinstance(pdf_path_or_bytes, str):
            doc = fitz.open(pdf_path_or_bytes)
        else:
            doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")

        items = []
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

                if any(kw in text.upper() for kw in SKIP_KW):
                    continue
                if re.search(r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}', text):
                    continue

                fields = [f.strip() for f in text.split('\n') if f.strip()]
                if not fields:
                    continue

                first = fields[0]

                # Note lines
                if x0 > 100 and first.startswith("Note:"):
                    if items and not items[-1].get("is_header"):
                        items[-1]["description"] += " [" + first + "]"
                    continue

                # Panel headers (line# + header in 2 fields)
                if len(fields) <= 2 and first.isdigit() and len(fields) >= 2:
                    hdr = fields[1].upper()
                    if any(kw in hdr for kw in HEADER_KW):
                        items.append({
                            "line_no":"","description":fields[1],"operation_label":"",
                            "part_price":0,"labor_hours":0,"paint_hours":0,
                            "is_header":True,"supplement":"",
                        })
                        continue

                # Standalone header
                if len(fields) == 1 and first.isupper() and len(first) <= 30:
                    if any(kw in first for kw in HEADER_KW):
                        items.append({
                            "line_no":"","description":first,"operation_label":"",
                            "part_price":0,"labor_hours":0,"paint_hours":0,
                            "is_header":True,"supplement":"",
                        })
                        continue

                # Must start with a line number
                if not re.match(r'^\d{1,3}$', first):
                    continue

                line_no = first
                supp = ""
                oper = ""
                desc = ""
                part_no = ""
                price = 0.0
                labor = 0.0
                paint = 0.0
                fi = 1

                # Flag (*, #)
                if fi < len(fields) and fields[fi] in ("*", "#"):
                    fi += 1

                # Supplement (S01, S02)
                if fi < len(fields) and re.match(r'^S\d{2}$', fields[fi]):
                    supp = fields[fi]
                    fi += 1

                # Operation
                if fi < len(fields) and re.match(r'^(R&I|Repl|PDR|Rpr|Blend|O/H|Incl\.?)$', fields[fi]):
                    oper = fields[fi]
                    fi += 1

                # Description parts
                desc_parts = []
                while fi < len(fields):
                    f = fields[fi]
                    if re.match(r'^[\d,]+\.?\d{0,2}$', f) or re.match(r'^[A-Z0-9]{6,20}$', f):
                        break
                    if f in ("X",):
                        fi += 1
                        continue
                    desc_parts.append(f)
                    fi += 1
                desc = " ".join(desc_parts)

                # Part number
                if fi < len(fields) and re.match(r'^[A-Z0-9]{6,20}$', fields[fi]):
                    part_no = fields[fi]
                    fi += 1

                # Quantity
                if fi < len(fields) and re.match(r'^\d{1,2}$', fields[fi]):
                    fi += 1

                # Price
                if fi < len(fields):
                    pf = fields[fi].replace(",", "")
                    if re.match(r'^\d+\.?\d{0,2}$', pf):
                        try:
                            price = float(pf)
                        except ValueError:
                            pass
                        fi += 1

                # Labor hours
                if fi < len(fields) and re.match(r'^-?[\d]+\.[\d]$', fields[fi]):
                    try:
                        labor = float(fields[fi])
                    except ValueError:
                        pass
                    fi += 1

                # Paint hours
                if fi < len(fields) and re.match(r'^-?[\d]+\.[\d]$', fields[fi]):
                    try:
                        paint = float(fields[fi])
                    except ValueError:
                        pass

                if desc:
                    items.append({
                        "line_no": line_no, "description": desc,
                        "operation_label": OP_MAP.get(oper, oper),
                        "operation_code": oper, "part_number": part_no,
                        "part_type": "", "part_price": price,
                        "labor_hours": labor, "paint_hours": paint,
                        "quantity": 1, "supplement": supp,
                        "is_header": False,
                    })

        doc.close()
        return items

    def _group_panels(self, items):
        panels = []
        current = {"name": "Estimate", "rows": []}
        for item in items:
            if item.get("is_header"):
                if current["rows"]:
                    panels.append(current)
                current = {"name": item["description"], "rows": []}
            else:
                rate = 71.0
                item["financial_signature"] = {
                    "part_price": item.get("part_price", 0),
                    "labor_hours_total": item.get("labor_hours", 0),
                    "labor_amount_total": item.get("labor_hours", 0) * rate,
                    "misc_amount": 0,
                }
                current["rows"].append(item)
        if current["rows"]:
            panels.append(current)
        return panels if panels else [{"name": "Estimate", "rows": items}]
