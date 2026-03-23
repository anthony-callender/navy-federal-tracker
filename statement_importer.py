"""
Statement Importer - Parse Navy Federal PDF statements into the database.

Handles: EveryDay Checking (7121417948) and Bills Savings (3225103682).
Skips internal transfers, fees, and balance lines.
"""
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import pdfplumber

import database
from categorizer import Categorizer

STATEMENTS_DIR = Path(__file__).parent / "statements_to_import"

# Only import these accounts (skip pure savings transfer noise)
IMPORT_ACCOUNTS = {"7121417948", "3225103682"}

ACCOUNT_NAMES = {
    "7121417948": "Checking",
    "3146585264": "Membership Savings",
    "3208476261": "Savings",
    "3225103682": "Bills Savings",
    "3225840572": "Savings",
    "3227689498": "Savings",
    "3228354886": "Savings",
}

ALL_ACCOUNT_NUMS = set(ACCOUNT_NAMES.keys())

# Lines to skip entirely
SKIP_RE = re.compile(
    r"^(Transfer\s+(From|To)\s+Sha?r?e?s?"   # Transfer From/To Shares (OCR-broken OK)
    r"|Transfer\s+From\s+Che?c?k?i?n?g?"      # Transfer From Checking
    r"|Transfer\s+To\s+Che?c?k?i?n?g?"        # Transfer To Checking
    r"|Intl\s*Transaction\s*Fe?e?"             # Intl Transaction Fee (OCR-broken OK)
    r"|Beginning Balance"
    r"|Ending Balance"
    r"|Average Daily Balance"
    r"|Dividend"
    r"|Items Paid"
    r"|Joint Owner"
    r"|Continued from"
    r"|Your account earned"
    r"|Statement of Account"
    r"|REMITTANCE RECEIVED"
    r"|Page \d+ of \d+)",
    re.IGNORECASE,
)

# ─── Amount parsing ───────────────────────────────────────────────────────────

def parse_amount(s: str) -> Tuple[float, str]:
    """'1,980.00' → (1980.0, 'credit'),  '89.83 -' or '89.83-' → (89.83, 'debit')"""
    s = s.strip()
    if s.endswith("-"):
        return round(float(s.rstrip("- ").replace(",", "")), 2), "debit"
    return round(float(s.replace(",", "")), 2), "credit"

# ─── Date parsing ─────────────────────────────────────────────────────────────

def resolve_date(mm_dd: str, start_year: int, start_month: int) -> str:
    month, day = int(mm_dd[:2]), int(mm_dd[3:])
    # If statement starts in Dec and this date is Jan-Jun, it belongs to next year
    year = start_year + 1 if start_month >= 10 and month <= 6 else start_year
    return f"{year}-{month:02d}-{day:02d}"

def extract_period(text: str) -> Tuple[int, int]:
    """Return (start_month, start_year) from statement header."""
    m = re.search(r"(\d{1,2})/\d{1,2}/(\d{2})\s*[-–]", text)
    if m:
        return int(m.group(1)), 2000 + int(m.group(2))
    return 1, 2026

# ─── Merchant extraction ─────────────────────────────────────────────────────

