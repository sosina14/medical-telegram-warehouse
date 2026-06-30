"""
scripts/setup_db.py
Creates the database and all schemas if they don't exist.
Run this ONCE before load_to_postgres.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

HOST     = os.getenv("POSTGRES_HOST", "localhost")
PORT     = int(os.getenv("POSTGRES_PORT", 5432))
USER     = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres123")
DBNAME   = os.getenv("POSTGRES_DB", "medical_warehouse")

# ── Step 1: connect to default 'postgres' DB to create our DB ────────────────
print(f"[INFO] Connecting to PostgreSQL at {HOST}:{PORT} as '{USER}'...")
try:
    conn = psycopg2.connect(
        host=HOST, port=PORT,
        dbname="postgres",        # connect to default db first
        user=USER, password=PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Check if DB already exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DBNAME,))
    exists = cur.fetchone()

    if not exists:
        cur.execute(f'CREATE DATABASE "{DBNAME}"')
        print(f"[OK]   Database '{DBNAME}' created")
    else:
        print(f"[OK]   Database '{DBNAME}' already exists")

    cur.close()
    conn.close()

except psycopg2.OperationalError as e:
    print(f"\n[ERROR] Cannot connect to PostgreSQL: {e}")
    print("\nMake sure PostgreSQL is running on your machine.")
    print("On Windows: search 'Services' → find 'postgresql-x64-XX' → Start")
    raise SystemExit(1)

# ── Step 2: connect to our new DB and create schemas ────────────────────────
conn2 = psycopg2.connect(
    host=HOST, port=PORT,
    dbname=DBNAME,
    user=USER, password=PASSWORD
)
cur2 = conn2.cursor()

cur2.execute("""
    CREATE SCHEMA IF NOT EXISTS raw;
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE SCHEMA IF NOT EXISTS marts;
""")

cur2.execute("""
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
""")

conn2.commit()
cur2.close()
conn2.close()

print("[OK]   Schemas created: raw, staging, marts")
print("[OK]   Table raw.telegram_messages ready")
print("\n[DONE] Database setup complete — now run: python scripts/load_to_postgres.py")
