# Meeting Prep Bot 🗓️

AI-powered meeting briefings delivered before your calendar events.

## What It Does

Automatically generates pre-meeting briefings by:
1. Fetching your Google Calendar (ICS feed)
2. Identifying meetings with external attendees (skips solo reminders)
3. For each attendee:
   - Searches CRM for existing contact data
   - Pulls recent news and LinkedIn updates
   - Checks if their company is in your portfolio
   - Finds past meeting notes
4. Delivers a concise briefing 30 minutes before

## Sample Output

```
📋 Meeting Briefing: Mute + RTP Lunch
📍 La Dong, 11 E 17th St, NYC
⏰ 12:30 PM ET

👥 Attendees:
• Tom (tom@rtp.vc) - RTP Global
• Robert B (robertb@rtp.vc) - RTP Global

🏢 About RTP Global:
- Global early-stage VC (NYC, founded 2000)
- Focus: AI/ML, B2B SaaS, Fintech, Health
- Notable: Datadog, DeliveryHero
- 1 in 10 portfolio companies reached unicorn

💡 Context:
Peer VC relationship meeting - likely discussing
co-investment opportunities or deal flow sharing.
```

## Setup

### Requirements
- Python 3.9+
- Access to Google Calendar ICS feeds
- CRM data (optional, enhances briefings)
- Brave Search API key (for attendee research)

### Configuration

```python
# config.py
CALENDARS = [
    "https://calendar.google.com/calendar/ical/you@company.com/private-xxx/basic.ics"
]

CRM_PATH = "./crm/"  # Directory with contact files
BRAVE_API_KEY = "your-key"
```

### Running

```bash
# Check upcoming meetings
python prep.py --check

# Generate briefing for next meeting
python prep.py --next

# Run as cron (every 30 min)
*/30 * * * * cd /path/to/meeting-prep-bot && python prep.py --auto
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Calendar Fetch │────▶│  Attendee       │────▶│  Briefing       │
│  (ICS Parser)   │     │  Enrichment     │     │  Generator      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               ┌────────┐ ┌────────┐ ┌────────┐
               │  CRM   │ │  Web   │ │ Past   │
               │ Lookup │ │ Search │ │ Notes  │
               └────────┘ └────────┘ └────────┘
```

## Filtering Logic

The bot skips:
- ❌ Meetings with only 1 attendee (self-reminders)
- ❌ All-day events
- ❌ Declined invitations
- ❌ Meetings already briefed (tracks in state file)

## Integration

Works great with:
- [OpenClaw](https://github.com/openclaw/openclaw) - Run as a cron job
- Telegram/Slack - Deliver briefings to chat
- Obsidian - Pull past meeting notes

## License

MIT
