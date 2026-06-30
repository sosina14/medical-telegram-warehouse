"""
scripts/load_to_postgres.py
Reads all JSON files from the data lake and loads into raw.telegram_messages
"""

import os
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB", "medical_warehouse"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

DATA_DIR = Path("data/raw/telegram_messages")

CREATE_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.telegram_messages (
    message_id    BIGINT,
    channel_name  VARCHAR(255),
    message_date  TIMESTAMP,
    message_text  TEXT,
    has_media     BOOLEAN DEFAULT FALSE,
    image_path    VARCHAR(500),
    views         INTEGER DEFAULT 0,
    forwards      INTEGER DEFAULT 0,
    scraped_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (message_id, channel_name)
);
"""

INSERT_SQL = """
    INSERT INTO raw.telegram_messages
        (message_id, channel_name, message_date, message_text,
         has_media, image_path, views, forwards)
    VALUES %s
    ON CONFLICT (message_id, channel_name) DO NOTHING
"""

def load_all():
    conn   = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Create schema + table if they don't exist
    cursor.execute(CREATE_SCHEMA_SQL)
    conn.commit()
    print("[INFO] Schema ready")

    total = 0
    json_files = sorted(DATA_DIR.rglob("*.json"))

    if not json_files:
        print("[WARN] No JSON files found in data/raw/telegram_messages/")
        print("       Make sure the scraper ran and created data files.")
        return

    for json_file in json_files:
        records = json.loads(json_file.read_text(encoding="utf-8"))
        if not records:
            continue

        rows = [
            (
                r["message_id"],
                r["channel_name"],
                r.get("message_date"),
                r.get("message_text", ""),
                r.get("has_media", False),
                r.get("image_path"),
                max(r.get("views", 0) or 0, 0),
                max(r.get("forwards", 0) or 0, 0),
            )
            for r in records
            if r.get("message_id") and r.get("message_text", "").strip()
        ]

        if rows:
            execute_values(cursor, INSERT_SQL, rows)
            conn.commit()
            total += len(rows)
            print(f"[INFO] Loaded {len(rows):>5} rows  ← {json_file}")

    cursor.close()
    conn.close()
    print(f"\n[DONE] Total rows loaded: {total}")

if __name__ == "__main__":
    load_all()
