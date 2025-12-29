"""Service classification for train services based on VSTP data and headcode patterns."""

from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Train category codes from VSTP CIF
# Maps CIF_train_category to service type
CATEGORY_TYPES = {
    "OO": "ordinary_passenger",
    "OW": "ordinary_passenger",
    "XC": "express_passenger",
    "XX": "express_passenger",
    "XZ": "sleeper",
    "BR": "bus_replacement",
    "BS": "bus_wtt",
    "EE": "empty_coaching_stock",
    "EL": "empty_coaching_stock",
    "ES": "empty_coaching_stock",
    "JJ": "postal",
    "PM": "postal",
    "PP": "parcels",
    "PV": "parcels",
    # Note: Freight uses different category codes
    "XY": "freight_special",
}

# Freight category codes (separate as they have different patterns)
FREIGHT_CATEGORIES = {
    "B": "freight_automotive",
    "E": "freight_empty",
    "F": "freight_freightliner",
    "G": "freight_general",
    "H": "freight_aggregates",
    "J": "freight_freight_trip",
    "M": "freight_intermodal",
    "Q": "freight_other",
    "R": "freight_infrastructure",
    "S": "freight_steel",
}

# Special service detection patterns

# RHTT (Rail Head Treatment Train) patterns
# Headcodes: 3Hxx or 3Yxx
# Operating characteristics: Contains "R"
RHTT_HEADCODE_PATTERN = re.compile(r"^3[HY]\d{2}$")

# Steam service patterns
# Often use 1Zxx headcodes for charter trains
STEAM_HEADCODE_PATTERN = re.compile(r"^1Z\d{2}$")

# Royal Train pattern
# 1X99 is reserved for royal trains
ROYAL_TRAIN_HEADCODE_PATTERN = re.compile(r"^1X99$")

# Freight headcode patterns
# 0xxx, 4xxx, 6xxx, 7xxx series
FREIGHT_HEADCODE_PATTERN = re.compile(r"^[0467]\w{3}$")

# Empty coaching stock (ECS) patterns
# 5xxx series headcodes
ECS_HEADCODE_PATTERN = re.compile(r"^5\w{3}$")

# Charter/Special patterns
# 1Zxx headcodes (also used for steam)
CHARTER_HEADCODE_PATTERN = re.compile(r"^1Z\d{2}$")

# Pullman/Luxury patterns
# Often identifiable by train class or operator
PULLMAN_KEYWORDS = ["pullman", "orient express", "luxury", "belmond"]


