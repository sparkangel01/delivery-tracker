import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
DATA_FILE = "data.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def read_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)


def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------- HOME (customer tracking page) ----------
@app.route("/")
def home():
    return Response(INDEX_HTML, mimetype="text/html")


# ---------- ADMIN PAGE ----------
@app.route("/admin.html")
def admin():
    return Response(ADMIN_HTML, mimetype="text/html")


# ---------- PUBLIC API ----------
@app.route("/api/track/<code>")
def track(code):
    data = read_data()
    key = code.upper()
    if key not in data:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(data[key])


# ---------- ADMIN API ----------
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

    code = (body.get("code") or "").strip()
    if not code:
        return jsonify({"error": "Tracking code required"}), 400

    data = read_data()
    key = code.upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if key in data:
        data[key]["status"] = body.get("status") or data[key]["status"]
        data[key]["history"].insert(0, {
            "status": body.get("status") or "Updated",
            "note": body.get("note", ""),
            "date": now,
        })
    else:
        data[key] = {
            "code": key,
            "status": body.get("status") or "Pending",
            "origin": body.get("origin", ""),
            "destination": body.get("destination", ""),
            "recipient": body.get("recipient", ""),
            "history": [{
                "status": body.get("status") or "Pending",
                "note": body.get("note") or "Shipment created",
                "date": now,
            }],
        }

    write_data(data)
    return jsonify({"ok": True, "shipment": data[key]})


@app.route("/api/admin/shipments")
def list_shipments():
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(list(read_data().values()))


@app.route("/api/admin/shipment/<code>", methods=["DELETE"])
def delete_shipment(code):
    if request.args.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = read_data()
    data.pop(code.upper(), None)
    write_data(data)
    return jsonify({"ok": True})


