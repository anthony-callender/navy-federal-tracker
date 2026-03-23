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
import hmac
import hashlib
import functools
from datetime import datetime, timedelta
from pathlib import Path

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
# Auth helpers
# ---------------------------------------------------------------------------

AUTH_USERNAME = os.environ.get("AUTH_USERNAME", "")
AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "")
_SECRET = os.environ.get("SECRET_KEY", "dev-secret-change-me")


def _make_token(username: str, password: str) -> str:
    msg = f"{username}:{password}".encode()
    return hmac.new(_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def _valid_token(token: str) -> bool:
    if not AUTH_USERNAME or not AUTH_PASSWORD:
        return True  # auth not configured — open access
    expected = _make_token(AUTH_USERNAME, AUTH_PASSWORD)
    return hmac.compare_digest(expected, token)


def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_USERNAME:
            return f(*args, **kwargs)
        token = request.headers.get("X-Auth-Token", "")
        if not _valid_token(token):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth guard — protect all /api/* except /api/login
# ---------------------------------------------------------------------------

@app.before_request
def check_auth():
    if not request.path.startswith("/api/"):
        return  # let static files and webhooks through
    if request.path == "/api/login":
        return  # login endpoint is public
    if not AUTH_USERNAME:
        return  # auth not configured
    token = request.headers.get("X-Auth-Token", "")
    if not _valid_token(token):
        return jsonify({"error": "unauthorized"}), 401


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


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")
    if not AUTH_USERNAME:
        return jsonify({"token": "no-auth"})
    if username == AUTH_USERNAME and password == AUTH_PASSWORD:
        return jsonify({"token": _make_token(username, password)})
    return jsonify({"error": "invalid credentials"}), 401


@app.route("/sync", methods=["POST"])
def manual_sync():
    sync_emails()
    return jsonify({"status": "sync complete"}), 200


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _last_n_months(n: int = 6):
    now = datetime.now()
    months = []
    for i in range(n - 1, -1, -1):
        # Step back i months correctly using year/month arithmetic
        total = now.year * 12 + (now.month - 1) - i
        y, m = divmod(total, 12)
        months.append(f"{y}-{m + 1:02d}")
    return months


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
    keywords = data.get("keywords", "")
    if not name:
        return jsonify({"error": "name required"}), 400
    me = database.create_monthly_expense(name, amount, category, keywords)
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


@app.route("/api/classify-transactions", methods=["POST"])
def api_classify():
    """Match transactions to monthly expenses using keywords."""
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    result = database.classify_transactions(month)
    return jsonify(result)


@app.route("/api/clear-classifications", methods=["POST"])
def api_clear_classifications():
    """Remove all monthly expense links for a month."""
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    cleared = database.clear_classifications(month)
    return jsonify({"cleared": cleared})


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
# Config API
# ---------------------------------------------------------------------------

@app.route("/api/config/<key>", methods=["GET"])
def api_config_get(key):
    value = database.get_config(key)
    if value is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"key": key, "value": value})


@app.route("/api/config/<key>", methods=["PATCH"])
def api_config_set(key):
    data = request.get_json(force=True)
    value = data.get("value")
    if value is None:
        return jsonify({"error": "value required"}), 400
    database.set_config(key, str(value))
    return jsonify({"status": "updated"})


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
    # ?offset=0 means most recent 6 months; offset=1 means 6 months before that, etc.
    offset = int(request.args.get("offset", 0))
    all_months = database.get_all_months()
    if not all_months:
        return jsonify([])
    end = max(0, len(all_months) - offset * 6)
    start = max(0, end - 6)
    months = all_months[start:end]
    data = database.get_chart_data(months)
    return jsonify({"data": data, "has_prev": start > 0, "has_next": offset > 0, "total_months": len(all_months)})


@app.route("/api/dashboard/chart-data/yearly", methods=["GET"])
def api_chart_data_yearly():
    data = database.get_yearly_chart_data()
    return jsonify({"data": data, "has_prev": False, "has_next": False, "total_months": len(data)})


# ---------------------------------------------------------------------------
# Statement import API
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(os.environ.get("DATA_DIR", "/data")) / "uploaded_statements"


@app.route("/upload-statement", methods=["POST"])
def upload_statement():
    """Upload a PDF statement file to the server."""
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400
    f = request.files["file"]
    if not f.filename.endswith(".pdf"):
        return jsonify({"error": "only PDF files accepted"}), 400
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f.filename
    f.save(str(dest))
    return jsonify({"status": "uploaded", "file": f.filename}), 200


@app.route("/import-statements", methods=["POST"])
def import_statements():
    """Run the PDF statement importer on all uploaded and bundled PDFs."""
    from statement_importer import parse_pdf, STATEMENTS_DIR

    # Collect PDFs from both the uploaded dir and the repo-bundled dir
    pdfs = []
    if UPLOAD_DIR.exists():
        pdfs.extend(sorted(UPLOAD_DIR.glob("*.pdf")))
    if STATEMENTS_DIR.exists():
        pdfs.extend(sorted(STATEMENTS_DIR.glob("*.pdf")))

    if not pdfs:
        return jsonify({"error": "no PDF files found"}), 400

    total_new = 0
    results = []
    for pdf_path in pdfs:
        txs = parse_pdf(pdf_path)
        new = sum(1 for tx in txs if database.save_transaction(tx))
        total_new += new
        results.append({"file": pdf_path.name, "parsed": len(txs), "new": new})

    return jsonify({"status": "done", "total_new": total_new, "files": results})


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
