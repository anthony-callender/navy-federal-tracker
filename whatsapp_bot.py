"""
WhatsApp Bot - Handles incoming and outgoing Twilio WhatsApp messages
"""
import os
from typing import Optional

import database
import budget


ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "+14155238886")
MY_WHATSAPP_NUMBER = os.environ.get("MY_WHATSAPP_NUMBER", "")


def handle_incoming_message(body: str, from_number: str) -> str:
    """
    Parse an incoming WhatsApp message and return the reply text.
    """
    text = body.strip().lower()

    # --- balance / free-to-spend ---
    if any(kw in text for kw in ["balance", "how much", "left", "budget", "status", "free"]):
        status = budget.get_budget_status()
        return budget.format_balance_message(status)

    # --- spending breakdown ---
    if any(kw in text for kw in ["spending", "breakdown", "categories", "spent"]):
        status = budget.get_budget_status()
        return budget.format_spending_breakdown(status)

    # --- recent transactions ---
    if any(kw in text for kw in ["transactions", "recent", "last", "history"]):
        txs = database.get_transactions(limit=5)
        if not txs:
            return "No transactions found."
        lines = ["*Last 5 Transactions*", ""]
        for tx in txs:
            sign = "-" if tx["transaction_type"] == "debit" else "+"
            name = tx["merchant"] or (tx["description"] or "")[:30]
            lines.append(f"{tx['date']}  {sign}${tx['amount']:.2f}  {name}")
        return "\n".join(lines)

    # --- help ---
    if any(kw in text for kw in ["help", "commands", "?"]):
        return (
            "*Navy Federal Budget Bot*\n\n"
            "Commands:\n"
            "• *balance* — Free to spend this month\n"
            "• *spending* — Breakdown by category\n"
            "• *transactions* — Last 5 transactions\n"
            "• *help* — Show this menu"
        )

    return "I didn't understand that. Reply *help* to see available commands."


def send_message(to_number: str, message: str):
    """Send a WhatsApp message via Twilio."""
    if not (ACCOUNT_SID and AUTH_TOKEN):
        print("⚠️  Twilio credentials not configured — skipping send")
        return

    from twilio.rest import Client
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to_number}",
        body=message,
    )


def check_and_send_low_balance_alert():
    """Send a WhatsApp alert if free-to-spend is below the configured threshold."""
    if not MY_WHATSAPP_NUMBER:
        return

    status = budget.get_budget_status()
    threshold_str = database.get_config("alert_threshold")
    threshold = float(threshold_str) if threshold_str else 200.0

    if status["free_to_spend"] < threshold:
        emoji = "🚨" if status["free_to_spend"] < 0 else "⚠️"
        message = (
            f"{emoji} *Low Balance Alert*\n\n"
            f"Free to spend: *${status['free_to_spend']:,.2f}*\n"
            f"Income: ${status['income']:,.2f}\n"
            f"Fixed bills: ${status['total_fixed']:,.2f}\n"
            f"Variable spending: ${status['total_variable']:,.2f}"
        )
        send_message(MY_WHATSAPP_NUMBER, message)
        print(f"📱 Low balance alert sent: ${status['free_to_spend']:,.2f}")
