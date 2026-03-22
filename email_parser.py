"""
Email Parser - Extracts transaction data from Navy Federal alert emails

Navy Federal sends various alert types:
- Debit card transactions
- ACH deposits/withdrawals  
- ATM transactions
- Transfers (we'll ignore internal ones)
"""

import re
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
import config


@dataclass
class Transaction:
    """Represents a parsed transaction."""
    date: datetime
    description: str
    amount: float
    transaction_type: str  # "credit" or "debit"
    account: str
    account_number: str
    merchant: str
    category: str
    email_id: str
    raw_subject: str
    is_internal: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Excel export."""
        return {
            "Date": self.date.strftime("%Y-%m-%d"),
            "Time": self.date.strftime("%H:%M:%S"),
            "Description": self.description,
            "Merchant": self.merchant,
            "Amount": self.amount if self.transaction_type == "credit" else -self.amount,
            "Type": self.transaction_type.capitalize(),
            "Category": self.category,
            "Account": self.account,
            "Account Number": self.account_number[-4:] if self.account_number else "",
            "Email ID": self.email_id,
        }


class NFCUEmailParser:
    """Parses Navy Federal Credit Union alert emails."""
    
    # Regex patterns for extracting transaction data
    PATTERNS = {
        # Amount patterns
        "amount": [
            r"\$([0-9,]+\.?\d*)",
            r"amount[:\s]+\$?([0-9,]+\.?\d*)",
            r"([0-9,]+\.?\d*)\s*(?:USD|dollars?)",
        ],

        # Account patterns
        "account": [
            r"account\s*(?:ending\s*in\s*|#?\s*)(\d{4,})",
            r"(?:checking|savings)\s*(?:account\s*)?[#-]?\s*(\d{4,})",
            r"account\s*(\d{4,})",
        ],

        # Merchant patterns — most specific first.
        # Navy Federal subjects look like:
        #   "… $25.00 debit card transaction at UBER TRIP on 03/15/2026"
        #   "… $25.00 debit card purchase at AMAZON.COM"
        # We want what comes after "at" / "from" / "to" but NOT account phrases.
        "merchant": [
            # After "transaction at" or "purchase at" up to " on <date>", period, or end
            r"(?:transaction|purchase)\s+at\s+([A-Za-z0-9][A-Za-z0-9\s\*\#\-\.\&\']+?)(?:\s+on\s+\d|\.$|\s*$)",
            # ACH / direct-deposit: "deposit from MERCHANT"
            r"(?:deposit|payment)\s+from\s+([A-Za-z0-9][A-Za-z0-9\s\*\#\-\.\&\']+?)(?:\s+on\s+\d|\.$|\s*$)",
            # Explicit merchant label
            r"merchant[:\s]+([A-Za-z0-9][A-Za-z0-9\s\*\#\-\.\&\']+)",
            # Generic "at MERCHANT" but reject if merchant starts with "your"
            r"(?<!\w)at\s+(?!your\b)([A-Z][A-Z0-9\s\*\#\-\.]{2,40})(?:\s+on\s+\d|\.$|\s*$)",
        ],

        # Date patterns
        "date": [
            r"(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(\d{1,2}-\d{1,2}-\d{2,4})",
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
        ],
    }
    
    # Keywords to identify transaction types
    CREDIT_KEYWORDS = [
        "deposit", "credit", "received", "refund", "payment received",
        "direct deposit", "payroll", "ach credit", "incoming"
    ]
    
    DEBIT_KEYWORDS = [
        "purchase", "debit", "withdrawal", "payment", "charge",
        "transaction", "pos", "atm", "ach debit", "outgoing"
    ]
    
    def parse_email(self, email_data: dict) -> Optional[Transaction]:
        """
        Parse a Navy Federal alert email into a Transaction.
        
        Args:
            email_data: Dictionary with 'subject', 'body', 'date', 'id'
            
        Returns:
            Transaction object or None if not a valid transaction
        """
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "")
        email_date = email_data.get("date", datetime.now())
        email_id = email_data.get("id", "")
        
        # Combine subject and body for parsing
        full_text = f"{subject}\n{body}"
        full_text_lower = full_text.lower()
        
        # Check if this is a transaction alert (not just informational)
        if not self._is_transaction_alert(subject, body):
            return None
        
        # Check if this is an internal transfer (should be ignored)
        if self._is_internal_transfer(full_text_lower):
            print(f"   ⏭️ Skipping internal transfer: {subject[:50]}...")
            return None
        
        # Extract transaction data
        amount = self._extract_amount(full_text)
        if amount is None or amount == 0:
            return None

        account_number = self._extract_account(full_text)
        merchant = self._extract_merchant(full_text, subject)
        transaction_type = self._determine_type(subject, body)

        # Get account name from config
        account_name = config.ACCOUNTS.get(account_number, "Unknown")

        # Strip URLs before categorizing so base64 links don't false-match keywords
        clean_body = re.sub(r'https?://\S+', '', body)

        # Auto-categorize
        from categorizer import Categorizer
        category = Categorizer.categorize(merchant, subject + " " + clean_body)
        
        return Transaction(
            date=email_date,
            description=email_data.get("subject", ""),
            amount=amount,
            transaction_type=transaction_type,
            account=account_name,
            account_number=account_number or "",
            merchant=merchant,
            category=category,
            email_id=email_id,
            raw_subject=email_data.get("subject", ""),
            is_internal=False
        )
    
    def _is_transaction_alert(self, subject: str, body: str) -> bool:
        """Check if email is a transaction alert vs informational."""
        transaction_indicators = [
            "transaction", "purchase", "deposit", "withdrawal",
            "payment", "debit", "credit", "charge", "atm",
            "$"  # Most transaction alerts have a dollar amount
        ]
        
        text = (subject + " " + body).lower()
        return any(indicator in text for indicator in transaction_indicators)
    
    def _is_internal_transfer(self, text: str) -> bool:
        """Check if this is an internal transfer between accounts."""
        for pattern in config.IGNORE_PATTERNS:
            if pattern.lower() in text:
                return True
        return False
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract dollar amount from text."""
        for pattern in self.PATTERNS["amount"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_account(self, text: str) -> Optional[str]:
        """Extract account number from text."""
        for pattern in self.PATTERNS["account"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account = match.group(1)
                # Try to match with known accounts
                for full_account in config.ACCOUNTS.keys():
                    if account in full_account or full_account.endswith(account):
                        return full_account
                return account
        return None
    
    def _extract_merchant(self, text: str, subject: str) -> str:
        """Extract merchant name from email text."""
        subject_lower = subject.lower()

        # Handle Navy Federal notification email types that have no merchant
        if "deposit notification" in subject_lower:
            # Check body for payroll/direct deposit indicators
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["payroll", "direct deposit", "ach credit"]):
                return "Direct Deposit"
            return "Check Deposit"

        if "withdrawal notification" in subject_lower:
            text_lower = text.lower()
            if "zelle" in text_lower:
                return "Zelle Transfer"
            if "ach" in text_lower:
                return "ACH Withdrawal"
            return "Withdrawal"

        # Strip URLs from text before regex matching
        clean_text = re.sub(r'https?://\S+', '', text)

        # Try specific patterns first on the subject, then cleaned body
        for source in [subject, clean_text]:
            for pattern in self.PATTERNS["merchant"]:
                match = re.search(pattern, source, re.IGNORECASE)
                if match:
                    merchant = match.group(1).strip()
                    merchant = re.sub(r'\s+', ' ', merchant)
                    merchant = merchant.strip('.-* ')
                    if len(merchant) > 3 and "account" not in merchant.lower():
                        return merchant[:50]

        # Last resort: strip known prefixes from subject
        cleaned = subject
        for prefix in ["navy federal alert:", "transaction alert:", "alert:"]:
            cleaned = re.sub(re.escape(prefix), "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()[:50] or "Unknown"
    
    def _determine_type(self, subject: str, body: str) -> str:
        """Determine if transaction is credit or debit."""
        text = (subject + " " + body).lower()
        
        # Check for credit indicators
        for keyword in self.CREDIT_KEYWORDS:
            if keyword in text:
                return "credit"
        
        # Default to debit for purchases
        return "debit"
    
    def parse_multiple(self, emails: List[dict]) -> List[Transaction]:
        """Parse multiple emails and return valid transactions."""
        transactions = []
        
        for email_data in emails:
            try:
                transaction = self.parse_email(email_data)
                if transaction:
                    transactions.append(transaction)
                    print(f"   ✅ Parsed: {transaction.merchant} - ${transaction.amount:.2f}")
            except Exception as e:
                print(f"   ⚠️ Error parsing email: {e}")
        
        return transactions


# Quick test
if __name__ == "__main__":
    # Test with sample email
    test_email = {
        "subject": "Navy Federal Alert: $25.00 debit card transaction at UBER TRIP",
        "body": "A $25.00 debit card transaction was made on your account ending in 7948 at UBER TRIP on 03/15/2026.",
        "date": datetime.now(),
        "id": "test123"
    }
    
    parser = NFCUEmailParser()
    tx = parser.parse_email(test_email)
    if tx:
        print(f"Parsed: {tx.to_dict()}")
