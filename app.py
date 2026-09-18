import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient

app = Flask(__name__, static_folder="static", static_url_path="/static")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Delivery Tracker")
TAGLINE = os.environ.get("TAGLINE", "Track your shipment in real time")
MONGO_URI = os.environ.get("MONGO_URI", "")

client = MongoClient(MONGO_URI) if MONGO_URI else None
db = client["delivery_tracker"] if client is not None else None
shipments_col = db["shipments"] if db is not None else None
payment_col = db["payment"] if db is not None else None


def get_shipment(code):
    if shipments_col is None:
        return None
    return shipments_col.find_one({"code": code.upper()}, {"_id": 0})


def save_shipment(doc):
    if shipments_col is None:
        return
    shipments_col.replace_one({"code": doc["code"]}, doc, upsert=True)


def delete_shipment_db(code):
    if shipments_col is None:
        return
    shipments_col.delete_one({"code": code.upper()})


def all_shipments():
    if shipments_col is None:
        return []
    return list(shipments_col.find({}, {"_id": 0}))


def get_payment():
    if payment_col is None:
        return {}
    doc = payment_col.find_one({"_id": "payment"})
    if not doc:
        return {}
    doc.pop("_id", None)
    return doc


def save_payment(data):
    if payment_col is None:
        return
    payment_col.replace_one({"_id": "payment"}, {**data, "_id": "payment"}, upsert=True)


@app.route("/")
def home():
    return render_template("index.html", company=COMPANY_NAME, tagline=TAGLINE)


@app.route("/admin.html")
def admin():
    return render_template("admin.html", company=COMPANY_NAME)


@app.route("/api/health")
def health():
    return jsonify({
        "mongo_connected": shipments_col is not None,
        "shipments_count": len(all_shipments()) if shipments_col is not None else 0
    })


@app.route("/api/track", methods=["POST"])
def track():
    body = request.get_json() or {}
    code = (body.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "Tracking code required"}), 400
    if shipments_col is None:
        return jsonify({"error": "Database not configured"}), 500
    doc = get_shipment(code)
    if not doc:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(doc)


@app.route("/api/track/<code>")
def track_get(code):
    if shipments_col is None:
        return jsonify({"error": "Database not configured"}), 500
    doc = get_shipment(code)
    if not doc:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(doc)


@app.route("/api/payment")
def api_payment():
    return jsonify(get_payment())


@app.route("/api/admin/login", methods=["POST"])
def login():
    body = request.get_json() or {}
    if body.get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"error": "Wrong password"}), 401


@app.route("/api/admin/payment", methods=["POST"])
def api_save_payment():
    body = request.get_json() or {}
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    save_payment({
        "name": body.get("name", ""),
        "bank": body.get("bank", ""),
        "account": body.get("account", ""),
        "other": body.get("other", ""),
        "note": body.get("note", ""),
    })
    return jsonify({"ok": True})


@app.route("/api/admin/shipment", methods=["POST"])
def add_shipment():
    body = request.get_json() or {}
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    code = (body.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "Tracking code required"}), 400

    if shipments_col is None:
        return jsonify({"error": "Database not configured"}), 500

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    raw = body.get("images", "") or ""
    images = [u.strip() for u in raw.replace("\n", ",").split(",") if u.strip()]

    existing = get_shipment(code)

    if body.get("edit_mode") and existing:
        existing["status"] = body.get("status") or existing.get("status", "")
        for f in ["origin", "destination", "recipient", "phone", "email",
                  "item", "weight", "pieces", "note_big"]:
            existing[f] = body.get(f, "")
        existing["images"] = images
        existing.setdefault("history", []).insert(0, {
            "status": body.get("status") or "Updated",
            "note": body.get("note") or "Shipment details edited",
            "date": now,
        })
        save_shipment(existing)
    elif existing:
        existing["status"] = body.get("status") or existing.get("status", "")
        if body.get("note_big"):
            existing["note_big"] = body.get("note_big")
        old = existing.get("images", [])
        existing["images"] = old + [u for u in images if u not in old]
        existing.setdefault("history", []).insert(0, {
            "status": body.get("status") or "Updated",
            "note": body.get("note", ""),
            "date": now,
        })
        save_shipment(existing)
    else:
        doc = {
            "code": code,
            "status": body.get("status") or "Pending",
            "origin": body.get("origin", ""),
            "destination": body.get("destination", ""),
            "recipient": body.get("recipient", ""),
            "phone": body.get("phone", ""),
            "email": body.get("email", ""),
            "item": body.get("item", ""),
            "weight": body.get("weight", ""),
            "pieces": body.get("pieces", ""),
            "note_big": body.get("note_big", ""),
            "images": images,
            "history": [{
                "status": body.get("status") or "Pending",
                "note": body.get("note") or "Shipment created",
                "date": now,
            }],
        }
        save_shipment(doc)

    return jsonify({"ok": True, "shipment": get_shipment(code)})


@app.route("/api/admin/shipment/<code>")
def api_get_shipment(code):
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    doc = get_shipment(code)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(doc)


@app.route("/api/admin/shipments")
def api_list_shipments():
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(all_shipments())


@app.route("/api/admin/shipment/<code>", methods=["DELETE"])
def api_delete_shipment(code):
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    delete_shipment_db(code)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
