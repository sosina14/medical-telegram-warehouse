"""
src/scraper.py
Telegram channel scraper — Task 1
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Try to load .env file — look in current dir AND parent dirs
from dotenv import load_dotenv

# Load .env from the project root (works whether you run from src/ or root)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"[INFO] Loaded .env from {env_path}")
else:
    load_dotenv()  # fallback: search current directory
    print(f"[WARN] .env not found at {env_path}, trying current directory")

# ── Validate credentials before doing anything else ───────────────────────────
API_ID_RAW   = os.getenv("TELEGRAM_API_ID")
API_HASH     = os.getenv("TELEGRAM_API_HASH")
PHONE        = os.getenv("TELEGRAM_PHONE")

if not API_ID_RAW:
    raise SystemExit(
        "\n[ERROR] TELEGRAM_API_ID not found.\n"
        "Make sure your .env file exists at the project root and contains:\n"
        "  TELEGRAM_API_ID=12345678\n"
        "  TELEGRAM_API_HASH=abcdef...\n"
        "  TELEGRAM_PHONE=+251XXXXXXXXX\n"
    )

API_ID  = int(API_ID_RAW)
SESSION = "medical_scraper"

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaPhoto

# ── Channels ──────────────────────────────────────────────────────────────────
CHANNELS = [
    "CheMed",
    "lobelia4cosmetics",
    "tikvahethiopiaph",
    "DoctorsETBot",
]

# ── Directories ───────────────────────────────────────────────────────────────
DATA_LAKE  = Path("data/raw/telegram_messages")
IMAGE_ROOT = Path("data/raw/images")
STATE_FILE = Path("data/.scrape_state.json")
LOG_DIR    = Path("logs")

# ── Logging (stdlib only — no loguru dependency) ──────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"scraper_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),                      # print to terminal
        logging.FileHandler(log_file, encoding="utf-8"),  # save to file
    ],
)
log = logging.getLogger(__name__)
log.info(f"Logging to {log_file}")


# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Scrape one channel ────────────────────────────────────────────────────────

async def scrape_channel(client: TelegramClient, channel: str, state: dict) -> list:
    messages  = []
    last_id   = state.get(channel, 0)
    image_dir = IMAGE_ROOT / channel
    image_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"[{channel}] Starting — last_id={last_id}")

    try:
        entity = await client.get_entity(channel)
    except Exception as exc:
        log.error(f"[{channel}] Could not resolve channel: {exc}")
        return messages

    try:
        async for msg in client.iter_messages(entity, min_id=last_id, limit=None):
            await asyncio.sleep(0.5)          # polite delay

            has_media  = isinstance(msg.media, MessageMediaPhoto)
            image_path = None

            if has_media:
                img_file = image_dir / f"{msg.id}.jpg"
                if not img_file.exists():
                    try:
                        await client.download_media(msg.media, file=str(img_file))
                        log.info(f"[{channel}] Downloaded image {msg.id}.jpg")
                    except Exception as exc:
                        log.warning(f"[{channel}] Image download failed (msg {msg.id}): {exc}")
                        has_media = False
                image_path = str(img_file) if img_file.exists() else None

            record = {
                "message_id":   msg.id,
                "channel_name": channel,
                "message_date": msg.date.isoformat() if msg.date else None,
                "message_text": msg.text or "",
                "has_media":    has_media,
                "image_path":   image_path,
                "views":        msg.views    or 0,
                "forwards":     msg.forwards or 0,
            }
            messages.append(record)

            if msg.id > last_id:
                last_id = msg.id

    except FloodWaitError as exc:
        log.warning(f"[{channel}] FloodWait — sleeping {exc.seconds}s")
        await asyncio.sleep(exc.seconds)
    except Exception as exc:
        log.error(f"[{channel}] Unexpected error: {exc}")

    state[channel] = last_id
    log.info(f"[{channel}] Done — {len(messages)} messages collected")
    return messages


# ── Save to data lake ─────────────────────────────────────────────────────────

async def save_to_data_lake(channel: str, messages: list):
    if not messages:
        log.info(f"[{channel}] No new messages — nothing to save")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir  = DATA_LAKE / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{channel}.json"
    out_file.write_text(json.dumps(messages, indent=2, ensure_ascii=False))
    log.info(f"[{channel}] Saved {len(messages)} records → {out_file}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    state  = load_state()
    client = TelegramClient(SESSION, API_ID, API_HASH)

    print("\n[INFO] Connecting to Telegram...")
    print("[INFO] First time? You will receive a code on your phone/app — type it below.\n")
    await client.start(phone=PHONE)
    log.info("Telegram client connected ✓")

    for channel in CHANNELS:
        messages = await scrape_channel(client, channel, state)
        await save_to_data_lake(channel, messages)
        save_state(state)

    await client.disconnect()
    log.info("All channels scraped ✓")


if __name__ == "__main__":
    asyncio.run(main())
