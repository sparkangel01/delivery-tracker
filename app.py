import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
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
    html = INDEX_HTML.replace("{{COMPANY_NAME}}", COMPANY_NAME).replace("{{TAGLINE}}", TAGLINE)
    return Response(html, mimetype="text/html")


@app.route("/admin.html")
def admin():
    html = ADMIN_HTML.replace("{{COMPANY_NAME}}", COMPANY_NAME)
    return Response(html, mimetype="text/html")


@app.route("/api/track/<code>")
def track(code):
    data = read_data()
    key = code.upper()
    if key not in data:
        return jsonify({"error": "Tracking code not found"}), 404
    return jsonify(data[key])


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

    # Parse comma-separated image URLs into a list
    images_raw = body.get("images", "") or ""
    images = [u.strip() for u in images_raw.split(",") if u.strip()]

    if key in data:
        data[key]["status"] = body.get("status") or data[key]["status"]
        # Merge new images (don't replace old ones)
        existing = data[key].get("images", [])
        merged = existing + [u for u in images if u not in existing]
        data[key]["images"] = merged
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
            "phone": body.get("phone", ""),
            "email": body.get("email", ""),
            "item": body.get("item", ""),
            "weight": body.get("weight", ""),
            "pieces": body.get("pieces", ""),
            "images": images,
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


# ---------- COLORFUL CUSTOMER PAGE ----------
INDEX_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{COMPANY_NAME}} — Track Shipment</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:system-ui,-apple-system,sans-serif;
  background:linear-gradient(135deg,#667eea 0%,#764ba2 50%,#f093fb 100%);
  background-attachment:fixed;
  min-height:100vh;padding:40px 15px;color:#222;
}
.container{max-width:750px;margin:0 auto}
.header{text-align:center;margin-bottom:30px;color:#fff}
.header .brand{
  display:inline-block;padding:8px 20px;
  background:rgba(255,255,255,.2);backdrop-filter:blur(10px);
  border-radius:30px;font-size:13px;font-weight:700;
  letter-spacing:1.5px;margin-bottom:14px;text-transform:uppercase;
  border:1px solid rgba(255,255,255,.3);
}
.header h1{
  font-size:2.1rem;margin-bottom:8px;
  text-shadow:0 2px 10px rgba(0,0,0,.2);
  animation:slideDown .6s ease;
}
.header p{opacity:.95;font-size:1rem;animation:slideDown .8s ease}
@keyframes slideDown{from{opacity:0;transform:translateY(-15px)}to{opacity:1;transform:translateY(0)}}

.search-box{
  display:flex;gap:10px;background:#fff;
  padding:12px;border-radius:16px;
  box-shadow:0 15px 40px rgba(0,0,0,.25);
  animation:slideUp .5s ease;
}
@keyframes slideUp{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}

input{
  flex:1;padding:14px 18px;border:2px solid #e5e7eb;
  border-radius:10px;font-size:15px;outline:none;
  transition:all .25s;background:#f9fafb;
}
input:focus{border-color:#8b5cf6;background:#fff;box-shadow:0 0 0 4px rgba(139,92,246,.15)}

button{
  padding:14px 26px;color:#fff;border:none;border-radius:10px;
  font-weight:700;font-size:15px;cursor:pointer;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);
  box-shadow:0 6px 20px rgba(139,92,246,.4);
  transition:all .2s;
}
button:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,.55)}

#result{margin-top:25px}

.card{
  background:#fff;border-radius:18px;padding:26px;
  box-shadow:0 20px 50px rgba(0,0,0,.2);
  animation:pop .35s cubic-bezier(.34,1.56,.64,1);
  position:relative;overflow:hidden;margin-bottom:20px;
}
.card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:5px;
  background:linear-gradient(90deg,#8b5cf6,#ec4899,#f59e0b);
}
@keyframes pop{from{opacity:0;transform:scale(.95) translateY(15px)}to{opacity:1;transform:scale(1) translateY(0)}}

