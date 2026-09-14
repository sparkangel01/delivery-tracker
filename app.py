import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response

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
    html = INDEX_HTML.replace("{{COMPANY_NAME}}", COMPANY_NAME).replace("{{TAGLINE}}", TAGLINE)
    return Response(html, mimetype="text/html")


@app.route("/admin.html")
def admin():
    return Response(ADMIN_HTML.replace("{{COMPANY_NAME}}", COMPANY_NAME), mimetype="text/html")


@app.route("/api/track/<code>")
def track(code):
    data = read_data()
    key = code.upper()
    if key not in data or key == PAYMENT_KEY:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(data[key])


# ---- PUBLIC: payment details ----
@app.route("/api/payment")
def get_payment():
    data = read_data()
    return jsonify(data.get(PAYMENT_KEY, {}))


# ---- ADMIN: save payment details ----
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


@app.route("/api/admin/login", methods=["POST"])
def login():
    if request.get_json().get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"error": "Wrong password"}), 401


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
        data[code]["status"] = body.get("status") or data[code]["status"]
        data[code]["origin"] = body.get("origin", "")
        data[code]["destination"] = body.get("destination", "")
        data[code]["recipient"] = body.get("recipient", "")
        data[code]["phone"] = body.get("phone", "")
        data[code]["email"] = body.get("email", "")
        data[code]["item"] = body.get("item", "")
        data[code]["weight"] = body.get("weight", "")
        data[code]["pieces"] = body.get("pieces", "")
        data[code]["note_big"] = body.get("note_big", "")
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
        existing = data[code].get("images", [])
        merged = existing + [u for u in images if u not in existing]
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