def classify_service(vstp_data: dict[str, Any] | None, headcode: str) -> dict[str, Any]:
    """Classify a train service based on VSTP schedule data and headcode patterns.
    
    Args:
        vstp_data: VSTP schedule data (JsonScheduleV1 structure), or None if not available
        headcode: Train headcode/train_id (e.g., "1F42", "6M94", "3H01")
        
    Returns:
        Dictionary with classification results:
        {
            "service_type": str,          # Primary service type
            "service_category": str,      # More specific category
            "description": str,           # Human-readable description
            "is_freight": bool,           # Whether this is a freight service
            "is_passenger": bool,         # Whether this is a passenger service
            "is_special": bool,           # Whether this is a special service (steam, royal, etc.)
            "special_types": list[str],   # List of special classifications (e.g., ["rhtt", "steam"])
            "alert_worthy": bool,         # Whether this might be worth alerting on
        }
    """
    result = {
        "service_type": "unknown",
        "service_category": "unknown",
        "description": "Unknown service",
        "is_freight": False,
        "is_passenger": False,
        "is_special": False,
        "special_types": [],
        "alert_worthy": False,
    }
    
    # Check for special patterns first (highest priority)
    special_types = _detect_special_services(vstp_data, headcode)
    if special_types:
        result["special_types"] = special_types
        result["is_special"] = True
        result["alert_worthy"] = True
        
        # Set primary service type based on special types
        if "royal_train" in special_types:
            result["service_type"] = "royal_train"
            result["service_category"] = "royal_train"
            result["description"] = "Royal Train"
        elif "steam" in special_types:
            result["service_type"] = "charter"
            result["service_category"] = "steam_charter"
            result["description"] = "Steam Charter Service"
            result["is_passenger"] = True
        elif "rhtt" in special_types:
            result["service_type"] = "infrastructure"
            result["service_category"] = "rhtt"
            result["description"] = "Rail Head Treatment Train"
        elif "pullman" in special_types:
            result["service_type"] = "passenger"
            result["service_category"] = "luxury_charter"
            result["description"] = "Pullman/Luxury Charter"
            result["is_passenger"] = True
        elif "charter" in special_types:
            result["service_type"] = "passenger"
            result["service_category"] = "charter"
            result["description"] = "Charter Service"
            result["is_passenger"] = True
    
    # Use VSTP data if available
    if vstp_data:
        category = vstp_data.get("CIF_train_category", "")
        power_type = vstp_data.get("CIF_power_type", "")
        train_class = vstp_data.get("train_class", "")
        operating_chars = vstp_data.get("operating_characteristics", "")
        
        # Check for RHTT in operating characteristics
        if "R" in operating_chars and "rhtt" not in result["special_types"]:
            result["special_types"].append("rhtt")
            result["is_special"] = True
            result["alert_worthy"] = True
            if result["service_type"] == "unknown":
                result["service_type"] = "infrastructure"
                result["service_category"] = "rhtt"
                result["description"] = "Rail Head Treatment Train"
        
        # Classify based on VSTP category
        if category in CATEGORY_TYPES and result["service_type"] == "unknown":
            service_type = CATEGORY_TYPES[category]
            result["service_type"] = service_type
            result["service_category"] = category
            
            if "passenger" in service_type:
                result["is_passenger"] = True
                result["description"] = service_type.replace("_", " ").title()
            elif "empty_coaching_stock" in service_type:
                result["description"] = "Empty Coaching Stock"
            elif "bus" in service_type:
                result["is_passenger"] = True
                result["description"] = "Bus Replacement Service"
            elif service_type in ["postal", "parcels"]:
                result["description"] = service_type.title()
            elif service_type == "freight_special":
                result["is_freight"] = True
                result["is_special"] = True
                result["alert_worthy"] = True
                result["description"] = "Special Freight Service"
        
        # Check for freight categories
        if category in FREIGHT_CATEGORIES and result["service_type"] == "unknown":
            result["is_freight"] = True
            result["service_type"] = "freight"
            result["service_category"] = FREIGHT_CATEGORIES[category]
            result["description"] = FREIGHT_CATEGORIES[category].replace("_", " ").title()
            result["alert_worthy"] = True
    
    # Fall back to headcode-based classification if still unknown
    if result["service_type"] == "unknown":
        headcode_result = _classify_by_headcode(headcode)
        result.update(headcode_result)
    
    return result


def _detect_special_services(vstp_data: dict[str, Any] | None, headcode: str) -> list[str]:
    """Detect special service types from VSTP data and headcode.
    
    Args:
        vstp_data: VSTP schedule data, or None
        headcode: Train headcode
        
    Returns:
        List of special service type strings (e.g., ["rhtt"], ["steam", "charter"])
    """
    special_types = []
    
    # Check for Royal Train
    if ROYAL_TRAIN_HEADCODE_PATTERN.match(headcode):
        special_types.append("royal_train")
        return special_types  # Royal train is the highest priority
    
    # Check for RHTT
    if RHTT_HEADCODE_PATTERN.match(headcode):
        special_types.append("rhtt")
    
    # Check VSTP data for RHTT operating characteristic
    if vstp_data:
        operating_chars = vstp_data.get("operating_characteristics", "")
        if "R" in operating_chars and "rhtt" not in special_types:
            special_types.append("rhtt")
    
    # Check for Steam (often 1Zxx charter trains)
    if STEAM_HEADCODE_PATTERN.match(headcode):
        # Could be steam, but 1Zxx is general charter code
        # We'll mark as charter, and steam can be confirmed from VSTP data
        special_types.append("charter")
        
        # Check VSTP for steam power type
        if vstp_data:
            power_type = vstp_data.get("CIF_power_type", "")
            if power_type in ["HST", "STEAM"]:  # Note: STEAM might not be in standard codes
                special_types.append("steam")
    
    # Check for Pullman/Luxury services
    if vstp_data:
        # Check train class, operator, or schedule location names
        train_class = vstp_data.get("train_class", "").lower()
        
        # Check schedule locations for pullman/luxury indicators
        schedule_locations = vstp_data.get("schedule_location", [])
        for location in schedule_locations:
            train_identity = location.get("train_identity", "").lower()
            if any(keyword in train_identity for keyword in PULLMAN_KEYWORDS):
                special_types.append("pullman")
                break
        
        # Check if any pullman keywords in class or other fields
        if any(keyword in train_class for keyword in PULLMAN_KEYWORDS):
            special_types.append("pullman")
    
    # Check for general charter (1Zxx that's not already identified)
    if CHARTER_HEADCODE_PATTERN.match(headcode) and "charter" not in special_types:
        special_types.append("charter")
    
    return special_types