# ---------- HTML PAGES (embedded) ----------
INDEX_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Track Your Delivery</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f0f2f5;min-height:100vh;padding:30px 15px;color:#222}
.container{max-width:700px;margin:0 auto}
h1{text-align:center;margin-bottom:8px;color:#1a1a2e}
.subtitle{text-align:center;color:#666;margin-bottom:25px}
.search-box{display:flex;gap:8px;margin-bottom:20px}
input{flex:1;padding:12px;border:2px solid #ddd;border-radius:8px;font-size:15px;outline:none}
input:focus{border-color:#4f46e5}
button{padding:12px 20px;background:#4f46e5;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer}
button:hover{background:#4338ca}
.card{background:#fff;border-radius:12px;padding:20px;margin-bottom:15px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.status-badge{display:inline-block;padding:6px 14px;background:#e0e7ff;color:#3730a3;border-radius:20px;font-size:13px;font-weight:600;margin-bottom:12px}
.details{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:15px 0}
.detail-label{font-size:12px;color:#888;text-transform:uppercase}
.detail-value{font-weight:600}
.timeline{margin-top:15px;border-top:1px solid #eee;padding-top:15px}
.event{padding:10px 0 10px 20px;border-left:2px solid #ddd;position:relative}
.event::before{content:'';position:absolute;left:-7px;top:15px;width:12px;height:12px;background:#4f46e5;border-radius:50%}
.event-status{font-weight:600;margin-bottom:3px}
.event-meta{font-size:13px;color:#888}
.error{background:#fee;color:#c00;padding:15px;border-radius:8px;text-align:center}
@media(max-width:500px){.details{grid-template-columns:1fr}}
</style></head><body>
<div class="container">
<h1>📦 Track Your Delivery</h1>
<p class="subtitle">Enter your tracking code below</p>
<div class="search-box">
<input type="text" id="codeInput" placeholder="Enter tracking code" autocomplete="off">
<button id="trackBtn">Track</button>
</div>
<div id="result"></div>
</div>
<script>
const input=document.getElementById('codeInput'),btn=document.getElementById('trackBtn'),result=document.getElementById('result');
async function track(){
 const code=input.value.trim(); if(!code)return;
 result.innerHTML='<div class="card">Searching...</div>';
 try{
  const res=await fetch('/api/track/'+encodeURIComponent(code));
  if(!res.ok){const err=await res.json();result.innerHTML='<div class="error">'+err.error+'</div>';return}
  render(await res.json());
 }catch{result.innerHTML='<div class="error">Something went wrong.</div>'}
}
function render(d){
 const history=d.history.map(h=>'<div class="event"><div class="event-status">'+h.status+'</div><div class="event-meta">'+(h.note?h.note+' • ':'')+h.date+'</div></div>').join('');
 result.innerHTML='<div class="card"><span class="status-badge">'+d.status+'</span><h2>'+d.code+'</h2><div class="details">'+
 (d.origin?'<div><div class="detail-label">Origin</div><div class="detail-value">'+d.origin+'</div></div>':'')+
 (d.destination?'<div><div class="detail-label">Destination</div><div class="detail-value">'+d.destination+'</div></div>':'')+
 (d.recipient?'<div><div class="detail-label">Recipient</div><div class="detail-value">'+d.recipient+'</div></div>':'')+
 '</div><div class="timeline"><h3>History</h3>'+history+'</div></div>';
}
btn.addEventListener('click',track);
input.addEventListener('keypress',e=>e.key==='Enter'&&track());
</script></body></html>"""


ADMIN_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Panel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f0f2f5;min-height:100vh;padding:30px 15px;color:#222}
.container{max-width:700px;margin:0 auto}
h1{text-align:center;margin-bottom:8px;color:#1a1a2e}
input{width:100%;padding:12px;border:2px solid #ddd;border-radius:8px;font-size:15px;outline:none;margin-bottom:10px}
input:focus{border-color:#4f46e5}
button{padding:12px 20px;background:#4f46e5;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;width:100%}
button:hover{background:#4338ca}
.card{background:#fff;border-radius:12px;padding:20px;margin-bottom:15px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card h3{margin-bottom:15px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px}
.form-grid input{margin-bottom:0}
.shipment-item{padding:12px;border:1px solid #eee;border-radius:8px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.shipment-item button{padding:6px 12px;font-size:13px;background:#ef4444;width:auto}
@media(max-width:500px){.form-grid{grid-template-columns:1fr}}
</style></head><body>
<div class="container">
<h1>🔧 Admin Panel</h1>
<div id="loginBox" class="card">
<h3>Enter Admin Password</h3>
<input type="password" id="passwordInput" placeholder="Password">
<button id="loginBtn">Login</button>
</div>
<div id="adminBox" style="display:none">
<div class="card">
<h3>Add / Update Shipment</h3>
<div class="form-grid">
<input id="f_code" placeholder="Tracking Code">
<input id="f_status" placeholder="Status">
<input id="f_origin" placeholder="Origin">
<input id="f_destination" placeholder="Destination">
<input id="f_recipient" placeholder="Recipient Name">
<input id="f_note" placeholder="Note (optional)">
</div>
<button id="saveBtn">Save Shipment</button>
</div>
<div class="card">
<h3>All Shipments</h3>
<div id="shipmentList">Loading...</div>
</div>
</div>
</div>
<script>
let password='';
const loginBox=document.getElementById('loginBox'),adminBox=document.getElementById('adminBox');
document.getElementById('loginBtn').addEventListener('click',async()=>{
 const pw=document.getElementById('passwordInput').value;
 const res=await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
 if(res.ok){password=pw;loginBox.style.display='none';adminBox.style.display='block';loadShipments()}
 else alert('Wrong password');
});
document.getElementById('saveBtn').addEventListener('click',async()=>{
 const body={password,code:f_code.value.trim(),status:f_status.value.trim(),origin:f_origin.value.trim(),destination:f_destination.value.trim(),recipient:f_recipient.value.trim(),note:f_note.value.trim()};
 if(!body.code)return alert('Tracking code is required');
 const res=await fetch('/api/admin/shipment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(res.ok){alert('Saved!');['f_code','f_status','f_origin','f_destination','f_recipient','f_note'].forEach(id=>document.getElementById(id).value='');loadShipments()}
 else alert('Error');
});
async function loadShipments(){
 const res=await fetch('/api/admin/shipments?password='+encodeURIComponent(password));
 const list=await res.json();
 const container=document.getElementById('shipmentList');
 if(!list.length){container.innerHTML='<p>No shipments yet.</p>';return}
 container.innerHTML=list.map(s=>'<div class="shipment-item"><div><strong>'+s.code+'</strong><br><small>'+s.status+' — '+(s.destination||'')+'</small></div><button onclick="del(\\''+s.code+'\\')">Delete</button></div>').join('');
}
async function del(code){
 if(!confirm('Delete '+code+'?'))return;
 await fetch('/api/admin/shipment/'+code+'?password='+encodeURIComponent(password),{method:'DELETE'});
 loadShipments();
}
window.del=del;
</script></body></html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
