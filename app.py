import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response, render_template

app = Flask(__name__)
DATA_FILE = "data.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Delivery Tracker")
TAGLINE = os.environ.get("TAGLINE", "Track your shipment in real time")
PAYMENT_KEY = "__payment__"


def read_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)


def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/")
def home():
    return render_template("index.html", company=COMPANY_NAME, tagline=TAGLINE)


@app.route("/admin.html")
def admin():
    return render_template("admin.html", company=COMPANY_NAME)


@app.route("/api/track/<code>")
def track(code):
    data = read_data()
    key = code.upper()
    if key not in data or key == PAYMENT_KEY:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(data[key])


@app.route("/api/payment")
def get_payment():
    data = read_data()
    return jsonify(data.get(PAYMENT_KEY, {}))


@app.route("/api/admin/login", methods=["POST"])
def login():
    if request.get_json().get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"error": "Wrong password"}), 401


@app.route("/api/admin/payment", methods=["POST"])
def save_payment():
    body = request.get_json()
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = read_data()
    data[PAYMENT_KEY] = {
        "name": body.get("name", ""),
        "bank": body.get("bank", ""),
        "account": body.get("account", ""),
        "other": body.get("other", ""),
        "note": body.get("note", ""),
    }
    write_data(data)
    return jsonify({"ok": True})


@app.route("/api/admin/shipment", methods=["POST"])
def add_shipment():
    body = request.get_json()
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    code = (body.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "Tracking code required"}), 400

    data = read_data()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    images_raw = body.get("images", "") or ""
    images = [u.strip() for u in images_raw.replace("\n", ",").split(",") if u.strip()]

    if body.get("edit_mode") and code in data:
        for f in ["origin","destination","recipient","phone","email","item","weight","pieces","note_big"]:
            data[code][f] = body.get(f, "")
        data[code]["status"] = body.get("status") or data[code]["status"]
        data[code]["images"] = images
        data[code]["history"].insert(0, {
            "status": body.get("status") or "Updated",
            "note": body.get("note") or "Shipment details edited",
            "date": now,
        })
    elif code in data:
        data[code]["status"] = body.get("status") or data[code]["status"]
        if body.get("note_big"):
            data[code]["note_big"] = body.get("note_big")
        merged = data[code].get("images", []) + [u for u in images if u not in data[code].get("images", [])]
        data[code]["images"] = merged
        data[code]["history"].insert(0, {
            "status": body.get("status") or "Updated",
            "note": body.get("note", ""),
            "date": now,
        })
    else:
        data[code] = {
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
    write_data(data)
    return jsonify({"ok": True, "shipment": data[code]})


@app.route("/api/admin/shipment/<code>")
def get_shipment(code):
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = read_data()
    key = code.upper()
    if key not in data:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data[key])


@app.route("/api/admin/shipments")
def list_shipments():
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = read_data()
    return jsonify([v for k, v in data.items() if k != PAYMENT_KEY])


@app.route("/api/admin/shipment/<code>", methods=["DELETE"])
def delete_shipment(code):
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = read_data()
    data.pop(code.upper(), None)
    write_data(data)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
