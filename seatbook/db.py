"""
Tiny database layer.

- On Vercel (or anywhere) with DATABASE_URL set  -> PostgreSQL (e.g. Neon)
- Locally with no DATABASE_URL                    -> SQLite file (seatdesk.db)

Write SQL with `?` placeholders; they are converted for Postgres automatically.
"""
import os
import sqlite3

from flask import g

DATABASE_URL = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "").strip()
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
ON_VERCEL = bool(os.environ.get("VERCEL"))

if IS_PG:
    import psycopg2
    import psycopg2.extras

    IntegrityError = psycopg2.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError
    if ON_VERCEL:
        # Vercel's disk is temporary: data here is lost on every cold start.
        SQLITE_PATH = "/tmp/seatdesk.db"
    else:
        SQLITE_PATH = os.environ.get(
            "SQLITE_PATH",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "seatdesk.db"),
        )

# False only when running on Vercel without a real database
PERSISTENT = IS_PG or not ON_VERCEL

_PK = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"

SCHEMA = [
    f"""CREATE TABLE IF NOT EXISTS shows (
        id {_PK},
        title TEXT NOT NULL,
        venue TEXT,
        show_date TEXT NOT NULL,
        show_time TEXT,
        notes TEXT,
        created_at TEXT NOT NULL
    )""",
    f"""CREATE TABLE IF NOT EXISTS bookings (
        id {_PK},
        code TEXT NOT NULL UNIQUE,
        show_id INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        city TEXT,
        num_seats INTEGER NOT NULL,
        seats TEXT NOT NULL,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'confirmed',
        created_at TEXT NOT NULL,
        cancelled_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS booked_seats (
        show_id INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
        seat TEXT NOT NULL,
        booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
        PRIMARY KEY (show_id, seat)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_bookings_show ON bookings(show_id)",
    "CREATE INDEX IF NOT EXISTS idx_bookings_created ON bookings(created_at)",
]

_schema_ready = False


def _ensure_schema(conn):
    global _schema_ready
    if _schema_ready:
        return
    cur = conn.cursor()
    try:
        for stmt in SCHEMA:
            cur.execute(stmt)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    _schema_ready = True


def get_db():
    if "db" not in g:
        if IS_PG:
            conn = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=10,
            )
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
        _ensure_schema(conn)
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        try:
            if exc is not None:
                conn.rollback()
        finally:
            conn.close()


def _sql(s):
    return s.replace("?", "%s") if IS_PG else s


def query(sql, params=(), one=False):
    cur = get_db().cursor()
    cur.execute(_sql(sql), tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run a write. If the statement has RETURNING, the first row is returned."""
    cur = get_db().cursor()
    cur.execute(_sql(sql), tuple(params))
    result = None
    if cur.description:
        row = cur.fetchone()
        result = dict(row) if row else None
    cur.close()
    return result


def executemany(sql, seq):
    cur = get_db().cursor()
    cur.executemany(_sql(sql), [tuple(p) for p in seq])
    cur.close()


def commit():
    get_db().commit()


def rollback():
    get_db().rollback()
