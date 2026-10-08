"""db.py - SQLite เก็บประวัติเหตุการณ์ Warning / Danger"""
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "drowsiness.db"
_lock = threading.Lock()
_conn = None


def _db():
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                session_id TEXT NOT NULL,
                model TEXT NOT NULL,
                status TEXT NOT NULL,
                closed_seconds REAL NOT NULL,
                p_closed REAL
            )"""
        )
        cols = {r["name"] for r in _conn.execute("PRAGMA table_info(events)")}
        if "reason" not in cols:  # ฐานข้อมูลเดิมยังไม่มีคอลัมน์นี้
            _conn.execute("ALTER TABLE events ADD COLUMN reason TEXT")
        if "yaw" not in cols:
            _conn.execute("ALTER TABLE events ADD COLUMN yaw REAL")
        _conn.commit()
    return _conn


def log_event(session_id, model, status, seconds, p_closed, reason="eyes", yaw=None):
    with _lock:
        c = _db()
        c.execute(
            "INSERT INTO events (ts, session_id, model, status, closed_seconds, p_closed, reason, yaw) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), session_id, model, status, seconds, p_closed, reason, yaw),
        )
        c.commit()


def list_events(limit=200):
    with _lock:
        rows = _db().execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def stats():
    with _lock:
        c = _db()
        by_model = [dict(r) for r in c.execute(
            """SELECT model,
                      SUM(status='Warning') AS warnings,
                      SUM(status='Danger') AS dangers
               FROM events GROUP BY model ORDER BY model""")]
        t = c.execute(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(status='Warning'), 0) AS warnings,
                      COALESCE(SUM(status='Danger'), 0) AS dangers,
                      COALESCE(SUM(reason='distracted'), 0) AS distracted,
                      COUNT(DISTINCT session_id) AS sessions,
                      MAX(ts) AS last_event
               FROM events""").fetchone()
    return {**dict(t), "by_model": by_model}


def clear_events():
    with _lock:
        c = _db()
        c.execute("DELETE FROM events")
        c.commit()
