"""
Scheduler - Background job to sync Gmail → SQLite every 5 minutes
"""
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import database
from gmail_client import GmailClient
from email_parser import NFCUEmailParser
from whatsapp_bot import check_and_send_low_balance_alert


def sync_emails():
    """Fetch new Navy Federal emails and persist any new transactions."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Syncing Gmail...")

    client = GmailClient()
    if not client.connect():
        print("  ❌ Gmail connection failed — skipping sync")
        return

    try:
        emails = client.fetch_nfcu_alerts(days_back=2)
        parser = NFCUEmailParser()
        new_count = 0

        for email_data in emails:
            if database.email_already_processed(email_data["id"]):
                continue

            transaction = parser.parse_email(email_data)
            if transaction:
                saved = database.save_transaction(transaction)
                if saved:
                    new_count += 1
                    print(f"  ✅ Saved: {transaction.merchant} — ${transaction.amount:.2f}")

        print(f"  Sync complete: {new_count} new transaction(s)")

        if new_count > 0:
            check_and_send_low_balance_alert()

    finally:
        client.disconnect()


def start_scheduler() -> BackgroundScheduler:
    """Start the APScheduler background scheduler and return it."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_emails, "interval", minutes=5, id="email_sync",
                      misfire_grace_time=60)
    scheduler.start()
    print("📅 Background email sync started (every 5 minutes)")
    return scheduler