def _classify_by_headcode(headcode: str) -> dict[str, Any]:
    """Classify service based solely on headcode patterns.
    
    Args:
        headcode: Train headcode
        
    Returns:
        Partial classification dictionary
    """
    result = {
        "service_type": "unknown",
        "service_category": "unknown",
        "description": f"Train {headcode}",
        "is_freight": False,
        "is_passenger": False,
        "is_special": False,
        "alert_worthy": False,
    }
    
    # Freight patterns (0xxx, 4xxx, 6xxx, 7xxx)
    if FREIGHT_HEADCODE_PATTERN.match(headcode):
        result["service_type"] = "freight"
        result["service_category"] = "freight_unclassified"
        result["description"] = "Freight Service"
        result["is_freight"] = True
        result["alert_worthy"] = True
        return result
    
    # Empty Coaching Stock (5xxx)
    if ECS_HEADCODE_PATTERN.match(headcode):
        result["service_type"] = "empty_coaching_stock"
        result["service_category"] = "ecs"
        result["description"] = "Empty Coaching Stock"
        return result
    
    # Charter trains (1Zxx) - already handled in special services
    # But include here as fallback
    if CHARTER_HEADCODE_PATTERN.match(headcode):
        result["service_type"] = "passenger"
        result["service_category"] = "charter"
        result["description"] = "Charter Service"
        result["is_passenger"] = True
        result["is_special"] = True
        result["alert_worthy"] = True
        return result
    
    # Passenger trains (1xxx, 2xxx, 3xxx - excluding special patterns)
    # This is a broad catch-all for passenger services
    if headcode and len(headcode) == 4 and headcode[0] in "123":
        result["service_type"] = "passenger"
        result["service_category"] = "passenger_unclassified"
        result["description"] = "Passenger Service"
        result["is_passenger"] = True
        return result
    
    return result


def should_alert_for_service(
    classification: dict[str, Any],
    alert_config: dict[str, bool]
) -> tuple[bool, str | None]:
    """Determine if a service should trigger an alert based on configuration.
    
    Args:
        classification: Service classification from classify_service()
        alert_config: Dictionary of alert settings:
            {
                "freight": bool,
                "rhtt": bool,
                "steam": bool,
                "charter": bool,
                "pullman": bool,
                "royal_train": bool,
                "named_trains": bool,
            }
            
    Returns:
        Tuple of (should_alert: bool, alert_reason: str | None)
    """
    if not alert_config:
        return False, None
    
    # Check special types first
    for special_type in classification.get("special_types", []):
        if alert_config.get(special_type, False):
            return True, f"Special service: {special_type}"
    
    # Check freight
    if classification.get("is_freight", False) and alert_config.get("freight", False):
        return True, "Freight service"
    
    # Check general passenger charter/special
    if classification.get("is_special", False) and alert_config.get("charter", False):
        return True, "Special/Charter service"
    
    return False, None
