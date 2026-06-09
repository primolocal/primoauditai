"""
CarDD trained model inference wrapper.
Drop-in replacement for the Ollama-based vision analysis.

Setup:
  1. git clone https://github.com/CarDD-USTC/CarDD-USTC.github.io.git
  2. cd CarDD-USTC.github.io/code/CarDD_detection
  3. pip install openmim && mim install mmdet && pip install mmcv==1.7.0
  4. Download pretrained epoch_24.pth from MMDetection Model Zoo
  5. Set CARD_MODEL_PATH and CARD_CONFIG_PATH env vars

Usage:
  from cardd_inference import CarDDDetector
  detector = CarDDDetector()
  results = detector.detect("damage.jpg")
  # returns: [{"label": "dent", "confidence": 0.92, "bbox": [x,y,w,h]}, ...]
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

CARD_REPO = os.getenv("CARD_REPO_PATH", "./CarDD-USTC.github.io")
CARD_CONFIG = os.getenv("CARD_CONFIG_PATH", "configs/car_damage/DCN_plus_cfg.py")
CARD_WEIGHTS = os.getenv("CARD_WEIGHTS_PATH", "epoch_24.pth")

DAMAGE_LABELS = [
    "dent",
    "scratch", 
    "crack",
    "glass break",
    "lamp break",
    "rust/corrosion",
]


class CarDDDetector:
    """Wrapper around the CarDD MMDetection model for inference."""
    
    def __init__(self):
        self.inference_script = Path(CARD_REPO) / "code/CarDD_detection/tools/inference.py"
        self.config = Path(CARD_REPO) / "code/CarDD_detection" / CARD_CONFIG
        self.weights = Path(CARD_REPO) / "code/CarDD_detection" / CARD_WEIGHTS
        
        if not self.inference_script.exists():
            raise FileNotFoundError(
                f"CarDD inference script not found at {self.inference_script}. "
                f"Clone the repo: git clone https://github.com/CarDD-USTC/CarDD-USTC.github.io.git"
            )
        if not self.weights.exists():
            raise FileNotFoundError(
                f"CarDD weights not found at {self.weights}. "
                f"Download from MMDetection Model Zoo or train on CarDD dataset."
            )
    
    def detect(self, image_path: str) -> list[dict[str, Any]]:
        """Run CarDD detection on a single image. Returns list of detections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.inference_script.parent.parent)
            env["MPLBACKEND"] = "Agg"
            
            result = subprocess.run(
                [
                    "python", str(self.inference_script),
                    "--img-path", image_path,
                    "--save-path", str(save_dir),
                    "--config-file", str(self.config),
                    "--checkpoint-file", str(self.weights),
                    "--show-score-thr", "0.5",
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            
            # Parse output JSON from MMDetection
            json_files = list(save_dir.glob("*.json"))
            if json_files:
                with open(json_files[0]) as f:
                    detections = json.load(f)
                return self._format_detections(detections)
            
            # Fallback: parse from stdout
            return self._parse_stdout(result.stdout)
    
    def _format_detections(self, raw: list[dict]) -> list[dict[str, Any]]:
        """Format MMDetection output to standard format."""
        results = []
        for det in raw:
            label_idx = det.get("category_id", 0)
            if label_idx < len(DAMAGE_LABELS):
                results.append({
                    "label": DAMAGE_LABELS[label_idx],
                    "confidence": round(det.get("score", 0), 3),
                    "bbox": det.get("bbox", []),
                    "area": det.get("area", 0),
                })
        return sorted(results, key=lambda x: x["confidence"], reverse=True)
    
    def _parse_stdout(self, stdout: str) -> list[dict[str, Any]]:
        """Fallback parser for MMDetection text output."""
        results = []
        for line in stdout.split("\n"):
            if "class" in line.lower() and "score" in line.lower():
                parts = line.strip().split()
                for i, label in enumerate(DAMAGE_LABELS):
                    if label.lower() in line.lower():
                        try:
                            conf = float(parts[-1])
                            results.append({"label": label, "confidence": conf, "bbox": []})
                        except (ValueError, IndexError):
                            pass
        return results


# ── FastAPI integration ──
# Replace the Ollama call in vision.py with:
#
#   detector = CarDDDetector()
#   results = detector.detect(temp_image_path)
#
# That's it. Same API contract, better accuracy.