def extract_merchant(detail: str) -> Tuple[str, Optional[str]]:
    """
    Returns (merchant_name, override_type | None).
    override_type is 'credit' when we can tell it's a deposit.
    """
    d = detail.strip()

    # ACH Payroll / Direct Deposit
    m = re.match(r"Deposit\s*[-–]\s*ACH Paid From\s+(.+?)(\s+\d+\w*)?$", d, re.I)
    if m:
        name = re.sub(r"\s*Payroll\s*\w*", " Payroll", m.group(1), flags=re.I).strip()
        return name[:50], "credit"

    # Generic Deposit (check, FCHV, etc.)
    m = re.match(r"Deposit\s+(?:\d{2}-\d{2}-\d{2}\s+)?(.+)", d, re.I)
    if m:
        return m.group(1).strip()[:50], "credit"

    # POS Debit with "Transaction MM-DD-YY MERCHANT"
    m = re.match(
        r"POS Debit[-\s]+Debit Card\s+\d+\s+Transaction\s+\d{2}-\d{2}-\d{2}\s+(.+)",
        d, re.I
    )
    if m:
        return _clean_pos(m.group(1)), None

    # POS Debit with "MM-DD-YY MERCHANT"
    m = re.match(
        r"POS Debit[-\s]+Debit Card\s+\d+\s+\d{2}-\d{2}-\d{2}\s+(.+)",
        d, re.I
    )
    if m:
        return _clean_pos(m.group(1)), None

    # Zelle debit
    m = re.match(r"Zelle DB\s+(.+)", d, re.I)
    if m:
        return f"Zelle: {m.group(1).strip()[:40]}", None

    # Zelle refund/credit
    m = re.match(r"Zelle Refund\s+(.+)", d, re.I)
    if m:
        return f"Zelle Refund: {m.group(1).strip()[:40]}", "credit"

    # Paid To (bill payments like Affirm)
    m = re.match(r"Paid To\s*[-–]\s*([A-Za-z0-9\.\*\s]+?)(?:\s+Payme|\s+Chk|\s+\d{5,})", d, re.I)
    if m:
        return m.group(1).strip()[:50], None
    m = re.match(r"Paid To\s*[-–]\s*(.+)", d, re.I)
    if m:
        return m.group(1).split()[0].strip()[:50], None

    # Transfer To Loan = loan payment (keep it)
    if re.match(r"Transfer To Loan", d, re.I):
        return "Loan Payment", None

    # Transfer From Checking with a name (incoming from another person)
    m = re.match(r"Transfer From Checking\s*[-–]?\s*(.+)", d, re.I)
    if m:
        return f"Transfer from {m.group(1).strip()[:40]}", "credit"

    return d[:50], None


def _clean_pos(raw: str) -> str:
    """Tidy up a POS merchant string."""
    # Remove trailing numeric store codes: "0754 43090 Dale ..."
    cleaned = re.sub(r"\s+\d{3,}\s+\d{3,}.*$", "", raw)
    # Remove trailing state abbreviation
    cleaned = re.sub(r"\s+[A-Z]{2}$", "", cleaned.strip())
    # Remove phone numbers
    cleaned = re.sub(r"\s+\d{3}-\d{3}-\d{4}.*$", "", cleaned)
    # Remove trailing city+state
    cleaned = re.sub(r"\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+[A-Z]{2}$", "", cleaned)
    # Collapse broken OCR spaces inside words (e.g. "I nc" → "Inc", "D R" → "DR")
    cleaned = re.sub(r"(?<=[A-Za-z])\s+(?=[a-z])", "", cleaned)
    return cleaned.strip()[:50]

# ─── PDF Parsing ─────────────────────────────────────────────────────────────

# A transaction line: starts with MM-DD, ends with amount (and optional balance)
TX_LINE_RE = re.compile(
    r"^(\d{1,2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2}\s*-?)\s+([\d,]+\.\d{2}\s*-?)?\s*$"
)

# Amount-only continuation line (for wrapped transactions)
AMOUNT_ONLY_RE = re.compile(r"^(.+?)\s+([\d,]+\.\d{2}\s*-?)\s+([\d,]+\.\d{2}\s*-?)?\s*$")

# Account number pattern
ACCT_RE = re.compile(r"\b(" + "|".join(ALL_ACCOUNT_NUMS) + r")\b")


