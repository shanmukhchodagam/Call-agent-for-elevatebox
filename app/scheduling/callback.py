import re
from datetime import datetime, timedelta
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass
import zoneinfo

from app.config import TIMEZONE


@dataclass
class CallbackSchedule:
    intent_detected: bool
    raw_request: str
    scheduled_time: Optional[datetime]
    iso_scheduled_time: Optional[str]
    timezone: str
    status: str = "scheduled"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_detected": self.intent_detected,
            "raw_request": self.raw_request,
            "scheduled_time": self.iso_scheduled_time,
            "timezone": self.timezone,
            "status": self.status,
        }


WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}


def _get_tz(tz_name: str) -> zoneinfo.ZoneInfo:
    try:
        return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        return zoneinfo.ZoneInfo("UTC")


def parse_callback_time(
    text: str,
    base_time: Optional[datetime] = None,
    tz_str: Optional[str] = None,
) -> Optional[datetime]:
    """
    Parses natural language relative time into a localized datetime.
    Supports expressions such as:
    - 'tomorrow morning' -> tomorrow 10:00
    - 'tomorrow afternoon' -> tomorrow 14:00
    - 'tomorrow evening' -> tomorrow 18:00
    - 'tomorrow at 4 pm' -> tomorrow 16:00
    - 'in 2 hours' / 'in two hours' -> now + 2h
    - 'in 30 minutes' -> now + 30m
    - 'next monday' -> upcoming Monday 10:00
    """
    tz_name = tz_str or TIMEZONE or "Asia/Kolkata"
    tz = _get_tz(tz_name)

    now = base_time if base_time else datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    text_lower = text.lower().strip()

    # 1. "in X hours" / "in X hour" / "after X hours"
    match_hours = re.search(r"(?:in|after)\s+(\d+)\s*hours?", text_lower)
    if match_hours:
        hrs = int(match_hours.group(1))
        return now + timedelta(hours=hrs)

    match_word_hours = re.search(
        r"(?:in|after)\s+(one|two|three|four|five)\s+hours?", text_lower
    )
    if match_word_hours:
        word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        hrs = word_map[match_word_hours.group(1)]
        return now + timedelta(hours=hrs)

    # 2. "in X minutes" / "after X minutes"
    match_mins = re.search(r"(?:in|after)\s+(\d+)\s*(?:minutes?|mins?)", text_lower)
    if match_mins:
        mins = int(match_mins.group(1))
        return now + timedelta(minutes=mins)

    # 3. "tomorrow at X (am/pm)"
    match_tomorrow_time = re.search(
        r"tomorrow\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text_lower
    )
    if match_tomorrow_time:
        hour = int(match_tomorrow_time.group(1))
        minute = int(match_tomorrow_time.group(2) or 0)
        ampm = match_tomorrow_time.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target_day = now + timedelta(days=1)
        return target_day.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # 4. "today at X (am/pm)" / "at X (am/pm)"
    match_today_time = re.search(
        r"(?:today\s+)?at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text_lower
    )
    if match_today_time:
        hour = int(match_today_time.group(1))
        minute = int(match_today_time.group(2) or 0)
        ampm = match_today_time.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            # If the hour already passed today, assume tomorrow
            target += timedelta(days=1)
        return target

    # 5. "tomorrow morning" -> 10:00 AM
    if "tomorrow morning" in text_lower or ("tomorrow" in text_lower and "morning" in text_lower):
        target = now + timedelta(days=1)
        return target.replace(hour=10, minute=0, second=0, microsecond=0)

    # 6. "tomorrow afternoon" -> 2:00 PM (14:00)
    if "tomorrow afternoon" in text_lower or ("tomorrow" in text_lower and "afternoon" in text_lower):
        target = now + timedelta(days=1)
        return target.replace(hour=14, minute=0, second=0, microsecond=0)

    # 7. "tomorrow evening" -> 6:00 PM (18:00)
    if "tomorrow evening" in text_lower or ("tomorrow" in text_lower and "evening" in text_lower):
        target = now + timedelta(days=1)
        return target.replace(hour=18, minute=0, second=0, microsecond=0)

    # 8. Plain "tomorrow" -> tomorrow 10:00 AM
    if "tomorrow" in text_lower:
        target = now + timedelta(days=1)
        return target.replace(hour=10, minute=0, second=0, microsecond=0)

    # 9. "next Monday", "on Friday", etc.
    for day_name, day_idx in WEEKDAYS.items():
        if f"next {day_name}" in text_lower or f"on {day_name}" in text_lower:
            days_ahead = (day_idx - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            target = now + timedelta(days=days_ahead)
            return target.replace(hour=10, minute=0, second=0, microsecond=0)

    return None


def detect_and_parse_callback(
    input_text: Union[str, List[str]],
    base_time: Optional[datetime] = None,
    tz_str: Optional[str] = None,
) -> Optional[CallbackSchedule]:
    """
    Detects callback intent in customer utterances and computes scheduled datetime.
    Returns CallbackSchedule object if intent is found, else None.
    """
    tz_name = tz_str or TIMEZONE or "Asia/Kolkata"

    statements: List[str] = []
    if isinstance(input_text, str):
        statements = [line.strip() for line in input_text.splitlines() if line.strip()]
    elif isinstance(input_text, list):
        statements = input_text

    callback_patterns = [
        r"\b(?:call|ring|reach)\s*(?:me\s*)?(?:back|later|again|tomorrow)?\b",
        r"\b(?:schedule|reschedule)\s*(?:a\s*)?call\b",
        r"\bnot\s+a\s+good\s+time\b",
        r"\bbusy\s+right\s+now\b",
    ]

    for stmt in statements:
        matched = any(re.search(pat, stmt, re.IGNORECASE) for pat in callback_patterns)
        if matched:
            dt = parse_callback_time(stmt, base_time=base_time, tz_str=tz_name)
            if dt is None:
                # Default to next business morning (tomorrow 10:00 AM) if intent present but time vague
                tz = _get_tz(tz_name)
                ref = base_time or datetime.now(tz)
                dt = (ref + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

            return CallbackSchedule(
                intent_detected=True,
                raw_request=stmt,
                scheduled_time=dt,
                iso_scheduled_time=dt.isoformat(),
                timezone=tz_name,
                status="scheduled",
            )

    return None
