"""VSTP (Very Short Term Plan) schedule manager for Network Rail data."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, date
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class VstpManager:
    """Manager for VSTP schedule data subscription and lookup."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize VSTP manager.
        
        Args:
            hass: Home Assistant instance
            entry: Config entry
        """
        self.hass = hass
        self.entry = entry
        
        # Schedule storage
        # Index by train_uid for fast lookup
        self._schedules_by_uid: dict[str, dict[str, Any]] = {}
        
        # Index by headcode/train_identity for fast lookup
        # Note: Multiple schedules can have the same headcode at different times
        self._schedules_by_headcode: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        # Track message counts
        self._message_count = 0
        self._schedule_count = 0
        
        _LOGGER.info("VSTP Manager initialized")
    
    def process_vstp_message(self, message: dict[str, Any]) -> None:
        """Process a VSTP schedule message.
        
        Args:
            message: VSTP message from STOMP feed
            
        Expected structure:
        {
            "JsonScheduleV1": {
                "CIF_train_uid": "C12345",
                "schedule_start_date": "2025-12-29",
                "schedule_end_date": "2025-12-29",
                "CIF_train_category": "XX",
                "CIF_power_type": "DMU",
                "train_class": "390",
                "schedule_location": [
                    {
                        "tiploc_code": "EUSTON",
                        "departure": "09:15",
                        "platform": "7",
                        "train_identity": "1F42"
                    }
                ],
                "transaction_type": "Create"
            }
        }
        """
        self._message_count += 1
        
        if "JsonScheduleV1" not in message:
            _LOGGER.debug("VSTP message missing JsonScheduleV1 key")
            return
        
        schedule = message["JsonScheduleV1"]
        
        # Check transaction type
        transaction_type = schedule.get("transaction_type", "Create")
        train_uid = schedule.get("CIF_train_uid")
        
        if not train_uid:
            _LOGGER.warning("VSTP schedule missing train_uid")
            return
        
        # Handle different transaction types
        if transaction_type == "Delete":
            self._delete_schedule(train_uid)
        elif transaction_type in ["Create", "Update"]:
            self._store_schedule(schedule)
        else:
            _LOGGER.debug("Unknown VSTP transaction type: %s", transaction_type)
    
    def _store_schedule(self, schedule: dict[str, Any]) -> None:
        """Store a schedule in the indexes.
        
        Args:
            schedule: JsonScheduleV1 schedule data
        """
        train_uid = schedule.get("CIF_train_uid")
        
        # Check if schedule is valid for today
        if not self._is_schedule_valid_today(schedule):
            _LOGGER.debug("Schedule %s not valid for today, skipping", train_uid)
            return
        
        # Store by UID
        self._schedules_by_uid[train_uid] = schedule
        
        # Extract headcodes from schedule locations
        headcodes = self._extract_headcodes(schedule)
        
        # Store by headcode
        for headcode in headcodes:
            # Check if already in list
            existing = self._schedules_by_headcode[headcode]
            # Remove old entry for same UID if exists
            existing = [s for s in existing if s.get("CIF_train_uid") != train_uid]
            # Add new entry
            existing.append(schedule)
            self._schedules_by_headcode[headcode] = existing
        
        self._schedule_count = len(self._schedules_by_uid)
        
        _LOGGER.debug(
            "Stored VSTP schedule: uid=%s, headcodes=%s, category=%s",
            train_uid,
            headcodes,
            schedule.get("CIF_train_category")
        )
    
    def _delete_schedule(self, train_uid: str) -> None:
        """Delete a schedule from indexes.
        
        Args:
            train_uid: Train UID to delete
        """
        # Remove from UID index
        schedule = self._schedules_by_uid.pop(train_uid, None)
        
        if schedule:
            # Remove from headcode index
            headcodes = self._extract_headcodes(schedule)
            for headcode in headcodes:
                schedules = self._schedules_by_headcode.get(headcode, [])
                schedules = [s for s in schedules if s.get("CIF_train_uid") != train_uid]
                if schedules:
                    self._schedules_by_headcode[headcode] = schedules
                else:
                    self._schedules_by_headcode.pop(headcode, None)
            
            self._schedule_count = len(self._schedules_by_uid)
            _LOGGER.debug("Deleted VSTP schedule: uid=%s", train_uid)
    
    def _is_schedule_valid_today(self, schedule: dict[str, Any]) -> bool:
        """Check if a schedule is valid for today's date.
        
        Args:
            schedule: JsonScheduleV1 schedule data
            
        Returns:
            True if schedule is valid for today
        """
        try:
            start_date_str = schedule.get("schedule_start_date")
            end_date_str = schedule.get("schedule_end_date")
            
            if not start_date_str or not end_date_str:
                return True  # Assume valid if dates not specified
            
            # Parse dates (format: YYYY-MM-DD)
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            today = date.today()
            
            return start_date <= today <= end_date
        except Exception as exc:
            _LOGGER.warning("Error checking schedule validity: %s", exc)
            return True  # Assume valid on error
    
    def _extract_headcodes(self, schedule: dict[str, Any]) -> list[str]:
        """Extract all headcodes/train identities from schedule.
        
        Args:
            schedule: JsonScheduleV1 schedule data
            
        Returns:
            List of unique headcodes found in schedule
        """
        headcodes = set()
        
        schedule_locations = schedule.get("schedule_location", [])
        for location in schedule_locations:
            train_identity = location.get("train_identity")
            if train_identity:
                headcodes.add(train_identity)
        
        return list(headcodes)
    
    def get_schedule_for_uid(self, uid: str) -> dict[str, Any] | None:
        """Get schedule for a given train UID.
        
        Args:
            uid: Train UID (CIF_train_uid)
            
        Returns:
            Schedule data or None if not found
        """
        return self._schedules_by_uid.get(uid)
    
    def get_schedule_for_headcode(self, headcode: str) -> dict[str, Any] | None:
        """Get schedule for a given headcode.
        
        If multiple schedules exist for the same headcode (different times),
        returns the first one found.
        
        Args:
            headcode: Train headcode/identity (e.g., "1F42")
            
        Returns:
            Schedule data or None if not found
        """
        schedules = self._schedules_by_headcode.get(headcode, [])
        return schedules[0] if schedules else None
    
    def get_all_schedules_for_headcode(self, headcode: str) -> list[dict[str, Any]]:
        """Get all schedules for a given headcode.
        
        Args:
            headcode: Train headcode/identity
            
        Returns:
            List of schedule data (may be empty)
        """
        return self._schedules_by_headcode.get(headcode, [])
    
    def get_origin_destination(self, schedule: dict[str, Any]) -> tuple[str | None, str | None]:
        """Extract origin and destination from schedule.
        
        Args:
            schedule: JsonScheduleV1 schedule data
            
        Returns:
            Tuple of (origin, destination) as TIPLOC codes or None
        """
        schedule_locations = schedule.get("schedule_location", [])
        
        if not schedule_locations:
            return None, None
        
        origin = None
        destination = None
        
        # First location with departure is origin
        for location in schedule_locations:
            if location.get("departure"):
                origin = location.get("tiploc_code")
                break
        
        # Last location with arrival is destination
        for location in reversed(schedule_locations):
            if location.get("arrival"):
                destination = location.get("tiploc_code")
                break
        
        return origin, destination
    
    def get_next_scheduled_stop(
        self, 
        schedule: dict[str, Any], 
        current_location: str | None = None
    ) -> dict[str, Any] | None:
        """Get the next scheduled stop for a train.
        
        Args:
            schedule: JsonScheduleV1 schedule data
            current_location: Current TIPLOC code (optional)
            
        Returns:
            Next schedule location dict or None
        """
        schedule_locations = schedule.get("schedule_location", [])
        
        if not schedule_locations:
            return None
        
        # If no current location, return first stop
        if not current_location:
            for location in schedule_locations:
                if location.get("arrival") or location.get("departure"):
                    return location
            return None
        
        # Find current location and return next stop
        found_current = False
        for location in schedule_locations:
            if found_current and (location.get("arrival") or location.get("departure")):
                return location
            if location.get("tiploc_code") == current_location:
                found_current = True
        
        return None
    
    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored schedules.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_messages": self._message_count,
            "total_schedules": self._schedule_count,
            "schedules_by_uid": len(self._schedules_by_uid),
            "unique_headcodes": len(self._schedules_by_headcode),
        }
    
    def clear_cache(self) -> None:
        """Clear all cached schedule data."""
        self._schedules_by_uid.clear()
        self._schedules_by_headcode.clear()
        self._schedule_count = 0
        _LOGGER.info("VSTP cache cleared")