.status-badge{
  display:inline-block;padding:8px 18px;border-radius:24px;
  font-size:13px;font-weight:700;margin-bottom:14px;
  letter-spacing:.4px;text-transform:uppercase;
  box-shadow:0 4px 12px rgba(0,0,0,.1);
}
.status-delivered{background:linear-gradient(135deg,#10b981,#059669);color:#fff}
.status-transit{background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff}
.status-pending{background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff}
.status-picked{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff}
.status-out{background:linear-gradient(135deg,#06b6d4,#0891b2);color:#fff}
.status-default{background:linear-gradient(135deg,#8b5cf6,#7c3aed);color:#fff}

.card h2{
  color:#1a1a2e;font-size:1.4rem;margin-bottom:4px;
  font-family:ui-monospace,monospace;letter-spacing:.5px;
}
.subline{color:#6b7280;font-size:13px;margin-bottom:14px}

.details{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}
.detail-item{
  padding:14px;background:linear-gradient(135deg,#f5f3ff,#fce7f3);
  border-radius:12px;border-left:4px solid #8b5cf6;
}
.detail-label{
  font-size:11px;color:#7c3aed;font-weight:700;
  text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;
}
.detail-value{font-weight:600;color:#1a1a2e;font-size:15px;word-break:break-word}

.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;margin-top:10px}
.gallery img{
  width:100%;height:120px;object-fit:cover;
  border-radius:12px;cursor:pointer;
  border:3px solid #f3f4f6;transition:all .2s;
}
.gallery img:hover{transform:scale(1.05);border-color:#8b5cf6;box-shadow:0 8px 20px rgba(139,92,246,.3)}

.lightbox{
  position:fixed;inset:0;background:rgba(0,0,0,.9);
  display:none;justify-content:center;align-items:center;
  padding:20px;z-index:1000;cursor:pointer;
}
.lightbox img{max-width:100%;max-height:90vh;border-radius:12px}

.timeline{margin-top:20px;border-top:2px dashed #e5e7eb;padding-top:20px}
.timeline h3{color:#1a1a2e;margin-bottom:15px;font-size:1.05rem}
.event{padding:12px 0 12px 26px;position:relative;border-left:2px solid #e5e7eb}
.event::before{
  content:'';position:absolute;left:-8px;top:16px;
  width:14px;height:14px;border-radius:50%;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);
  box-shadow:0 0 0 4px rgba(139,92,246,.15);
  border:2px solid #fff;
}
.event:first-child::before{
  background:linear-gradient(135deg,#10b981,#059669);
  box-shadow:0 0 0 4px rgba(16,185,129,.2);
  animation:pulse 2s infinite;
}
@keyframes pulse{0%,100%{box-shadow:0 0 0 4px rgba(16,185,129,.2)}50%{box-shadow:0 0 0 8px rgba(16,185,129,.05)}}
.event-status{font-weight:700;color:#1a1a2e;margin-bottom:4px;font-size:15px}
.event-meta{font-size:13px;color:#6b7280}

.error{
  background:linear-gradient(135deg,#fee2e2,#fecaca);
  color:#991b1b;padding:20px;border-radius:14px;
  text-align:center;font-weight:600;
  border-left:4px solid #dc2626;
}
.loading{text-align:center;padding:30px;color:#fff;font-weight:600}
.loading::after{
  content:'';display:inline-block;width:16px;height:16px;
  margin-left:10px;border:3px solid rgba(255,255,255,.4);
  border-top-color:#fff;border-radius:50%;
  animation:spin .8s linear infinite;vertical-align:middle;
}
@keyframes spin{to{transform:rotate(360deg)}}

@media(max-width:500px){
  .details{grid-template-columns:1fr}
  .header h1{font-size:1.6rem}
}
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

<div class="lightbox" id="lightbox" onclick="this.style.display='none'">
  <img id="lightboxImg" src="">
</div>

<script>
const input=document.getElementById('codeInput'),btn=document.getElementById('trackBtn'),result=document.getElementById('result');

function statusClass(s){
  s=(s||'').toLowerCase();
  if(s.includes('delivered'))return 'status-delivered';
  if(s.includes('transit')||s.includes('shipping'))return 'status-transit';
  if(s.includes('pending')||s.includes('created')||s.includes('label'))return 'status-pending';
  if(s.includes('picked')||s.includes('pickup'))return 'status-picked';
  if(s.includes('out for'))return 'status-out';
  return 'status-default';
}

async function track(){
 const code=input.value.trim(); if(!code)return;
 result.innerHTML='<div class="loading">Searching</div>';
 try{
  const res=await fetch('/api/track/'+encodeURIComponent(code));
  if(!res.ok){const err=await res.json();result.innerHTML='<div class="error">❌ '+err.error+'</div>';return}
  render(await res.json());
 }catch{result.innerHTML='<div class="error">❌ Something went wrong.</div>'}
}

function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}

function render(d){
 const history=d.history.map(h=>'<div class="event"><div class="event-status">'+esc(h.status)+'</div><div class="event-meta">'+(h.note?esc(h.note)+' • ':'')+esc(h.date)+'</div></div>').join('');

 const details=[
   {label:'From',value:d.origin},
   {label:'To',value:d.destination},
   {label:'Recipient',value:d.recipient},
   {label:'Phone',value:d.phone},
   {label:'Email',value:d.email},
   {label:'Item',value:d.item},
   {label:'Weight',value:d.weight},
   {label:'Pieces',value:d.pieces}
 ].filter(x=>x.value).map(x=>'<div class="detail-item"><div class="detail-label">'+x.label+'</div><div class="detail-value">'+esc(x.value)+'</div></div>').join('');

 const imgs = (d.images && d.images.length)
   ? '<div class="card"><h3 style="color:#1a1a2e;margin-bottom:12px">📷 Package Images</h3><div class="gallery">'+
     d.images.map(u=>'<img src="'+esc(u)+'" onclick="showImg(this.src)" onerror="this.style.display=\\'none\\'">').join('')+
     '</div></div>'
   : '';

 result.innerHTML='<div class="card"><span class="status-badge '+statusClass(d.status)+'">'+esc(d.status)+'</span><h2>'+esc(d.code)+'</h2>'+
   (d.item?'<div class="subline">'+esc(d.item)+'</div>':'')+
   '<div class="details">'+details+'</div>'+
   '<div class="timeline"><h3>📍 Tracking History</h3>'+history+'</div></div>'+
   imgs;
}

function showImg(src){
 const lb=document.getElementById('lightbox');
 document.getElementById('lightboxImg').src=src;
 lb.style.display='flex';
}
window.showImg=showImg;

btn.addEventListener('click',track);
input.addEventListener('keypress',e=>e.key==='Enter'&&track());
</script></body></html>"""


# ---------- COLORFUL ADMIN PAGE ----------
ADMIN_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{COMPANY_NAME}} — Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:system-ui,-apple-system,sans-serif;
  background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#4c1d95 100%);
  background-attachment:fixed;min-height:100vh;padding:40px 15px;color:#222;
}
.container{max-width:800px;margin:0 auto}
.header{text-align:center;margin-bottom:25px;color:#fff}
.header .brand{
  display:inline-block;padding:8px 20px;
  background:rgba(255,255,255,.15);border-radius:30px;
  font-size:13px;font-weight:700;letter-spacing:1.5px;
  margin-bottom:12px;text-transform:uppercase;
  border:1px solid rgba(255,255,255,.25);
}
.header h1{font-size:1.8rem;text-shadow:0 2px 10px rgba(0,0,0,.3)}

.card{
  background:#fff;border-radius:18px;padding:24px;
  margin-bottom:20px;box-shadow:0 20px 50px rgba(0,0,0,.3);
  animation:pop .35s cubic-bezier(.34,1.56,.64,1);
  position:relative;overflow:hidden;
}
.card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:5px;
  background:linear-gradient(90deg,#f59e0b,#ec4899,#8b5cf6);
}
@keyframes pop{from{opacity:0;transform:scale(.96) translateY(10px)}to{opacity:1;transform:scale(1) translateY(0)}}

.card h3{margin-bottom:18px;color:#1a1a2e;font-size:1.1rem}

input,textarea{
  width:100%;padding:12px 15px;border:2px solid #e5e7eb;
  border-radius:10px;font-size:14px;outline:none;
  margin-bottom:12px;transition:all .2s;background:#f9fafb;
  font-family:inherit;resize:vertical;
}
input:focus,textarea:focus{border-color:#8b5cf6;background:#fff;box-shadow:0 0 0 4px rgba(139,92,246,.15)}

button{
  padding:13px 24px;color:#fff;border:none;border-radius:10px;
  font-weight:700;font-size:14px;cursor:pointer;
  background:linear-gradient(135deg,#8b5cf6,#ec4899);
  box-shadow:0 6px 20px rgba(139,92,246,.4);
  transition:all .2s;width:100%;
}
button:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,.55)}

.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.form-grid input{margin-bottom:0}

.section-label{
  font-size:12px;color:#7c3aed;font-weight:700;
  text-transform:uppercase;letter-spacing:.8px;
  margin:10px 0 8px;
}

.shipment-item{
  padding:14px 16px;border:2px solid #e5e7eb;
  border-radius:12px;margin-bottom:10px;
  display:flex;justify-content:space-between;align-items:center;gap:10px;
  transition:all .2s;background:#f9fafb;
}
.shipment-item:hover{border-color:#8b5cf6;background:#faf5ff;transform:translateX(3px)}
.shipment-item strong{color:#1a1a2e;font-family:ui-monospace,monospace;font-size:15px}
.shipment-item small{color:#6b7280;font-size:13px}
.shipment-item button{
  padding:8px 14px;font-size:12px;width:auto;
  background:linear-gradient(135deg,#ef4444,#dc2626);
  box-shadow:0 4px 12px rgba(239,68,68,.35);
}

.empty{text-align:center;color:#6b7280;padding:20px;font-style:italic}

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
<div class="card">
<h3>➕ Add / Update Shipment</h3>

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

<div class="section-label">Images (paste URLs, comma-separated)</div>
<textarea id="f_images" rows="3" placeholder="https://i.imgur.com/abc.jpg, https://i.imgur.com/xyz.jpg"></textarea>
<p style="font-size:12px;color:#6b7280;margin-bottom:12px">Upload your image to <b>imgur.com</b>, <b>postimages.org</b>, or any image host → copy the direct link → paste it here. Separate multiple with commas.</p>

<div class="section-label">Note (optional)</div>
<input id="f_note" placeholder="e.g. Customs clearance in progress">

<button id="saveBtn">💾 Save Shipment</button>
</div>

<div class="card">
<h3>📋 All Shipments</h3>
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
 else alert('❌ Wrong password');
});

document.getElementById('saveBtn').addEventListener('click',async()=>{
 const g=id=>document.getElementById(id).value.trim();
 const body={password,code:g('f_code'),status:g('f_status'),origin:g('f_origin'),destination:g('f_destination'),recipient:g('f_recipient'),phone:g('f_phone'),email:g('f_email'),item:g('f_item'),weight:g('f_weight'),pieces:g('f_pieces'),images:g('f_images'),note:g('f_note')};
 if(!body.code)return alert('Tracking code is required');
 const res=await fetch('/api/admin/shipment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(res.ok){alert('✅ Saved!');['f_code','f_status','f_origin','f_destination','f_recipient','f_phone','f_email','f_item','f_weight','f_pieces','f_images','f_note'].forEach(id=>document.getElementById(id).value='');loadShipments()}
 else alert('❌ Error');
});

async function loadShipments(){
 const res=await fetch('/api/admin/shipments?password='+encodeURIComponent(password));
 const list=await res.json();
 const container=document.getElementById('shipmentList');
 if(!list.length){container.innerHTML='<p class="empty">No shipments yet — add one above ☝️</p>';return}
 container.innerHTML=list.map(s=>{
   const imgs = s.images && s.images.length ? ' 📷'+s.images.length : '';
   return '<div class="shipment-item"><div><strong>'+s.code+'</strong>'+imgs+'<br><small>'+s.status+' — '+(s.destination||'no destination')+'</small></div><button onclick="del(\\''+s.code+'\\')">🗑️</button></div>';
 }).join('');
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
