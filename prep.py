#!/usr/bin/env python3
"""
Meeting Prep Bot - AI-powered meeting briefings
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

# Optional: for web search
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Config
CALENDARS = os.environ.get("CALENDARS", "").split(",")
CRM_PATH = os.environ.get("CRM_PATH", "./crm/")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
STATE_FILE = os.environ.get("STATE_FILE", ".prep_state.json")


def parse_ics(ics_content: str) -> list[dict]:
    """Parse ICS content into event dicts."""
    events = []
    current_event = None
    
    for line in ics_content.split("\n"):
        line = line.strip()
        
        if line == "BEGIN:VEVENT":
            current_event = {}
        elif line == "END:VEVENT" and current_event:
            events.append(current_event)
            current_event = None
        elif current_event is not None:
            if ":" in line:
                key, value = line.split(":", 1)
                # Handle properties with parameters (e.g., DTSTART;TZID=...)
                key = key.split(";")[0]
                current_event[key] = value
    
    return events


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse ICS datetime string."""
    # Remove Z suffix for UTC
    dt_str = dt_str.rstrip("Z")
    
    # Try various formats
    formats = [
        "%Y%m%dT%H%M%S",
        "%Y%m%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    return None


def extract_attendees(event: dict) -> list[dict]:
    """Extract attendee info from event."""
    attendees = []
    
    # ATTENDEE lines contain mailto: and CN= for name
    for key, value in event.items():
        if key.startswith("ATTENDEE"):
            email_match = re.search(r"mailto:([^\s]+)", value, re.IGNORECASE)
            name_match = re.search(r"CN=([^;:]+)", key + ":" + value)
            
            if email_match:
                attendees.append({
                    "email": email_match.group(1).lower(),
                    "name": name_match.group(1) if name_match else None
                })
    
    return attendees


def search_crm(email: str, crm_path: str) -> Optional[dict]:
    """Search CRM for contact by email."""
    crm_dir = Path(crm_path)
    if not crm_dir.exists():
        return None
    
    for file in crm_dir.glob("**/*.json"):
        try:
            data = json.loads(file.read_text())
            if isinstance(data, dict) and data.get("email", "").lower() == email:
                return data
            if isinstance(data, list):
                for contact in data:
                    if contact.get("email", "").lower() == email:
                        return contact
        except (json.JSONDecodeError, KeyError):
            continue
    
    return None


def web_search(query: str, api_key: str) -> list[dict]:
    """Search web using Brave API."""
    if not HAS_REQUESTS or not api_key:
        return []
    
    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key},
            params={"q": query, "count": 3}
        )
        if resp.ok:
            return resp.json().get("web", {}).get("results", [])
    except Exception:
        pass
    
    return []


def generate_briefing(event: dict, attendees: list[dict]) -> str:
    """Generate meeting briefing."""
    lines = []
    
    # Header
    summary = event.get("SUMMARY", "Meeting")
    location = event.get("LOCATION", "")
    dt_start = parse_datetime(event.get("DTSTART", ""))
    
    lines.append(f"📋 Meeting Briefing: {summary}")
    if location:
        lines.append(f"📍 {location}")
    if dt_start:
        lines.append(f"⏰ {dt_start.strftime('%I:%M %p')} on {dt_start.strftime('%b %d')}")
    
    lines.append("")
    lines.append("👥 Attendees:")
    
    for att in attendees:
        name = att.get("name") or att["email"].split("@")[0]
        domain = att["email"].split("@")[1] if "@" in att["email"] else ""
        
        # Check CRM
        crm_data = search_crm(att["email"], CRM_PATH)
        if crm_data:
            company = crm_data.get("company", domain)
            title = crm_data.get("title", "")
            lines.append(f"• {name} ({att['email']}) - {title} @ {company}")
        else:
            lines.append(f"• {name} ({att['email']}) - {domain}")
    
    return "\n".join(lines)


def load_state() -> dict:
    """Load state file."""
    if os.path.exists(STATE_FILE):
        return json.loads(Path(STATE_FILE).read_text())
    return {"briefed": []}


def save_state(state: dict):
    """Save state file."""
    Path(STATE_FILE).write_text(json.dumps(state, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Meeting Prep Bot")
    parser.add_argument("--check", action="store_true", help="Check upcoming meetings")
    parser.add_argument("--next", action="store_true", help="Brief next meeting")
    parser.add_argument("--auto", action="store_true", help="Auto-brief meetings starting in 30-60 min")
    args = parser.parse_args()
    
    if not CALENDARS or not CALENDARS[0]:
        print("Error: Set CALENDARS environment variable")
        sys.exit(1)
    
    # Fetch all calendars
    all_events = []
    for cal_url in CALENDARS:
        if not cal_url.strip():
            continue
        try:
            with urlopen(cal_url.strip()) as resp:
                ics_content = resp.read().decode("utf-8")
                all_events.extend(parse_ics(ics_content))
        except Exception as e:
            print(f"Warning: Failed to fetch {cal_url}: {e}")
    
    # Filter to upcoming events
    now = datetime.now()
    upcoming = []
    
    for event in all_events:
        dt_start = parse_datetime(event.get("DTSTART", ""))
        if not dt_start:
            continue
        
        # Skip past events
        if dt_start < now:
            continue
        
        # Skip all-day events (no time component)
        if len(event.get("DTSTART", "")) == 8:
            continue
        
        attendees = extract_attendees(event)
        
        # Skip solo events
        if len(attendees) <= 1:
            continue
        
        upcoming.append((dt_start, event, attendees))
    
    # Sort by start time
    upcoming.sort(key=lambda x: x[0])
    
    if args.check:
        print(f"Found {len(upcoming)} upcoming meetings with attendees:\n")
        for dt, event, attendees in upcoming[:10]:
            print(f"  {dt.strftime('%b %d %I:%M %p')} - {event.get('SUMMARY', 'Meeting')} ({len(attendees)} attendees)")
    
    elif args.next and upcoming:
        dt, event, attendees = upcoming[0]
        print(generate_briefing(event, attendees))
    
    elif args.auto:
        state = load_state()
        window_start = now + timedelta(minutes=30)
        window_end = now + timedelta(minutes=60)
        
        for dt, event, attendees in upcoming:
            if window_start <= dt <= window_end:
                event_id = f"{event.get('UID', '')}_{dt.isoformat()}"
                if event_id not in state["briefed"]:
                    print(generate_briefing(event, attendees))
                    state["briefed"].append(event_id)
                    save_state(state)
                    break
        else:
            print("No meetings in the 30-60 minute window.")


if __name__ == "__main__":
    main()