def parse_pdf(pdf_path: Path) -> List[Dict]:
    """Parse one PDF statement, return list of transaction dicts."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages_text = [p.extract_text() or "" for p in pdf.pages]

    full_text = "\n".join(pages_text)
    start_month, start_year = extract_period(full_text)
    print(f"  Period: {start_month}/{start_year}")

    # Build a clean list of logical lines (join wrapped continuations)
    raw_lines = full_text.split("\n")
    logical_lines = _join_wrapped_lines(raw_lines)

    transactions = []
    current_account = None
    in_tx_section = False

    for line in logical_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect account section header
        acct_match = ACCT_RE.search(stripped)
        if acct_match and ("Checking" in stripped or "Savings" in stripped or
                           "7121417948" in stripped or "3225103682" in stripped):
            current_account = acct_match.group(1)
            in_tx_section = True
            continue

        if not in_tx_section or current_account not in IMPORT_ACCOUNTS:
            continue

        # Try to parse as transaction line
        tx = _parse_tx_line(stripped, current_account, start_year, start_month, pdf_path.stem)
        if tx:
            transactions.append(tx)

    return transactions


def _join_wrapped_lines(raw: List[str]) -> List[str]:
    """
    Join continuation lines (e.g., 'Wilmington' following a POS line) back
    to their parent transaction line.
    """
    out = []
    for line in raw:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        # A new transaction always starts with MM-DD
        if re.match(r"^\d{1,2}-\d{2}\s", stripped):
            out.append(stripped)
        elif out and out[-1] and not re.match(r"^\d{1,2}-\d{2}\s", out[-1]):
            # Both previous and current are non-date lines — just append as-is
            out.append(stripped)
        elif out and out[-1]:
            # Previous line is a date line; check if current is a pure continuation
            # (no leading date, not a header)
            # Merge only if current line looks like a city/location tail with no amount
            if not re.search(r"[\d,]+\.\d{2}", stripped) and len(stripped) < 40:
                out[-1] = out[-1] + " " + stripped
            else:
                out.append(stripped)
        else:
            out.append(stripped)
    return out


def _parse_tx_line(
    line: str,
    account: str,
    start_year: int,
    start_month: int,
    file_stem: str,
) -> Optional[Dict]:
    m = TX_LINE_RE.match(line)
    if not m:
        return None

    date_str = m.group(1)
    detail = m.group(2).strip()
    amount_str = m.group(3).strip()

    # Skip noise lines
    if SKIP_RE.match(detail):
        return None

    # Skip balance/summary rows
    if detail.lower() in ("date", "transaction detail", "amount($)", "balance($)"):
        return None

    try:
        amount, tx_type = parse_amount(amount_str)
    except ValueError:
        return None

    if amount == 0:
        return None

    date = resolve_date(date_str, start_year, start_month)
    merchant, type_override = extract_merchant(detail)
    if type_override:
        tx_type = type_override

    # Skip Transfer To Loan? No — keep it, it's a real payment
    # But skip internal transfers that slipped through
    if re.match(r"Transfer (From|To) (Shares|Checking|Saving)", detail, re.I):
        return None

    category = Categorizer.categorize(merchant, detail)

    email_id = (
        f"stmt_{file_stem}_{account}_{date}_"
        + re.sub(r"\W+", "_", amount_str)
        + "_"
        + re.sub(r"\W+", "_", detail[:25])
    )

    return {
        "email_id": email_id,
        "date": date,
        "merchant": merchant,
        "description": detail,
        "amount": amount,
        "transaction_type": tx_type,
        "category": category,
        "account": ACCOUNT_NAMES.get(account, "Unknown"),
        "account_number": account,
    }

# ─── Main ─────────────────────────────────────────────────────────────────────

def import_all():
    database.init_db()
    pdfs = sorted(STATEMENTS_DIR.glob("*.pdf"))
    if not pdfs:
        print("No PDF files found in statements_to_import/")
        return

    total_new = 0
    for pdf_path in pdfs:
        print(f"\nParsing: {pdf_path.name}")
        txs = parse_pdf(pdf_path)
        new = 0
        for tx in txs:
            if database.save_transaction(tx):
                new += 1
                sign = "+" if tx["transaction_type"] == "credit" else "-"
                print(f"  {tx['date']}  {sign}${tx['amount']:<9.2f}  {tx['merchant']}")
        print(f"  → {new} new / {len(txs)} parsed")
        total_new += new

    print(f"\nDone. {total_new} total transactions imported.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import_all()
