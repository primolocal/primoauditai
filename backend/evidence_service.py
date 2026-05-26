from typing import Dict, Any, List

from cv_service import ComputerVisionService

class EvidenceMappingService:
    @staticmethod
    def classify_and_map(parsed_data: Dict[str, Any], raw_assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determines doc_type and photo damage_area based on Computer Vision heuristics.
        """
        enriched_assets = ComputerVisionService.analyze_assets(raw_assets)
        documents = []
        photos = []
        
        for asset in enriched_assets:
            cv = asset.get("cv_inferences", {})
            detected_type = cv.get("detected_type", "unknown")
            confidence = cv.get("confidence", 0.0)
            
            # Sub-split into specific structures
            if "document" in detected_type or asset["filename"].lower().endswith('.pdf'):
                doc_type = detected_type.split("_")[1] if "_" in detected_type else "generic_pdf"
                doc = {
                    "id": asset["id"],
                    "filename": asset["filename"],
                    "doc_type": doc_type,
                    "source_url": asset["source_url"],
                    "thumbnail_url": asset["thumbnail_url"],
                    "processing_status": "complete",
                    "is_mock": asset.get("is_mock", False)
                }
                documents.append(doc)
            else:
                photo_type = "vin" if "vin" in detected_type else "exterior"
                photo = {
                    "id": asset["id"],
                    "url": asset["source_url"],
                    "thumbnail_url": asset["thumbnail_url"],
                    "type": photo_type,
                    "damage_area": cv.get("damage_area"),
                    "clarity": "unknown",
                    "confidence": confidence
                }
                photos.append(photo)
            
        evidence_matrix = parsed_data.get("evidence_matrix", {})
        evidence_matrix["documents"] = documents
        evidence_matrix["photos"] = photos
        evidence_matrix["processing_status"] = "complete"
        parsed_data["evidence_matrix"] = evidence_matrix
        
        return parsed_data