# ---------- CUSTOMER PAGE ----------
INDEX_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{COMPANY_NAME}} — Track Shipment</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 50%,#f093fb 100%);background-attachment:fixed;min-height:100vh;padding:40px 15px;color:#222}
.container{max-width:750px;margin:0 auto}
.header{text-align:center;margin-bottom:30px;color:#fff}
.header .brand{display:inline-block;padding:8px 20px;background:rgba(255,255,255,.2);border-radius:30px;font-size:13px;font-weight:700;letter-spacing:1.5px;margin-bottom:14px;text-transform:uppercase;border:1px solid rgba(255,255,255,.3)}
.header h1{font-size:2.1rem;margin-bottom:8px;text-shadow:0 2px 10px rgba(0,0,0,.2)}
.header p{opacity:.95;font-size:1rem}
.search-box{display:flex;gap:10px;background:#fff;padding:12px;border-radius:16px;box-shadow:0 15px 40px rgba(0,0,0,.25)}
input{flex:1;padding:14px 18px;border:2px solid #e5e7eb;border-radius:10px;font-size:15px;outline:none;transition:all .25s;background:#f9fafb}
input:focus{border-color:#8b5cf6;background:#fff;box-shadow:0 0 0 4px rgba(139,92,246,.15)}
button{padding:14px 26px;color:#fff;border:none;border-radius:10px;font-weight:700;font-size:15px;cursor:pointer;background:linear-gradient(135deg,#8b5cf6,#ec4899);box-shadow:0 6px 20px rgba(139,92,246,.4);transition:all .2s}
button:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,.55)}
#result{margin-top:25px}
.card{background:#fff;border-radius:18px;padding:26px;box-shadow:0 20px 50px rgba(0,0,0,.2);animation:pop .35s cubic-bezier(.34,1.56,.64,1);position:relative;overflow:hidden;margin-bottom:20px}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(90deg,#8b5cf6,#ec4899,#f59e0b)}
@keyframes pop{from{opacity:0;transform:scale(.95) translateY(15px)}to{opacity:1;transform:scale(1) translateY(0)}}
.status-badge{display:inline-block;padding:8px 18px;border-radius:24px;font-size:13px;font-weight:700;margin-bottom:14px;letter-spacing:.4px;text-transform:uppercase;box-shadow:0 4px 12px rgba(0,0,0,.1)}
.status-delivered{background:linear-gradient(135deg,#10b981,#059669);color:#fff}
.status-transit{background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff}
.status-pending{background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff}
.status-picked{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff}
.status-out{background:linear-gradient(135deg,#06b6d4,#0891b2);color:#fff}
.status-default{background:linear-gradient(135deg,#8b5cf6,#7c3aed);color:#fff}
.card h2{color:#1a1a2e;font-size:1.4rem;margin-bottom:4px;font-family:ui-monospace,monospace;letter-spacing:.5px}
.subline{color:#6b7280;font-size:13px;margin-bottom:14px}
.details{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}
.detail-item{padding:14px;background:linear-gradient(135deg,#f5f3ff,#fce7f3);border-radius:12px;border-left:4px solid #8b5cf6}
.detail-label{font-size:11px;color:#7c3aed;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px}
.detail-value{font-weight:600;color:#1a1a2e;font-size:15px;word-break:break-word}
.big-note{margin:20px 0;padding:22px;background:linear-gradient(135deg,#fef3c7,#fde68a);border-left:6px solid #f59e0b;border-radius:14px;font-size:18px;line-height:1.6;color:#78350f;font-weight:500;white-space:pre-wrap}
.big-note-label{font-size:12px;color:#92400e;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}
.section-title{color:#1a1a2e;font-size:1.2rem;margin-bottom:14px;font-weight:700}
.photo-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.photo-grid img{width:100%;height:200px;object-fit:cover;border-radius:16px;cursor:pointer;border:4px solid #f3f4f6;transition:all .25s;box-shadow:0 6px 18px rgba(0,0,0,.08)}
.photo-grid img:hover{transform:scale(1.03);border-color:#8b5cf6;box-shadow:0 12px 28px rgba(139,92,246,.3)}
.photo-grid img:only-child{grid-column:1/-1;height:300px}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.93);display:none;justify-content:center;align-items:center;padding:20px;z-index:1000;cursor:pointer}
.lightbox img{max-width:100%;max-height:90vh;border-radius:12px}
.pay-btn{width:100%;margin-top:20px;padding:18px;font-size:17px;font-weight:800;letter-spacing:.5px;background:linear-gradient(135deg,#10b981,#059669);box-shadow:0 10px 30px rgba(16,185,129,.4);border-radius:14px}
.pay-btn:hover{box-shadow:0 14px 40px rgba(16,185,129,.55)}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;justify-content:center;align-items:center;padding:20px;z-index:2000}
.modal.show{display:flex}
.modal-inner{background:#fff;border-radius:20px;padding:28px;max-width:440px;width:100%;box-shadow:0 30px 80px rgba(0,0,0,.5);animation:pop .3s cubic-bezier(.34,1.56,.64,1);position:relative;max-height:90vh;overflow-y:auto}
.modal-inner h3{color:#1a1a2e;font-size:1.3rem;margin-bottom:6px}
.modal-inner .modal-sub{color:#6b7280;font-size:13px;margin-bottom:20px}
.pay-row{padding:14px 18px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-left:4px solid #10b981;border-radius:12px;margin-bottom:10px}
.pay-row-label{font-size:11px;color:#065f46;font-weight:800;text-transform:uppercase;letter-spacing:.8px;margin-bottom:3px}
.pay-row-value{font-weight:700;color:#064e3b;font-size:16px;font-family:ui-monospace,monospace;word-break:break-all}
.pay-note{margin-top:16px;padding:14px;background:#fef3c7;border-radius:10px;color:#92400e;font-size:13px;font-weight:500;line-height:1.5}
.modal-close{position:absolute;top:14px;right:14px;background:#f3f4f6;color:#374151;border:none;border-radius:50%;width:36px;height:36px;font-size:18px;font-weight:700;cursor:pointer;padding:0;box-shadow:none}
.modal-close:hover{background:#e5e7eb;transform:none}
.timeline{margin-top:20px;border-top:2px dashed #e5e7eb;padding-top:20px}
.timeline h3{color:#1a1a2e;margin-bottom:15px;font-size:1.05rem}
.event{padding:12px 0 12px 26px;position:relative;border-left:2px solid #e5e7eb}
.event::before{content:'';position:absolute;left:-8px;top:16px;width:14px;height:14px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#ec4899);box-shadow:0 0 0 4px rgba(139,92,246,.15);border:2px solid #fff}
.event:first-child::before{background:linear-gradient(135deg,#10b981,#059669);box-shadow:0 0 0 4px rgba(16,185,129,.2);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 4px rgba(16,185,129,.2)}50%{box-shadow:0 0 0 8px rgba(16,185,129,.05)}}
.event-status{font-weight:700;color:#1a1a2e;margin-bottom:4px;font-size:15px}
.event-meta{font-size:13px;color:#6b7280}
.error{background:linear-gradient(135deg,#fee2e2,#fecaca);color:#991b1b;padding:20px;border-radius:14px;text-align:center;font-weight:600;border-left:4px solid #dc2626}
.loading{text-align:center;padding:30px;color:#fff;font-weight:600}
.loading::after{content:'';display:inline-block;width:16px;height:16px;margin-left:10px;border:3px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:500px){.details{grid-template-columns:1fr}.header h1{font-size:1.6rem}.photo-grid img{height:150px}.photo-grid img:only-child{height:220px}.big-note{font-size:16px}}
</style></head><body>
<div class="container">
<div class="header">
<div class="brand">{{COMPANY_NAME}}</div>
<h1>📦 Track Your Shipment</h1>
<p>{{TAGLINE}}</p>
</div>
<div class="search-box">
<input type="text" id="codeInput" placeholder="Enter tracking code" autocomplete="off">
<button id="trackBtn">Track</button>
</div>
<div id="result"></div>
</div>
<div class="lightbox" id="lightbox" onclick="this.style.display='none'"><img id="lightboxImg" src=""></div>
<div class="modal" id="payModal" onclick="if(event.target===this)this.classList.remove('show')">
  <div class="modal-inner">
    <button class="modal-close" onclick="document.getElementById('payModal').classList.remove('show')">✕</button>
    <h3>💳 Payment Details</h3>
    <p class="modal-sub">Send payment to any account below</p>
    <div id="payDetails">Loading...</div>
    <div class="pay-note" id="payNote" style="display:none"></div>
  </div>
</div>
<script>
const input=document.getElementById('codeInput'),btn=document.getElementById('trackBtn'),result=document.getElementById('result');
function statusClass(s){s=(s||'').toLowerCase();if(s.includes('delivered'))return 'status-delivered';if(s.includes('transit')||s.includes('shipping'))return 'status-transit';if(s.includes('pending')||s.includes('created')||s.includes('label'))return 'status-pending';if(s.includes('picked')||s.includes('pickup'))return 'status-picked';if(s.includes('out for'))return 'status-out';return 'status-default'}
async function track(){const code=input.value.trim();if(!code)return;result.innerHTML='<div class="loading">Searching</div>';try{const res=await fetch('/api/track/'+encodeURIComponent(code));if(!res.ok){const err=await res.json();result.innerHTML='<div class="error">❌ '+err.error+'</div>';return}render(await res.json())}catch{result.innerHTML='<div class="error">❌ Something went wrong.</div>'}}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function render(d){
 const history=d.history.map(h=>'<div class="event"><div class="event-status">'+esc(h.status)+'</div><div class="event-meta">'+(h.note?esc(h.note)+' • ':'')+esc(h.date)+'</div></div>').join('');
 const details=[{label:'From',value:d.origin},{label:'To',value:d.destination},{label:'Recipient',value:d.recipient},{label:'Phone',value:d.phone},{label:'Email',value:d.email},{label:'Item',value:d.item},{label:'Weight',value:d.weight},{label:'Pieces',value:d.pieces}].filter(x=>x.value).map(x=>'<div class="detail-item"><div class="detail-label">'+x.label+'</div><div class="detail-value">'+esc(x.value)+'</div></div>').join('');
 const noteBlock=d.note_big?'<div class="big-note"><div class="big-note-label">📝 Important Note</div>'+esc(d.note_big)+'</div>':'';
 const photoBlock=(d.images&&d.images.length)?'<div class="card"><div class="section-title">📷 Package Photos</div><div class="photo-grid">'+d.images.map(u=>'<img src="'+esc(u)+'" onclick="showImg(this.src)" onerror="this.style.display=\\'none\\'">').join('')+'</div></div>':'';
 const payBlock='<button class="pay-btn" onclick="openPay()">💳 Pay Now</button>';
 result.innerHTML='<div class="card"><span class="status-badge '+statusClass(d.status)+'">'+esc(d.status)+'</span><h2>'+esc(d.code)+'</h2>'+(d.item?'<div class="subline">'+esc(d.item)+'</div>':'')+'<div class="details">'+details+'</div>'+noteBlock+'<div class="timeline"><h3>📍 Tracking History</h3>'+history+'</div>'+payBlock+'</div>'+photoBlock;
}
function showImg(src){const lb=document.getElementById('lightbox');document.getElementById('lightboxImg').src=src;lb.style.display='flex'}
async function openPay(){
 document.getElementById('payModal').classList.add('show');
 const box=document.getElementById('payDetails');
 box.innerHTML='Loading...';
 try{
  const res=await fetch('/api/payment');
  const p=await res.json();
  const rows=[];
  if(p.name)rows.push(['Account Name',p.name]);
  if(p.bank)rows.push(['Bank',p.bank]);
  if(p.account)rows.push(['Account Number',p.account]);
  if(p.other)rows.push(['Other',p.other]);
  if(!rows.length)rows.push(['Notice','Payment details not available yet. Please contact us.']);
  box.innerHTML=rows.map(r=>'<div class="pay-row"><div class="pay-row-label">'+esc(r[0])+'</div><div class="pay-row-value">'+esc(r[1])+'</div></div>').join('');
  const n=document.getElementById('payNote');
  if(p.note){n.textContent='💡 '+p.note;n.style.display='block'}else n.style.display='none';
 }catch{box.innerHTML='<div class="error">Could not load payment details</div>'}
}
window.showImg=showImg;window.openPay=openPay;
btn.addEventListener('click',track);
input.addEventListener('keypress',e=>e.key==='Enter'&&track());
</script></body></html>"""


# ---------- ADMIN PAGE ----------
ADMIN_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{COMPANY_NAME}} — Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#4c1d95 100%);background-attachment:fixed;min-height:100vh;padding:40px 15px;color:#222}
.container{max-width:800px;margin:0 auto}
.header{text-align:center;margin-bottom:25px;color:#fff}
.header .brand{display:inline-block;padding:8px 20px;background:rgba(255,255,255,.15);border-radius:30px;font-size:13px;font-weight:700;letter-spacing:1.5px;margin-bottom:12px;text-transform:uppercase;border:1px solid rgba(255,255,255,.25)}
.header h1{font-size:1.8rem;text-shadow:0 2px 10px rgba(0,0,0,.3)}
.card{background:#fff;border-radius:18px;padding:24px;margin-bottom:20px;box-shadow:0 20px 50px rgba(0,0,0,.3);position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(90deg,#f59e0b,#ec4899,#8b5cf6)}
.card.payment::before{background:linear-gradient(90deg,#10b981,#06b6d4,#3b82f6)}
.card h3{margin-bottom:18px;color:#1a1a2e;font-size:1.1rem}
input,textarea{width:100%;padding:12px 15px;border:2px solid #e5e7eb;border-radius:10px;font-size:14px;outline:none;margin-bottom:12px;transition:all .2s;background:#f9fafb;font-family:inherit;resize:vertical}
input:focus,textarea:focus{border-color:#8b5cf6;background:#fff;box-shadow:0 0 0 4px rgba(139,92,246,.15)}
button{padding:13px 24px;color:#fff;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;background:linear-gradient(135deg,#8b5cf6,#ec4899);box-shadow:0 6px 20px rgba(139,92,246,.4);transition:all .2s;width:100%}
button:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,.55)}
button.green{background:linear-gradient(135deg,#10b981,#059669);box-shadow:0 6px 20px rgba(16,185,129,.4)}
button.green:hover{box-shadow:0 8px 25px rgba(16,185,129,.55)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.form-grid input{margin-bottom:0}
.section-label{font-size:12px;color:#7c3aed;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin:10px 0 8px}
.edit-banner{display:none;padding:12px 16px;background:linear-gradient(135deg,#fef3c7,#fde68a);border-left:4px solid #f59e0b;border-radius:10px;margin-bottom:16px;font-weight:600;color:#92400e}
.edit-banner.show{display:block}
.btn-cancel{padding:10px 20px;background:#e5e7eb;color:#374151;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer;margin-top:8px;width:100%;box-shadow:none}
.btn-cancel:hover{background:#d1d5db;transform:none;box-shadow:none}
.shipment-item{padding:14px 16px;border:2px solid #e5e7eb;border-radius:12px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;gap:10px;transition:all .2s;background:#f9fafb}
.shipment-item:hover{border-color:#8b5cf6;background:#faf5ff}
.shipment-item strong{color:#1a1a2e;font-family:ui-monospace,monospace;font-size:15px}
.shipment-item small{color:#6b7280;font-size:13px}
.shipment-actions{display:flex;gap:6px}
.btn-edit{padding:8px 14px;font-size:12px;width:auto;background:linear-gradient(135deg,#3b82f6,#2563eb);box-shadow:0 4px 12px rgba(59,130,246,.35)}
.btn-del{padding:8px 14px;font-size:12px;width:auto;background:linear-gradient(135deg,#ef4444,#dc2626);box-shadow:0 4px 12px rgba(239,68,68,.35)}
.empty{text-align:center;color:#6b7280;padding:20px;font-style:italic}
.pay-hint{font-size:12px;color:#6b7280;margin-bottom:10px}
@media(max-width:500px){.form-grid{grid-template-columns:1fr}}
</style></head><body>
<div class="container">
<div class="header">
<div class="brand">{{COMPANY_NAME}} Admin</div>
<h1>🔧 Control Panel</h1>
</div>

<div id="loginBox" class="card">
<h3>🔐 Enter Admin Password</h3>
<input type="password" id="passwordInput" placeholder="Password">
<button id="loginBtn">Login</button>
</div>

<div id="adminBox" style="display:none">

<!-- PAYMENT SETTINGS -->
<div class="card payment">
<h3>💳 Payment Settings</h3>
<p class="pay-hint">These show up when a customer taps "Pay Now". Editable anytime.</p>
<div class="form-grid">
<input id="p_name" placeholder="Account Name">
<input id="p_bank" placeholder="Bank Name">
</div>
<div class="form-grid">
<input id="p_account" placeholder="Account Number">
<input id="p_other" placeholder="Other (Opay, PayPal, etc.)">
</div>
<input id="p_note" placeholder="Note for customers (e.g. Send screenshot after payment)">
<button id="savePaymentBtn" class="green">💾 Save Payment Settings</button>
</div>

<!-- SHIPMENT FORM -->
<div class="card">
<div id="editBanner" class="edit-banner">✏️ Editing: <span id="editingCode"></span></div>
<h3 id="formTitle">➕ Add / Update Shipment</h3>

<div class="section-label">Tracking Info</div>
<div class="form-grid">
<input id="f_code" placeholder="Tracking Code">
<input id="f_status" placeholder="Status (e.g. In Transit)">
</div>

<div class="section-label">Route</div>
<div class="form-grid">
<input id="f_origin" placeholder="Origin">
<input id="f_destination" placeholder="Destination">
</div>

<div class="section-label">Recipient</div>
<div class="form-grid">
<input id="f_recipient" placeholder="Recipient Name">
<input id="f_phone" placeholder="Phone">
</div>
<input id="f_email" placeholder="Email">

<div class="section-label">Package Details</div>
<div class="form-grid">
<input id="f_item" placeholder="Item (e.g. Electronics)">
<input id="f_weight" placeholder="Weight (e.g. 2.5 kg)">
</div>
<input id="f_pieces" placeholder="Number of Pieces">

<div class="section-label">📸 Package Photos (paste image URLs, one per line)</div>
<textarea id="f_images" rows="5" placeholder="https://i.imgur.com/abc.jpg&#10;https://i.imgur.com/xyz.jpg" style="font-size:13px"></textarea>

<div class="section-label">📝 Big Note (shown large on customer page)</div>
<textarea id="f_note_big" rows="6" placeholder="Type any important info here — pickup instructions, customs notes, delivery window, payment reminders..." style="font-size:15px;line-height:1.5"></textarea>

<div class="section-label">Short Note (for history entry only)</div>
<input id="f_note" placeholder="e.g. Customs clearance in progress">

<button id="saveBtn">💾 Save Shipment</button>
<button id="cancelBtn" class="btn-cancel" style="display:none">✖️ Cancel Edit</button>
</div>

<div class="card">
<h3>📋 All Shipments</h3>
<div id="shipmentList">Loading...</div>
</div>
</div>
</div>
<script>
let password='';
let editingCode=null;
const loginBox=document.getElementById('loginBox'),adminBox=document.getElementById('adminBox');
const saveBtn=document.getElementById('saveBtn'),cancelBtn=document.getElementById('cancelBtn');
const editBanner=document.getElementById('editBanner'),editingCodeSpan=document.getElementById('editingCode');
const formTitle=document.getElementById('formTitle');

document.getElementById('loginBtn').addEventListener('click',async()=>{
 const pw=document.getElementById('passwordInput').value;
 const res=await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
 if(res.ok){password=pw;loginBox.style.display='none';adminBox.style.display='block';loadPayment();loadShipments()}
 else alert('❌ Wrong password');
});

// --- Payment settings ---
async function loadPayment(){
 try{
  const res=await fetch('/api/payment');
  const p=await res.json();
  document.getElementById('p_name').value=p.name
