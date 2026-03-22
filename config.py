"""
Configuration for Navy Federal Transaction Tracker

SETUP:
1. Create Gmail App Password (see README)
2. Fill in your credentials below
3. Run: python run_sync.py
"""

import os
from pathlib import Path

# Load .env file when running locally (no-op in production)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# GMAIL CREDENTIALS
# =============================================================================
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "tonycallender001@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "glua skrj tqqg oxmp")

# =============================================================================
# NAVY FEDERAL SETTINGS
# =============================================================================
# Email sender to look for (Navy Federal's alert email)
NFCU_SENDER = "notice@email.navyfederal.org"

# Your accounts (for reference/filtering)
ACCOUNTS = {
    "7121417948": "Checking",
    "3146585264": "Membership Savings",
    "3208476261": "Savings",
    "3225103682": "Bills Savings",
    "3225840572": "Savings",
    "3228354886": "Savings",
}

# =============================================================================
# FILE PATHS
# =============================================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRANSACTIONS_FILE = DATA_DIR / "transactions.xlsx"

# =============================================================================
# CATEGORY MAPPING
# =============================================================================
# Keywords to auto-categorize transactions
# Add your own patterns here!
CATEGORY_RULES = {
    "Food & Dining": [
        "rappi",
        "uber eats",
        "doordash",
        "grubhub",
        "restaurant",
        "mcdonald",
        "chick-fil-a",
        "subway",
        "starbucks",
        "cafe",
        "coffee",
        "pizza",
        "crepes",
        "waffles",
        "burger",
        "taco",
        "sushi",
        "bakery",
        "pastry",
        "smoothi",
        "juice",
        "bar",
        "grill",
        "kitchen",
        "diner",
        "bistro",
        "food",
        "eat",
        "comida",
        "freshens",
        "carbones",
        "parrill",
    ],
    "Groceries": [
        "giant",
        "walmart",
        "target",
        "costco",
        "safeway",
        "kroger",
        "aldi",
        "trader joe",
        "whole foods",
        "carulla",
        "jumbo",
        "tienda d1",
        "oxxo",
        "minimarket",
        "supermercado",
        "grocery",
        "market",
    ],
    "Transportation": [
        "uber",
        "lyft",
        "taxi",
        "gas",
        "shell",
        "exxon",
        "chevron",
        "bp",
        "spirit",
        "airline",
        "delta",
        "united",
        "american air",
        "flight",
        "metro",
        "transit",
        "parking",
        "toll",
    ],
    "Shopping": [
        "amazon",
        "ebay",
        "walmart",
        "target",
        "best buy",
        "apple store",
        "farmatodo",
        "farmacia",
        "pharmacy",
        "cvs",
        "walgreens",
        "dollarcity",
        "dollar",
        "homecenter",
        "home depot",
        "lowes",
        "ikea",
        "libreria",
    ],
    "Subscriptions": [
        "netflix",
        "spotify",
        "hulu",
        "disney",
        "hbo",
        "apple music",
        "youtube",
        "google one",
        "microsoft",
        "adobe",
        "dropbox",
        "amazon prime",
        "skool",
        "cursor",
        "claude",
        "openai",
        "chatgpt",
        "freedom.to",
        "godaddy",
        "domain",
        "hosting",
        "capcut",
    ],
    "Bills & Utilities": [
        "comcast",
        "xfinity",
        "verizon",
        "at&t",
        "t-mobile",
        "mint mobile",
        "electric",
        "water",
        "gas bill",
        "internet",
        "cable",
        "utility",
        "dominion",
        "pepco",
        "northern virginia",
        "rent",
        "domuso",
        "lease",
    ],
    "Money Transfer": [
        "zelle",
        "venmo",
        "paypal",
        "cash app",
        "worldremit",
        "remit",
        "wire",
        "transfer",
        "western union",
        "moneygram",
    ],
    "Entertainment": [
        "movie",
        "cinema",
        "theater",
        "theatre",
        "royal films",
        "amc",
        "regal",
        "concert",
        "ticket",
        "event",
        "game",
        "xbox",
        "playstation",
        "nintendo",
        "steam",
    ],
    "Health": [
        "doctor",
        "hospital",
        "clinic",
        "medical",
        "health",
        "dental",
        "pharmacy",
        "medicine",
        "gym",
        "fitness",
        "yoga",
    ],
    "Income": [
        "payroll",
        "direct deposit",
        "salary",
        "wage",
        "income",
        "refund",
        "cashback",
        "dividend",
        "interest",
    ],
}

# Transactions to IGNORE (internal transfers)
IGNORE_PATTERNS = [
    "transfer from share",
    "transfer to share",
    "transfer from check",
    "transfer to check",
    "transfer from saving",
    "transfer to saving",
]

# =============================================================================
# SYNC SETTINGS
# =============================================================================
# How many days back to look for emails on first run
INITIAL_DAYS_BACK = 30

# How often to check for new emails (in minutes) when running continuous
CHECK_INTERVAL_MINUTES = 5
