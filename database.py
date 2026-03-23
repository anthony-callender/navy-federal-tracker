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

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL,
                is_default INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS monthly_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                expected_amount REAL DEFAULT 0,
                category TEXT,
                keywords TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transaction_monthly_link (
                transaction_id INTEGER PRIMARY KEY,
                monthly_expense_id INTEGER,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (monthly_expense_id) REFERENCES monthly_expenses(id)
            );

            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount_owed REAL NOT NULL,
                creditor TEXT,
                due_date TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
        """)
        _seed_default_config(conn)
        _seed_categories(conn)
        _migrate_monthly_expenses(conn)
        _seed_monthly_expenses(conn)
        conn.commit()
        print("✅ Database initialized")
    finally:
        conn.close()


def _seed_default_config(conn: sqlite3.Connection):
    """Insert default budget config values if not already present."""
    defaults = {
        "monthly_income": "4800.00",
        "alert_threshold": "200.00",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO budget_config (key, value) VALUES (?, ?)",
            (key, value),
        )


def _migrate_monthly_expenses(conn: sqlite3.Connection):
    """Add keywords column if it doesn't exist yet (migration)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(monthly_expenses)").fetchall()]
    if "keywords" not in cols:
        conn.execute("ALTER TABLE monthly_expenses ADD COLUMN keywords TEXT DEFAULT ''")


def _seed_categories(conn: sqlite3.Connection):
    """Insert default categories if not already present."""
    defaults = [
        ("Income", "#22c55e"),
        ("Food & Dining", "#f59e0b"),
        ("Transportation", "#3b82f6"),
        ("Shopping", "#a855f7"),
        ("Groceries", "#14b8a6"),
        ("Bills & Utilities", "#ef4444"),
        ("Entertainment", "#ec4899"),
        ("Health", "#06b6d4"),
        ("Subscriptions", "#8b5cf6"),
        ("Money Transfer", "#6366f1"),
        ("ATM/Cash", "#78716c"),
        ("Other", "#9ca3af"),
    ]
    for name, color in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, color, is_default) VALUES (?, ?, 1)",
            (name, color),
        )


