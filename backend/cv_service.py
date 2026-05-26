from typing import List, Dict, Any

class ComputerVisionService:
    @staticmethod
    def analyze_assets(raw_assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simulates a YOLO / CV inference pass over the evidence array.
        Deterministic mock implementation targeting specific filenames to guarantee consistent UI testing.
        """
        enriched_assets = []
        for asset in raw_assets:
            # Transition to cv_pending
            asset["processing_status"] = "cv_pending"
            
            # Simulate inference
            filename = asset.get("filename", "").lower()
            
            cv_predictions = {
                "detected_type": "unknown",
                "confidence": 0.0,
                "damage_area": None
            }
            
            if "bumper" in filename:
                cv_predictions["detected_type"] = "exterior_damage"
                cv_predictions["damage_area"] = "front_bumper"
                cv_predictions["confidence"] = 0.92
            elif "vin" in filename:
                cv_predictions["detected_type"] = "vin_plate"
                cv_predictions["damage_area"] = "vin"
                cv_predictions["confidence"] = 0.98
            elif "invoice" in filename or "sublet" in filename:
                cv_predictions["detected_type"] = "document_invoice"
                cv_predictions["confidence"] = 0.88
            elif "scan" in filename or "autel" in filename:
                cv_predictions["detected_type"] = "document_scan"
                cv_predictions["confidence"] = 0.95
            elif "supplement" in filename:
                cv_predictions["detected_type"] = "document_supplement"
                cv_predictions["confidence"] = 0.85
            else:
                # Generic fallback if not matched
                cv_predictions["detected_type"] = "exterior_damage"
                cv_predictions["damage_area"] = "unspecified_panel"
                cv_predictions["confidence"] = 0.65
                
            asset["cv_inferences"] = cv_predictions
            
            # Final status update
            asset["processing_status"] = "cv_complete"
            
            enriched_assets.append(asset)
            
        return enriched_assets
