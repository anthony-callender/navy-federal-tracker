"""
app.py - Main Flask application
  Existing:
    POST /webhook  - Twilio WhatsApp webhook
    GET  /health   - Health check
    POST /sync     - Manual email sync

  New dashboard API:
    /api/transactions, /api/categories, /api/monthly-expenses,
    /api/debts, /api/dashboard/*
"""
import os
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse

import database
import budget
import whatsapp_bot
from scheduler import start_scheduler, sync_emails

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
CORS(app)

database.init_db()


# ---------------------------------------------------------------------------
# Existing routes (keep unchanged)
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
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
    sync_emails()
    return jsonify({"status": "sync complete"}), 200


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _last_n_months(n: int = 6):
    months = []
    now = datetime.now()
    for i in range(n - 1, -1, -1):
        d = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
        months.append(d.strftime("%Y-%m"))
    return sorted(set(months))


# ---------------------------------------------------------------------------
# Transactions API
# ---------------------------------------------------------------------------

@app.route("/api/transactions", methods=["GET"])
def api_transactions():
    month = request.args.get("month")
    category = request.args.get("category")
    limit = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))
    rows = database.get_transactions_filtered(month=month, category=category,
                                              limit=limit, offset=offset)
    return jsonify(rows)


@app.route("/api/transactions/<int:tx_id>", methods=["GET"])
def api_transaction_get(tx_id):
    rows = database.get_transactions_filtered()
    match = next((r for r in rows if r["id"] == tx_id), None)
    if not match:
        return jsonify({"error": "not found"}), 404
    return jsonify(match)


@app.route("/api/transactions/<int:tx_id>", methods=["PATCH"])
def api_transaction_update(tx_id):
    data = request.get_json(force=True)
    allowed = {k: data[k] for k in ("category", "monthly_expense_id") if k in data}
    if not allowed:
        return jsonify({"error": "no valid fields"}), 400
    database.update_transaction(tx_id, allowed)
    return jsonify({"status": "updated"})


@app.route("/api/transactions/recent/<int:limit>", methods=["GET"])
def api_transactions_recent(limit):
    rows = database.get_transactions(limit=limit)
    return jsonify(rows)


# ---------------------------------------------------------------------------
# Categories API
# ---------------------------------------------------------------------------

@app.route("/api/categories", methods=["GET"])
def api_categories_list():
    return jsonify(database.get_categories())


@app.route("/api/categories", methods=["POST"])
def api_categories_create():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    color = data.get("color", "#9ca3af")
    if not name:
        return jsonify({"error": "name required"}), 400
    try:
        cat = database.create_category(name, color)
        return jsonify(cat), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 409


@app.route("/api/categories/<int:cat_id>", methods=["PATCH"])
def api_categories_update(cat_id):
    data = request.get_json(force=True)
    database.update_category(cat_id, data)
    return jsonify({"status": "updated"})


@app.route("/api/categories/<int:cat_id>", methods=["DELETE"])
def api_categories_delete(cat_id):
    ok = database.delete_category(cat_id)
    if not ok:
        return jsonify({"error": "cannot delete default category"}), 400
    return jsonify({"status": "deleted"})


# ---------------------------------------------------------------------------
# Monthly Expenses API
# ---------------------------------------------------------------------------

@app.route("/api/monthly-expenses", methods=["GET"])
def api_me_list():
    return jsonify(database.get_monthly_expenses())


@app.route("/api/monthly-expenses", methods=["POST"])
def api_me_create():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    amount = float(data.get("expected_amount", 0))
    category = data.get("category", "Bills & Utilities")
    if not name:
        return jsonify({"error": "name required"}), 400
    me = database.create_monthly_expense(name, amount, category)
    return jsonify(me), 201


@app.route("/api/monthly-expenses/<int:me_id>", methods=["PATCH"])
def api_me_update(me_id):
    data = request.get_json(force=True)
    database.update_monthly_expense(me_id, data)
    return jsonify({"status": "updated"})


@app.route("/api/monthly-expenses/<int:me_id>", methods=["DELETE"])
def api_me_delete(me_id):
    database.delete_monthly_expense(me_id)
    return jsonify({"status": "deleted"})


# ---------------------------------------------------------------------------
# Debts API
# ---------------------------------------------------------------------------

@app.route("/api/debts", methods=["GET"])
def api_debts_list():
    return jsonify(database.get_debts())


@app.route("/api/debts", methods=["POST"])
def api_debts_create():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    amount = float(data.get("amount_owed", 0))
    if not name:
        return jsonify({"error": "name required"}), 400
    debt = database.create_debt(
        name=name,
        amount_owed=amount,
        creditor=data.get("creditor", ""),
        due_date=data.get("due_date", ""),
        notes=data.get("notes", ""),
    )
    return jsonify(debt), 201


@app.route("/api/debts/<int:debt_id>", methods=["PATCH"])
def api_debts_update(debt_id):
    data = request.get_json(force=True)
    database.update_debt(debt_id, data)
    return jsonify({"status": "updated"})


@app.route("/api/debts/<int:debt_id>", methods=["DELETE"])
def api_debts_delete(debt_id):
    database.delete_debt(debt_id)
    return jsonify({"status": "deleted"})


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------

@app.route("/api/dashboard/totals", methods=["GET"])
def api_dashboard_totals():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    return jsonify(database.get_dashboard_totals(month))


@app.route("/api/dashboard/variable-by-category", methods=["GET"])
def api_variable_by_category():
    months = _last_n_months(6)
    data = database.get_variable_by_category_pivot(months)
    return jsonify({"months": months, "data": data})


@app.route("/api/dashboard/monthly-by-expense", methods=["GET"])
def api_monthly_by_expense():
    months = _last_n_months(6)
    data = database.get_monthly_by_expense_pivot(months)
    return jsonify({"months": months, "data": data})


@app.route("/api/dashboard/free-spending", methods=["GET"])
def api_free_spending():
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    status = budget.get_budget_status(month)
    return jsonify(status)


@app.route("/api/dashboard/chart-data", methods=["GET"])
def api_chart_data():
    months = _last_n_months(6)
    data = database.get_chart_data(months)
    return jsonify(data)


# ---------------------------------------------------------------------------
# Serve React frontend (after build)
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    dist = os.path.join(app.root_path, "frontend", "dist")
    if path and os.path.exists(os.path.join(dist, path)):
        return send_from_directory(dist, path)
    index = os.path.join(dist, "index.html")
    if os.path.exists(index):
        return send_from_directory(dist, "index.html")
    return jsonify({"message": "Navy Federal API", "status": "ok"}), 200


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scheduler = start_scheduler()
    port = int(os.environ.get("PORT", 5000))
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    finally:
        scheduler.shutdown()
