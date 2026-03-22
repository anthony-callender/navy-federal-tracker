"""
app.py - Main Flask application
  - POST /webhook  : Twilio WhatsApp webhook
  - GET  /health   : Health check
  - POST /sync     : Manually trigger email sync
"""
import os

from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse

import database
import whatsapp_bot
from scheduler import start_scheduler, sync_emails

app = Flask(__name__)

# Initialize DB tables on startup
database.init_db()


@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive an incoming WhatsApp message from Twilio and reply."""
    incoming_msg = request.form.get("Body", "")
    from_number = request.form.get("From", "")

    print(f"📱 Message from {from_number}: {incoming_msg!r}")

    reply_text = whatsapp_bot.handle_incoming_message(incoming_msg, from_number)

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/sync", methods=["POST"])
def manual_sync():
    """Trigger an immediate email sync (useful for testing)."""
    sync_emails()
    return jsonify({"status": "sync complete"}), 200


if __name__ == "__main__":
    # Start background Gmail polling
    scheduler = start_scheduler()

    port = int(os.environ.get("PORT", 5000))
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    finally:
        scheduler.shutdown()
