(function(){
var input=document.getElementById('codeInput'),btn=document.getElementById('trackBtn'),result=document.getElementById('result');
if(!input||!btn||!result){return}

function sc(s){s=(s||'').toLowerCase();if(s.indexOf('delivered')>-1)return 'status-delivered';if(s.indexOf('transit')>-1||s.indexOf('shipping')>-1)return 'status-transit';if(s.indexOf('pending')>-1||s.indexOf('created')>-1||s.indexOf('label')>-1)return 'status-pending';if(s.indexOf('picked')>-1)return 'status-picked';if(s.indexOf('out for')>-1)return 'status-out';return 'status-default'}
function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}

function track(){
  var code=input.value.trim();
  if(!code){alert('Please enter a tracking code');return}
  result.innerHTML='<div class="loading">Searching...</div>';
  fetch('/api/track',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code:code})
  })
  .then(function(r){
    return r.text().then(function(txt){
      var data;
      try{data=JSON.parse(txt)}
      catch(e){throw new Error('Server error ('+r.status+'): '+txt.substring(0,150))}
      return {ok:r.ok,status:r.status,data:data};
    });
  })
  .then(function(r){
    if(!r.ok){
      result.innerHTML='<div class="error">❌ '+(r.data.error||('HTTP '+r.status))+'</div>';
      return;
    }
    render(r.data);
  })
  .catch(function(e){
    result.innerHTML='<div class="error">❌ '+esc(e.message)+'</div>';
  });
}

function render(d){
var history=d.history.map(function(h){return '<div class="event"><div class="event-status">'+esc(h.status)+'</div><div class="event-meta">'+(h.note?esc(h.note)+' • ':'')+esc(h.date)+'</div></div>'}).join('');
var fields=[{label:'From',value:d.origin},{label:'To',value:d.destination},{label:'Recipient',value:d.recipient},{label:'Phone',value:d.phone},{label:'Email',value:d.email},{label:'Item',value:d.item},{label:'Weight',value:d.weight},{label:'Pieces',value:d.pieces}];
var details=fields.filter(function(x){return x.value}).map(function(x){return '<div class="detail-item"><div class="detail-label">'+x.label+'</div><div class="detail-value">'+esc(x.value)+'</div></div>'}).join('');
var noteBlock=d.note_big?'<div class="big-note"><div class="big-note-label">📝 Important Note</div>'+esc(d.note_big)+'</div>':'';
var photoBlock=(d.images&&d.images.length)?'<div class="card"><div class="section-title">📷 Package Photos</div><div class="photo-grid">'+d.images.map(function(u){return '<img src="'+esc(u)+'" onclick="showImg(this.src)" onerror="this.style.display=\'none\'">'}).join('')+'</div></div>':'';
result.innerHTML='<div class="card"><span class="status-badge '+sc(d.status)+'">'+esc(d.status)+'</span><h2>'+esc(d.code)+'</h2>'+(d.item?'<div class="subline">'+esc(d.item)+'</div>':'')+'<div class="details">'+details+'</div>'+noteBlock+'<div class="timeline"><h3>📍 Tracking History</h3>'+history+'</div><button class="pay-btn" onclick="openPay()">💳 Pay Now</button></div>'+photoBlock}

window.showImg=function(src){var lb=document.getElementById('lightbox');if(!lb)return;document.getElementById('lightboxImg').src=src;lb.style.display='flex'};
window.openPay=function(){var modal=document.getElementById('payModal');if(!modal)return;modal.classList.add('show');var box=document.getElementById('payDetails');box.innerHTML='Loading...';fetch('/api/payment').then(function(r){return r.json()}).then(function(p){var rows=[];if(p.name)rows.push(['Account Name',p.name]);if(p.bank)rows.push(['Bank',p.bank]);if(p.account)rows.push(['Account Number',p.account]);if(p.other)rows.push(['Other',p.other]);if(!rows.length)rows.push(['Notice','Payment details not available yet.']);box.innerHTML=rows.map(function(r){return '<div class="pay-row"><div class="pay-row-label">'+esc(r[0])+'</div><div class="pay-row-value">'+esc(r[1])+'</div></div>'}).join('');var n=document.getElementById('payNote');if(p.note){n.textContent='💡 '+p.note;n.style.display='block'}else{n.style.display='none'}}).catch(function(){box.innerHTML='<div class="error">Could not load payment details</div>'})};

btn.addEventListener('click',track);
input.addEventListener('keypress',function(e){if(e.key==='Enter')track()});
})();
