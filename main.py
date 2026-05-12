import os
import json
import subprocess
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

ANKI_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
STATIC_DIR = Path(__file__).parent / "static"


def launch_anki_if_needed():
    """Best-effort launch of the Anki desktop app. Silently no-ops if Anki isn't installed."""
    try:
        if sys.platform == "darwin":
            cmd = ["open", "-a", "Anki"]
        elif sys.platform.startswith("win"):
            # `start` is a cmd builtin, so shell=True is required.
            subprocess.Popen("start \"\" anki", shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        else:  # linux / *bsd
            cmd = ["anki"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATIC_DIR.mkdir(exist_ok=True)
    launch_anki_if_needed()
    yield


app = FastAPI(title="Catchphrase", lifespan=lifespan)


# ── AnkiConnect helpers ───────────────────────────────────────────────────────

async def anki(action: str, **params):
    payload = {"action": action, "version": 6, "params": params}
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.post(ANKI_URL, json=payload)
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                raise HTTPException(502, f"AnkiConnect: {data['error']}")
            return data["result"]
        except httpx.ConnectError:
            raise HTTPException(503, "AnkiConnect not reachable — is Anki open?")


# ── API routes ────────────────────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    phrase: str

class AddCardRequest(BaseModel):
    deck: str
    phrase: str
    definition: str
    examples: list[str]
    style: str       # register / formality level
    notes: str
    similar: list[str]


ENRICH_PROMPT = """\
You are helping a fluent English speaker capture phrases and idioms for active recall.

Given the phrase: "{phrase}"

Return a JSON object (and ONLY the JSON object, no markdown fences) with these keys:
- "phrase": the canonical form of the phrase (clean it up if needed)
- "definition": a plain-English definition written the way Wiktionary does it — one short
  sentence, everyday words, no jargon. Skip phrases like "refers to" or "is used to describe".
  Just say what it means. Example style: "To start something new with energy and skill,
  doing well right away." If the phrase has multiple senses, give the most common one only.
- "examples": array of exactly 3 natural example sentences using this phrase. Keep each
  under ~15 words. Use varied everyday contexts (work, friends, family — not all business).
- "register": one of "formal", "informal", "neutral", "slang", or "idiomatic"
- "notes": one or two short sentences on when and how people actually use this — tone,
  context, anything that surprises learners. No dictionary stiffness.
- "similar": array of 2-3 closely related phrases or synonyms

Write like you're explaining to a friend, not writing a dictionary entry.\
"""


@app.post("/api/enrich")
async def enrich(req: EnrichRequest, x_gemini_key: str | None = Header(default=None)):
    phrase = req.phrase.strip()
    if not phrase:
        raise HTTPException(400, "phrase is required")

    key = x_gemini_key or GEMINI_KEY
    if not key:
        raise HTTPException(400, "Gemini API key missing — set it in Settings")

    payload = {
        "contents": [{"parts": [{"text": ENRICH_PROMPT.format(phrase=phrase)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4,
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(GEMINI_URL, params={"key": key}, json=payload)
        if r.status_code != 200:
            raise HTTPException(502, f"Gemini error {r.status_code}: {r.text[:300]}")
        body = r.json()

    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise HTTPException(502, f"Gemini returned unexpected response: {e}")


DEFAULT_DECK = "Catchphrase"


@app.get("/api/decks")
async def list_decks():
    decks = await anki("deckNames")
    if DEFAULT_DECK not in decks:
        await anki("createDeck", deck=DEFAULT_DECK)
        decks.append(DEFAULT_DECK)
    return {"decks": sorted(decks), "default": DEFAULT_DECK}


@app.get("/api/anki-status")
async def anki_status():
    try:
        version = await anki("version")
        return {"connected": True, "version": version}
    except HTTPException:
        return {"connected": False}


@app.post("/api/add-card")
async def add_card(req: AddCardRequest):
    examples_html = "".join(f"<li>{e}</li>" for e in req.examples)
    similar_html = ", ".join(f"<em>{s}</em>" for s in req.similar)

    back = f"""\
<div class="catchphrase-card">
  <div class="definition">{req.definition}</div>
  <div class="section-label">Examples</div>
  <ul class="examples">{examples_html}</ul>
  <div class="meta">
    <span class="register">{req.style}</span>
    {"<span class='similar'>See also: " + similar_html + "</span>" if req.similar else ""}
  </div>
  {"<div class='notes'>" + req.notes + "</div>" if req.notes else ""}
</div>"""

    note_id = await anki(
        "addNote",
        note={
            "deckName": req.deck,
            "modelName": "Basic",
            "fields": {"Front": req.phrase, "Back": back},
            "options": {"allowDuplicate": False},
            "tags": ["catchphrase", req.style],
        },
    )

    # Fire-and-forget sync to AnkiWeb so cards appear on phone within seconds.
    synced = True
    try:
        await anki("sync")
    except HTTPException:
        synced = False

    return {"note_id": note_id, "synced": synced}


@app.get("/api/config")
async def get_config():
    return {"server_has_key": bool(GEMINI_KEY)}


@app.post("/api/launch-anki")
async def launch_anki():
    launch_anki_if_needed()
    return {"launched": True, "platform": sys.platform}


# ── Static files (frontend) ───────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")
