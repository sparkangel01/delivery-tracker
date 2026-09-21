import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, static_folder="static", static_url_path="/static")

DATA_FILE = "data.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Delivery Tracker")
TAGLINE = os.environ.get("TAGLINE", "Track your shipment in real time")


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


@app.route("/api/health")
def health():
    data = read_data()
    return jsonify({"storage": "file", "shipments_count": len(data)})


@app.route("/api/track", methods=["POST"])
def track():
    body = request.get_json() or {}
    code = (body.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "Tracking code required"}), 400
    data = read_data()
    if code not in data:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(data[code])


@app.route("/api/track/<code>")
def track_get(code):
    data = read_data()
    key = code.upper()
    if key not in data:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(data[key])


@app.route("/api/admin/login", methods=["POST"])
def login():
    body = request.get_json() or {}
    if body.get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"error": "Wrong password"}), 401


@app.route("/api/admin/shipment", methods=["POST"])
def add_shipment():
    body = request.get_json() or {}
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    code = (body.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "Tracking code required"}), 400

    data = read_data()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    raw = body.get("images", "") or ""
    images = [u.strip() for u in raw.replace("\n", ",").split(",") if u.strip()]

    # Payment fields (per shipment)
    pay_name = body.get("pay_name", "")
    pay_bank = body.get("pay_bank", "")
    pay_account = body.get("pay_account", "")
    pay_other = body.get("pay_other", "")
    pay_note = body.get("pay_note", "")

    if body.get("edit_mode") and code in data:
        for f in ["origin", "destination", "recipient", "phone", "email",
                  "item", "weight", "pieces", "note_big"]:
            data[code][f] = body.get(f, "")
        data[code]["status"] = body.get("status") or data[code]["status"]
        data[code]["images"] = images
        data[code]["pay_name"] = pay_name
        data[code]["pay_bank"] = pay_bank
        data[code]["pay_account"] = pay_account
        data[code]["pay_other"] = pay_other
        data[code]["pay_note"] = pay_note
        data[code]["history"].insert(0, {
            "status": body.get("status") or "Updated",
            "note": body.get("note") or "Shipment details edited",
            "date": now,
        })
    elif code in data:
        data[code]["status"] = body.get("status") or data[code]["status"]
        if body.get("note_big"):
            data[code]["note_big"] = body.get("note_big")
        existing = data[code].get("images", [])
        data[code]["images"] = existing + [u for u in images if u not in existing]
        # Update payment fields if provided
        if pay_name: data[code]["pay_name"] = pay_name
        if pay_bank: data[code]["pay_bank"] = pay_bank
        if pay_account: data[code]["pay_account"] = pay_account
        if pay_other: data[code]["pay_other"] = pay_other
        if pay_note: data[code]["pay_note"] = pay_note
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
            "pay_name": pay_name,
            "pay_bank": pay_bank,
            "pay_account": pay_account,
            "pay_other": pay_other,
            "pay_note": pay_note,
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
    return jsonify(list(data.values()))


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
