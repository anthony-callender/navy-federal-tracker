"""
Database - SQLite operations for Navy Federal Budget Tracker
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import config


DB_PATH = config.DATA_DIR / "budget.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create tables if they don't exist."""
    config.DATA_DIR.mkdir(exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT UNIQUE,
                date TEXT NOT NULL,
                merchant TEXT,
                description TEXT,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                category TEXT,
                account TEXT,
                account_number TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS budget_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS monthly_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                total_income REAL DEFAULT 0,
                total_spending REAL DEFAULT 0,
                total_fixed REAL DEFAULT 0,
                remaining REAL DEFAULT 0,
                computed_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
        """)
        _seed_default_config(conn)
        conn.commit()
        print("✅ Database initialized")
    finally:
        conn.close()


def _seed_default_config(conn: sqlite3.Connection):
    """Insert default budget config values if not already present."""
    defaults = {
        "monthly_income": "4800.00",
        "fixed_bills": json.dumps({
            "Rent": 1580.00,
            "Utilities": 120.00,
            "Capital One": 450.00,
        }),
        "alert_threshold": "200.00",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO budget_config (key, value) VALUES (?, ?)",
            (key, value),
        )


# ---------------------------------------------------------------------------
# Transaction helpers
# ---------------------------------------------------------------------------

def save_transaction(tx) -> bool:
    """
    Save a Transaction object to the DB.
    Returns True if inserted, False if already exists (duplicate email_id).
    """
    if hasattr(tx, "email_id"):
        email_id = tx.email_id
        date = tx.date.strftime("%Y-%m-%d") if hasattr(tx.date, "strftime") else str(tx.date)
        merchant = tx.merchant
        description = tx.description
        amount = abs(tx.amount)
        transaction_type = tx.transaction_type
        category = tx.category
        account = tx.account
        account_number = tx.account_number
    else:
        email_id = tx.get("email_id", "")
        date = tx.get("date", "")
        merchant = tx.get("merchant", "")
        description = tx.get("description", "")
        amount = abs(tx.get("amount", 0))
        transaction_type = tx.get("transaction_type", "debit")
        category = tx.get("category", "Other")
        account = tx.get("account", "")
        account_number = tx.get("account_number", "")

    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO transactions
               (email_id, date, merchant, description, amount, transaction_type,
                category, account, account_number)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (email_id, date, merchant, description, amount, transaction_type,
             category, account, account_number),
        )
        inserted = conn.total_changes > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def email_already_processed(email_id: str) -> bool:
    """Return True if this email_id is already in the DB."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM transactions WHERE email_id = ?", (email_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_transactions(month: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """
    Return recent debit transactions.
    month: 'YYYY-MM' filter (optional). limit: max rows.
    """
    conn = get_connection()
    try:
        if month:
            rows = conn.execute(
                """SELECT * FROM transactions
                   WHERE date LIKE ? AND transaction_type = 'debit'
                   ORDER BY date DESC LIMIT ?""",
                (f"{month}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM transactions
                   WHERE transaction_type = 'debit'
                   ORDER BY date DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_spending_by_category(month: str) -> Dict[str, float]:
    """Return {category: total_spent} for debit transactions in the given month."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE date LIKE ? AND transaction_type = 'debit'
               GROUP BY category
               ORDER BY total DESC""",
            (f"{month}%",),
        ).fetchall()
        return {r["category"]: round(r["total"], 2) for r in rows}
    finally:
        conn.close()


def get_income(month: str) -> float:
    """Return total credit/income for the given month."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE date LIKE ? AND transaction_type = 'credit'""",
            (f"{month}%",),
        ).fetchone()
        return round(row["total"], 2) if row else 0.0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_config(key: str) -> Optional[str]:
    """Retrieve a config value by key."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM budget_config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_config(key: str, value: str):
    """Upsert a config key-value pair."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO budget_config (key, value, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()