def _seed_monthly_expenses(conn: sqlite3.Connection):
    """Insert default monthly expenses if not already present."""
    defaults = [
        ("Rent", 1580.00, "Bills & Utilities",
         "domuso"),
        ("Utilities", 120.00, "Bills & Utilities",
         "northern virgini,comcast,xfinity"),
        ("Capital One", 450.00, "Bills & Utilities",
         "capital one"),
        ("Phone", 70.00, "Bills & Utilities",
         "mint mobile"),
        ("Loan Payment", 170.00, "Bills & Utilities",
         "loan payment"),
        ("Subscriptions", 100.00, "Subscriptions",
         "skool,cursor,netflix,spotify,disney,claude,anthropic,amazon prime,"
         "google *youtube,google *capcut,godaddy,freedom.to,microsoft"),
    ]
    for name, amount, category, keywords in defaults:
        conn.execute(
            """INSERT OR IGNORE INTO monthly_expenses (name, expected_amount, category, keywords)
               VALUES (?, ?, ?, ?)""",
            (name, amount, category, keywords),
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


# ---------------------------------------------------------------------------
# Transaction extended helpers
# ---------------------------------------------------------------------------

def get_transactions_filtered(
    month: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict]:
    """Return transactions with optional filters, joined with monthly_expense name."""
    wheres = []
    params: list = []

    if month:
        wheres.append("t.date LIKE ?")
        params.append(f"{month}%")
    if category:
        wheres.append("t.category = ?")
        params.append(category)

    where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT t.*, me.name as monthly_expense_name, me.id as monthly_expense_id_joined
                FROM transactions t
                LEFT JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
                LEFT JOIN monthly_expenses me ON tml.monthly_expense_id = me.id
                {where_sql}
                ORDER BY t.date DESC, t.id DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_transaction(tx_id: int, fields: Dict) -> bool:
    """Update category and/or monthly_expense_id for a transaction."""
    conn = get_connection()
    try:
        if "category" in fields:
            conn.execute(
                "UPDATE transactions SET category = ? WHERE id = ?",
                (fields["category"], tx_id),
            )

        if "monthly_expense_id" in fields:
            me_id = fields["monthly_expense_id"]
            if me_id is None:
                conn.execute(
                    "DELETE FROM transaction_monthly_link WHERE transaction_id = ?",
                    (tx_id,),
                )
            else:
                conn.execute(
                    """INSERT OR REPLACE INTO transaction_monthly_link
                       (transaction_id, monthly_expense_id) VALUES (?, ?)""",
                    (tx_id, me_id),
                )

        conn.commit()
        return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def get_categories() -> List[Dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_category(name: str, color: str) -> Dict:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO categories (name, color, is_default) VALUES (?, ?, 0)",
            (name, color),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_category(cat_id: int, fields: Dict) -> bool:
    conn = get_connection()
    try:
        if "name" in fields:
            conn.execute("UPDATE categories SET name = ? WHERE id = ?", (fields["name"], cat_id))
        if "color" in fields:
            conn.execute("UPDATE categories SET color = ? WHERE id = ?", (fields["color"], cat_id))
        conn.commit()
        return True
    finally:
        conn.close()


def delete_category(cat_id: int) -> bool:
    """Only delete non-default categories."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT is_default FROM categories WHERE id = ?", (cat_id,)).fetchone()
        if not row or row["is_default"]:
            return False
        conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Monthly Expenses
# ---------------------------------------------------------------------------

def get_monthly_expenses() -> List[Dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM monthly_expenses ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_monthly_expense(name: str, expected_amount: float, category: str,
                           keywords: str = "") -> Dict:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO monthly_expenses (name, expected_amount, category, keywords)
               VALUES (?, ?, ?, ?)""",
            (name, expected_amount, category, keywords),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM monthly_expenses WHERE name = ?", (name,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_monthly_expense(me_id: int, fields: Dict) -> bool:
    conn = get_connection()
    try:
        for col in ("name", "expected_amount", "category", "keywords", "is_active"):
            if col in fields:
                conn.execute(
                    f"UPDATE monthly_expenses SET {col} = ? WHERE id = ?",
                    (fields[col], me_id),
                )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_monthly_expense(me_id: int) -> bool:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM monthly_expenses WHERE id = ?", (me_id,))
        conn.execute(
            "DELETE FROM transaction_monthly_link WHERE monthly_expense_id = ?", (me_id,)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def classify_transactions(month: str) -> Dict:
    """
    Match transactions for a month against monthly expense keywords.
    Links matches via transaction_monthly_link.
    Returns { matched: int, total_checked: int }.
    """
    conn = get_connection()
    try:
        # Get active monthly expenses with keywords
        expenses = conn.execute(
            "SELECT id, name, keywords FROM monthly_expenses WHERE is_active = 1"
        ).fetchall()

        # Get all debit transactions for the month that aren't already linked
        txs = conn.execute(
            """SELECT t.id, t.merchant, t.description
               FROM transactions t
               LEFT JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
               WHERE t.date LIKE ? AND t.transaction_type = 'debit'
               AND tml.transaction_id IS NULL""",
            (f"{month}%",),
        ).fetchall()

        matched = 0
        for tx in txs:
            search_text = f"{tx['merchant'] or ''} {tx['description'] or ''}".lower()
            for exp in expenses:
                kw_str = exp["keywords"] or ""
                keywords = [k.strip().lower() for k in kw_str.split(",") if k.strip()]
                if any(kw in search_text for kw in keywords):
                    conn.execute(
                        """INSERT OR REPLACE INTO transaction_monthly_link
                           (transaction_id, monthly_expense_id) VALUES (?, ?)""",
                        (tx["id"], exp["id"]),
                    )
                    matched += 1
                    break  # first match wins

        conn.commit()
        return {"matched": matched, "total_checked": len(txs)}
    finally:
        conn.close()


def clear_classifications(month: str) -> int:
    """Remove all monthly expense links for transactions in the given month."""
    conn = get_connection()
    try:
        result = conn.execute(
            """DELETE FROM transaction_monthly_link
               WHERE transaction_id IN (
                   SELECT id FROM transactions WHERE date LIKE ?
               )""",
            (f"{month}%",),
        )
        conn.commit()
        return result.rowcount
    finally:
        conn.close()


def get_expected_fixed() -> float:
    """Sum of expected_amount from all active monthly expenses."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(expected_amount), 0) as total FROM monthly_expenses WHERE is_active = 1"
        ).fetchone()
        return round(row["total"], 2)
    finally:
        conn.close()


def get_fixed_spending(month: str) -> float:
    """Sum of debit transactions linked to a monthly expense for the month."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(t.amount), 0) as total
               FROM transactions t
               JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
               WHERE t.date LIKE ? AND t.transaction_type = 'debit'""",
            (f"{month}%",),
        ).fetchone()
        return round(row["total"], 2)
    finally:
        conn.close()


def get_variable_spending(month: str) -> float:
    """Sum of debit transactions NOT linked to any monthly expense."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(t.amount), 0) as total
               FROM transactions t
               LEFT JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
               WHERE t.date LIKE ? AND t.transaction_type = 'debit'
               AND tml.transaction_id IS NULL""",
            (f"{month}%",),
        ).fetchone()
        return round(row["total"], 2)
    finally:
        conn.close()


def get_variable_by_category(month: str) -> Dict[str, float]:
    """Variable spending (unlinked) grouped by category."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT t.category, SUM(t.amount) as total
               FROM transactions t
               LEFT JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
               WHERE t.date LIKE ? AND t.transaction_type = 'debit'
               AND tml.transaction_id IS NULL
               GROUP BY t.category
               ORDER BY total DESC""",
            (f"{month}%",),
        ).fetchall()
        return {r["category"]: round(r["total"], 2) for r in rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Debts
# ---------------------------------------------------------------------------

def get_debts(include_inactive: bool = False) -> List[Dict]:
    conn = get_connection()
    try:
        if include_inactive:
            rows = conn.execute("SELECT * FROM debts ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM debts WHERE is_active = 1 ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_debt(name: str, amount_owed: float, creditor: str = "",
                due_date: str = "", notes: str = "") -> Dict:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO debts (name, amount_owed, creditor, due_date, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (name, amount_owed, creditor, due_date, notes),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM debts WHERE id = last_insert_rowid()"
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_debt(debt_id: int, fields: Dict) -> bool:
    conn = get_connection()
    try:
        for col in ("name", "amount_owed", "creditor", "due_date", "notes", "is_active"):
            if col in fields:
                conn.execute(
                    f"UPDATE debts SET {col} = ? WHERE id = ?",
                    (fields[col], debt_id),
                )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_debt(debt_id: int) -> bool:
    """Soft delete — sets is_active=0."""
    conn = get_connection()
    try:
        conn.execute("UPDATE debts SET is_active = 0 WHERE id = ?", (debt_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Dashboard aggregations
# ---------------------------------------------------------------------------

def get_dashboard_totals(month: str) -> Dict:
    """Total monthly expenses (linked), total variable, grand total for a month."""
    conn = get_connection()
    try:
        # Total spending on transactions linked to monthly_expenses
        row = conn.execute(
            """SELECT COALESCE(SUM(t.amount), 0) as total
               FROM transactions t
               JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
               WHERE t.date LIKE ? AND t.transaction_type = 'debit'""",
            (f"{month}%",),
        ).fetchone()
        total_monthly = round(row["total"], 2)

        # Total variable (not linked to monthly expenses)
        row2 = conn.execute(
            """SELECT COALESCE(SUM(t.amount), 0) as total
               FROM transactions t
               LEFT JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
               WHERE t.date LIKE ? AND t.transaction_type = 'debit'
               AND tml.transaction_id IS NULL""",
            (f"{month}%",),
        ).fetchone()
        total_variable = round(row2["total"], 2)

        return {
            "month": month,
            "total_monthly": total_monthly,
            "total_variable": total_variable,
            "grand_total": round(total_monthly + total_variable, 2),
        }
    finally:
        conn.close()


def get_variable_by_category_pivot(months: List[str]) -> Dict:
    """Variable spending by category for each month."""
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(months))
        month_patterns = [f"{m}%" for m in months]

        rows = conn.execute(
            f"""SELECT substr(t.date, 1, 7) as month, t.category,
                       COALESCE(SUM(t.amount), 0) as total
                FROM transactions t
                LEFT JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
                WHERE substr(t.date, 1, 7) IN ({placeholders})
                AND t.transaction_type = 'debit'
                AND tml.transaction_id IS NULL
                GROUP BY month, t.category""",
            months,
        ).fetchall()

        result: Dict = {}
        for r in rows:
            cat = r["category"] or "Other"
            m = r["month"]
            if cat not in result:
                result[cat] = {}
            result[cat][m] = round(r["total"], 2)
        return result
    finally:
        conn.close()


def get_monthly_by_expense_pivot(months: List[str]) -> Dict:
    """Monthly expense amounts per expense name per month."""
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(months))

        rows = conn.execute(
            f"""SELECT substr(t.date, 1, 7) as month, me.name,
                       COALESCE(SUM(t.amount), 0) as total
                FROM transactions t
                JOIN transaction_monthly_link tml ON t.id = tml.transaction_id
                JOIN monthly_expenses me ON tml.monthly_expense_id = me.id
                WHERE substr(t.date, 1, 7) IN ({placeholders})
                AND t.transaction_type = 'debit'
                GROUP BY month, me.name""",
            months,
        ).fetchall()

        result: Dict = {}
        for r in rows:
            name = r["name"]
            m = r["month"]
            if name not in result:
                result[name] = {}
            result[name][m] = round(r["total"], 2)
        return result
    finally:
        conn.close()


def get_chart_data(months: List[str]) -> List[Dict]:
    """Income vs total spending per month for chart."""
    conn = get_connection()
    try:
        result = []
        for month in months:
            income_row = conn.execute(
                """SELECT COALESCE(SUM(amount), 0) as total FROM transactions
                   WHERE date LIKE ? AND transaction_type = 'credit'""",
                (f"{month}%",),
            ).fetchone()
            spending_row = conn.execute(
                """SELECT COALESCE(SUM(amount), 0) as total FROM transactions
                   WHERE date LIKE ? AND transaction_type = 'debit'""",
                (f"{month}%",),
            ).fetchone()
            result.append({
                "month": month,
                "income": round(income_row["total"], 2),
                "spending": round(spending_row["total"], 2),
            })
        return result
    finally:
        conn.close()
