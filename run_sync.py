#!/usr/bin/env python3
"""
Navy Federal Transaction Tracker - Main Entry Point

Usage:
    python run_sync.py              # Run once
    python run_sync.py --watch      # Run continuously (check every 5 min)
    python run_sync.py --days 30    # Sync last 30 days
    python run_sync.py --test       # Test Gmail connection only
"""

import argparse
import sys
import time
from datetime import datetime, timedelta

from gmail_client import GmailClient
from email_parser import NFCUEmailParser
from excel_manager import ExcelManager
import config


def print_banner():
    """Print a nice banner."""
    print("\n" + "=" * 60)
    print("  🏦 Navy Federal Transaction Tracker")
    print("=" * 60)


def test_connection():
    """Test Gmail connection."""
    print("\n🔌 Testing Gmail connection...")
    client = GmailClient()
    
    if client.connect():
        print("✅ Connection successful!")
        
        # Try to fetch a few emails
        emails = client.fetch_nfcu_alerts(days_back=7)
        print(f"📧 Found {len(emails)} Navy Federal emails in the last 7 days")
        
        if emails:
            print("\nSample email subjects:")
            for e in emails[:5]:
                print(f"   • {e['subject'][:60]}...")
        
        client.disconnect()
        return True
    else:
        print("❌ Connection failed!")
        print("\nTroubleshooting:")
        print("1. Check your Gmail address in config.py")
        print("2. Make sure you're using an App Password")
        print("3. App Password link: https://myaccount.google.com/apppasswords")
        return False


def sync_transactions(days_back: int = None):
    """
    Sync transactions from Gmail to Excel.
    
    Args:
        days_back: How many days to look back. If None, uses last sync date.
    """
    print("\n🔄 Starting transaction sync...")
    
    # Initialize components
    gmail = GmailClient()
    parser = NFCUEmailParser()
    excel = ExcelManager()
    
    # Determine how far back to look
    if days_back:
        since_date = datetime.now() - timedelta(days=days_back)
        print(f"📅 Looking back {days_back} days (since {since_date.strftime('%Y-%m-%d')})")
    else:
        last_sync = excel.get_last_sync_date()
        if last_sync:
            since_date = last_sync - timedelta(days=1)  # Overlap by 1 day for safety
            print(f"📅 Last sync: {last_sync.strftime('%Y-%m-%d')}, checking since then...")
        else:
            since_date = datetime.now() - timedelta(days=config.INITIAL_DAYS_BACK)
            print(f"📅 First run! Looking back {config.INITIAL_DAYS_BACK} days")
    
    # Connect to Gmail
    if not gmail.connect():
        return False
    
    try:
        # Fetch emails
        emails = gmail.fetch_nfcu_alerts(since_date=since_date)
        
        if not emails:
            print("📭 No new Navy Federal emails found")
            return True
        
        # Parse transactions
        print(f"\n📝 Parsing {len(emails)} emails...")
        transactions = parser.parse_multiple(emails)
        
        if not transactions:
            print("📭 No valid transactions found (might all be internal transfers)")
            return True
        
        # Save to Excel
        print(f"\n💾 Saving to Excel...")
        added = excel.add_transactions(transactions)
        
        # Summary
        print("\n" + "-" * 40)
        print("📊 Sync Summary:")
        print(f"   • Emails processed: {len(emails)}")
        print(f"   • Transactions found: {len(transactions)}")
        print(f"   • New transactions added: {added}")
        print(f"   • Total in database: {excel.get_transaction_count()}")
        print(f"   • File: {excel.filepath}")
        print("-" * 40)
        
        return True
        
    finally:
        gmail.disconnect()


def watch_mode():
    """Run continuously, checking for new transactions periodically."""
    print(f"\n👁️ Watch mode: Checking every {config.CHECK_INTERVAL_MINUTES} minutes")
    print("   Press Ctrl+C to stop\n")
    
    try:
        while True:
            sync_transactions()
            print(f"\n💤 Sleeping for {config.CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(config.CHECK_INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching. Goodbye!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync Navy Federal transactions from email to Excel"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Test Gmail connection only"
    )
    parser.add_argument(
        "--watch", 
        action="store_true", 
        help="Run continuously, checking periodically"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        help="Number of days to look back"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check config
    if config.GMAIL_ADDRESS == "your_email@gmail.com":
        print("\n⚠️  Please configure your Gmail credentials in config.py first!")
        print("   Edit: config.py")
        print("   Set: GMAIL_ADDRESS and GMAIL_APP_PASSWORD")
        sys.exit(1)
    
    if args.test:
        success = test_connection()
        sys.exit(0 if success else 1)
    
    if args.watch:
        watch_mode()
    else:
        success = sync_transactions(days_back=args.days)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
