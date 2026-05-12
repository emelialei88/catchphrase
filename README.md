# Catchphrase

Capture English phrases and idioms, enrich them with AI, and send the cards to Anki.

![Catchphrase demo](docs/screenshot.png)

## How it works

1. Type a phrase ("bite the bullet", "read the room"…)
2. **Enrich** — Gemini fills in definition, 3 example sentences, register, usage notes, and similar phrases
3. Edit anything inline
4. **Add to Anki** — card lands in your `Catchphrase` deck and auto-syncs to AnkiWeb

## Setup

```bash
pip install -r requirements.txt

./start.sh     # macOS / Linux
start.bat      # Windows
```

Open <http://localhost:7823>. On first run, you'll be prompted to:

1. Grab a free Gemini API key at <https://aistudio.google.com/app/apikey>
2. Paste it into Settings (key is stored in your browser's localStorage)
3. Make sure Anki is running with the AnkiConnect add-on installed

> Alternatively, set `GEMINI_API_KEY` in a `.env` file to skip the in-app prompt.

## Requirements

- **Anki desktop** installed. Catchphrase auto-launches it on macOS, Windows, and Linux when the backend starts (and exposes a "Launch Anki" button in the UI if it's ever closed).
- **AnkiConnect** add-on: in Anki → Tools → Add-ons → Get Add-ons → code `2055492159`
- **AnkiWeb account** configured in Anki preferences if you want phone sync

> The Anki app needs to be running because AnkiConnect lives inside Anki — but Catchphrase handles starting it for you. You can leave Anki minimized in the dock. For zero friction, add Anki to **System Settings → General → Login Items** so it's always running.

## Stack

- FastAPI backend (`main.py`) — `/api/enrich`, `/api/decks`, `/api/add-card`, `/api/anki-status`
- Vanilla JS frontend (`static/`) — no build step
- Gemini 2.5 Flash for enrichment (free tier: 250 req/day)
- AnkiConnect over `localhost:8765` for card injection

## Limits to know

- Anki desktop must be running (AnkiConnect lives inside the Anki process). Catchphrase auto-launches it on all major platforms.
- Gemini free tier sends your inputs to Google for training. Don't paste anything sensitive.
- Duplicate phrases in the same deck are rejected by AnkiConnect.
