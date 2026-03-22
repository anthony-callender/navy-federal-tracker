"""
Gmail Client - Connects to Gmail and fetches Navy Federal alert emails
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Optional
import config


class GmailClient:
    """Handles connection to Gmail and fetching Navy Federal alerts."""
    
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993
    
    def __init__(self):
        self.mail: Optional[imaplib.IMAP4_SSL] = None
        
    def connect(self) -> bool:
        """Connect to Gmail using IMAP."""
        try:
            self.mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            self.mail.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            print(f"✅ Connected to Gmail as {config.GMAIL_ADDRESS}")
            return True
        except imaplib.IMAP4.error as e:
            print(f"❌ Gmail login failed: {e}")
            print("   Make sure you're using an App Password, not your regular password!")
            print("   Get one at: https://myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close the Gmail connection."""
        if self.mail:
            try:
                self.mail.logout()
                print("📪 Disconnected from Gmail")
            except:
                pass
    
    def fetch_nfcu_alerts(self, days_back: int = 7, since_date: Optional[datetime] = None) -> List[dict]:
        """
        Fetch Navy Federal alert emails.
        
        Args:
            days_back: How many days back to search
            since_date: If provided, only fetch emails after this date
            
        Returns:
            List of email data dictionaries
        """
        if not self.mail:
            print("❌ Not connected to Gmail")
            return []
        
        # Select All Mail to include archived/deleted emails (except Trash)
        # Try different folder names for different Gmail languages/settings
        folder_selected = False
        for folder in ['"[Gmail]/All Mail"', '"[Gmail]/Todos"', '"[Gmail]/Todo el correo"', 'INBOX']:
            try:
                status, _ = self.mail.select(folder)
                if status == "OK":
                    print(f"📁 Searching in: {folder}")
                    folder_selected = True
                    break
            except:
                continue
        
        if not folder_selected:
            print("⚠️ Could not select All Mail, falling back to INBOX")
            self.mail.select("INBOX")
        
        # Build search criteria
        if since_date:
            date_str = since_date.strftime("%d-%b-%Y")
        else:
            date_str = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        
        # Search for emails from Navy Federal
        search_criteria = f'(FROM "{config.NFCU_SENDER}" SINCE "{date_str}")'
        
        print(f"🔍 Searching for Navy Federal emails since {date_str}...")
        
        try:
            status, message_ids = self.mail.search(None, search_criteria)
            
            if status != "OK":
                print("❌ Search failed")
                return []
            
            email_ids = message_ids[0].split()
            print(f"📧 Found {len(email_ids)} Navy Federal emails")
            
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []
    
    def _fetch_email(self, email_id: bytes) -> Optional[dict]:
        """Fetch a single email by ID."""
        try:
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")
            
            # Get date
            date_str = msg["Date"]
            # Parse email date (handle various formats)
            try:
                # Remove timezone name in parentheses if present
                if "(" in date_str:
                    date_str = date_str[:date_str.index("(")].strip()
                email_date = email.utils.parsedate_to_datetime(date_str)
            except:
                email_date = datetime.now()
            
            # Get body
            body = self._get_email_body(msg)
            
            return {
                "id": email_id.decode(),
                "subject": subject,
                "date": email_date,
                "body": body,
                "raw": msg
            }
            
        except Exception as e:
            print(f"⚠️ Error parsing email: {e}")
            return None
    
    def _get_email_body(self, msg) -> str:
        """Extract the text body from an email message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get text content
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = str(msg.get_payload())
        
        return body


# Quick test
if __name__ == "__main__":
    client = GmailClient()
    if client.connect():
        emails = client.fetch_nfcu_alerts(days_back=7)
        for e in emails[:3]:  # Show first 3
            print(f"\n📧 {e['date']}: {e['subject']}")
        client.disconnect()
