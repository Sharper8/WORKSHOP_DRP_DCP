import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request

DB_PATH = os.getenv("DB_PATH", "/data/app.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backup")

app = Flask(__name__)

# ---------- DB helpers ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# ---------- Routes ----------

@app.get("/")
def hello():
    init_db()
    return jsonify(status="Bonjour tout le monde !")


@app.get("/health")
def health():
    init_db()
    return jsonify(status="ok")

@app.get("/add")
def add():
    init_db()

    msg = request.args.get("message", "hello")
    ts = datetime.utcnow().isoformat() + "Z"

    conn = get_conn()
    conn.execute(
        "INSERT INTO events (ts, message) VALUES (?, ?)",
        (ts, msg)
    )
    conn.commit()
    conn.close()

    return jsonify(
        status="added",
        timestamp=ts,
        message=msg
    )

@app.get("/consultation")
def consultation():
    init_db()

    conn = get_conn()
    cur = conn.execute(
        "SELECT id, ts, message FROM events ORDER BY id DESC LIMIT 50"
    )

    rows = [
        {"id": r[0], "timestamp": r[1], "message": r[2]}
        for r in cur.fetchall()
    ]

    conn.close()

    return jsonify(rows)

@app.get("/count")
def count():
    init_db()

    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM events")
    n = cur.fetchone()[0]
    conn.close()

    return jsonify(count=n)


@app.get("/status")
def status():
    init_db()

    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM events")
    event_count = cur.fetchone()[0]
    conn.close()

    backup_path = Path(BACKUP_DIR)
    backup_files = sorted(backup_path.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)

    if not backup_files:
        db_file = Path(DB_PATH)
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
            if db_file.exists():
                bootstrap_name = f"app-bootstrap-{int(time.time())}.db"
                bootstrap_file = backup_path / bootstrap_name
                shutil.copy2(db_file, bootstrap_file)
                backup_files = [bootstrap_file]
        except OSError:
            pass

    if backup_files:
        latest_backup = backup_files[0]
        backup_age_seconds = int(time.time() - latest_backup.stat().st_mtime)
        last_backup_file = latest_backup.name
    else:
        backup_age_seconds = None
        last_backup_file = None

    return jsonify(
        count=event_count,
        last_backup_file=last_backup_file,
        backup_age_seconds=backup_age_seconds,
    )

# ---------- Main ----------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
