# Navy Federal Transaction Tracker 🏦

Automatically sync your Navy Federal Credit Union transactions to a local Excel file by parsing email alerts.

## How It Works

```
Navy Federal Transaction → Email Alert → Gmail → This Script → Excel File
```

When you make a purchase, deposit, or withdrawal, Navy Federal sends you an email alert. This script:
1. Connects to your Gmail account
2. Finds Navy Federal alert emails
3. Parses transaction details (amount, merchant, date)
4. Auto-categorizes each transaction
5. Saves to an Excel file (avoiding duplicates)

## Setup Instructions

### Step 1: Enable Navy Federal Alerts

1. Log into [Navy Federal Online Banking](https://www.navyfederal.org)
2. Go to **Settings** → **Alerts & Notifications**
3. Enable alerts for ALL your accounts:
   - ✅ Debit Card Transactions
   - ✅ Deposits/Credits
   - ✅ Withdrawals/Debits
   - ✅ ACH Transactions
4. Set the threshold to **$0.01** (minimum) to capture everything
5. Set delivery method to **Email** (your Gmail address)

### Step 2: Create Gmail App Password

Google requires an "App Password" for third-party apps (not your regular password).

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Click **Select app** → Choose **Mail**
5. Click **Select device** → Choose **Windows** (or your OS)
6. Click **Generate**
7. Copy the 16-character password (looks like: `xxxx xxxx xxxx xxxx`)

### Step 3: Configure the Script

1. Open `config.py` in a text editor
2. Update these lines:

```python
GMAIL_ADDRESS = "your_actual_email@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # The app password from Step 2
```

3. Update your Navy Federal account numbers if needed:

```python
ACCOUNTS = {
    "7121417948": "Checking",
    "3146585264": "Membership Savings",
    # ... add your accounts
}
```

### Step 4: Install Dependencies

```bash
cd navy_federal_tracker
pip install -r requirements.txt
```

### Step 5: Test Connection

```bash
python run_sync.py --test
```

If successful, you'll see:
```
✅ Connected to Gmail as your_email@gmail.com
📧 Found X Navy Federal emails in the last 7 days
```

### Step 6: Run Your First Sync

```bash
# Sync last 30 days
python run_sync.py --days 30
```

## Usage

### One-Time Sync
```bash
python run_sync.py
```

### Sync Specific Number of Days
```bash
python run_sync.py --days 7     # Last 7 days
python run_sync.py --days 90    # Last 90 days
```

### Watch Mode (Continuous)
```bash
python run_sync.py --watch
```
This checks for new emails every 5 minutes (configurable in `config.py`).

### Test Connection
```bash
python run_sync.py --test
```

## Output

Transactions are saved to `data/transactions.xlsx` with two sheets:

### Transactions Sheet
| Date | Time | Description | Merchant | Amount | Type | Category | Account |
|------|------|-------------|----------|--------|------|----------|---------|
| 2026-03-15 | 14:30:00 | Card purchase at UBER | UBER TRIP | -$25.00 | Debit | Transportation | Checking |

### Summary Sheet
- Total Income
- Total Expenses
- Net
- Breakdown by Category

## Customizing Categories

Edit `config.py` to add your own category rules:

```python
CATEGORY_RULES = {
    "Food & Dining": [
        "rappi", "uber eats", "restaurant", "cafe",
        # Add your own keywords here
    ],
    "My Custom Category": [
        "keyword1", "keyword2",
    ],
}
```

## Ignoring Internal Transfers

The script automatically ignores internal transfers between your accounts. If you see transfers being tracked that shouldn't be, add patterns to:

```python
IGNORE_PATTERNS = [
    "transfer from share",
    "transfer to share",
    # Add more patterns here
]
```

## Troubleshooting

### "Gmail login failed"
- Make sure you're using an **App Password**, not your regular password
- Check that 2-Step Verification is enabled
- Verify the email address in `config.py`

### "No Navy Federal emails found"
- Check that alerts are enabled in Navy Federal
- Make sure alerts go to the Gmail address in `config.py`
- Try increasing `--days` parameter
- Check your Gmail spam folder

### "No valid transactions found"
- The emails might all be internal transfers (which are ignored)
- Check `config.py` IGNORE_PATTERNS if too much is being filtered

### Duplicate transactions
- The script tracks email IDs to prevent duplicates
- If you see duplicates, the email ID column might have issues

## Security Notes

⚠️ **Keep your credentials safe!**

- Never share `config.py` with your passwords
- Add `config.py` to `.gitignore` if using version control
- The App Password only grants access to Gmail, not your full Google account
- You can revoke the App Password anytime at [myaccount.google.com](https://myaccount.google.com/apppasswords)

## File Structure

```
navy_federal_tracker/
├── config.py           # Your settings (edit this!)
├── gmail_client.py     # Gmail connection
├── email_parser.py     # Parse Navy Federal emails
├── categorizer.py      # Auto-categorize transactions
├── excel_manager.py    # Excel file handling
├── run_sync.py         # Main script (run this!)
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── data/
    └── transactions.xlsx   # Your transaction database
```

## License

Personal use. Do whatever you want with it! 🎉
