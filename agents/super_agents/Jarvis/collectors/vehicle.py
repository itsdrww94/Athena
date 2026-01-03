import re
from typing import List, Dict, Any
from .base import BaseCollector

class VehicleCollector(BaseCollector):
    """
    Vehicle Artifact Intelligence.
    Spec Section 6.7: Modern vs Classic VIN, historical mentions.
    """
    
    MODERN_VIN_REGEX = r"^[A-HJ-NPR-Z0-9]{17}$"
    CLASSIC_VIN_REGEX = r"^[A-Z0-9]{8,12}$"  # Pre-1981 VINs were shorter
    
    def _collect(self, target: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        target = target.upper().strip()
        
        # Classify VIN type
        if re.match(self.MODERN_VIN_REGEX, target):
            vin_type = "modern"
            # Modern VIN: positions have meaning
            # WMI (1-3), VDS (4-9), VIS (10-17)
            wmi = target[:3]
            findings.append({
                "type": "vin_modern",
                "value": target,
                "wmi": wmi,
                "manufacturer_hint": self._decode_wmi(wmi),
                "confidence": 0.9
            })
        elif re.match(self.CLASSIC_VIN_REGEX, target):
            vin_type = "classic"
            findings.append({
                "type": "vin_classic",
                "value": target,
                "note": "Classic VIN detected. Pivot to forum/auction search.",
                "confidence": 0.7
            })
        else:
            findings.append({
                "type": "vin_invalid",
                "value": target,
                "confidence": 0.0
            })
            
        return findings

    def _decode_wmi(self, wmi: str) -> str:
        """Simple WMI country hint."""
        if wmi.startswith("1") or wmi.startswith("4") or wmi.startswith("5"):
            return "USA"
        elif wmi.startswith("J"):
            return "Japan"
        elif wmi.startswith("W"):
            return "Germany"
        return "Unknown"
