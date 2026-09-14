(function () {
  var password = '';
  var editingCode = null;

  var loginBox = document.getElementById('loginBox');
  var adminBox = document.getElementById('adminBox');

  function g(id) {
    var el = document.getElementById(id);
    return el ? el.value.trim() : '';
  }

  function setVal(id, v) {
    var el = document.getElementById(id);
    if (el) el.value = v || '';
  }

  document.getElementById('loginBtn').addEventListener('click', function () {
    var pw = document.getElementById('passwordInput').value;
    fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw })
    }).then(function (res) {
      if (res.ok) {
        password = pw;
        loginBox.style.display = 'none';
        adminBox.style.display = 'block';
        loadPayment();
        loadShipments();
      } else {
        alert('❌ Wrong password');
      }
    });
  });

  function loadPayment() {
    fetch('/api/payment')
      .then(function (r) { return r.json(); })
      .then(function (p) {
        setVal('p_name', p.name);
        setVal('p_bank', p.bank);
        setVal('p_account', p.account);
        setVal('p_other', p.other);
        setVal('p_note', p.note);
      });
  }

  document.getElementById('savePaymentBtn').addEventListener('click', function () {
    fetch('/api/admin/payment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        password: password,
        name: g('p_name'),
        bank: g('p_bank'),
        account: g('p_account'),
        other: g('p_other'),
        note: g('p_note')
      })
    }).then(function (res) {
      if (res.ok) alert('✅ Payment details saved!');
      else alert('❌ Error saving');
    });
  });

  document.getElementById('saveBtn').addEventListener('click', function () {
    var body = {
      password: password,
      edit_mode: !!editingCode,
      code: g('f_code'),
      status: g('f_status'),
      origin: g('f_origin'),
      destination: g('f_destination'),
      recipient: g('f_recipient'),
      phone: g('f_phone'),
      email: g('f_email'),
      item: g('f_item'),
      weight: g('f_weight'),
      pieces: g('f_pieces'),
      images: g('f_images'),
      note_big: g('f_note_big'),
      note: g('f_note')
    };

    if (!body.code) {
      alert('Tracking code is required');
      return;
    }

    fetch('/api/admin/shipment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (res) {
      if (res.ok) {
        alert(editingCode ? '✅ Updated!' : '✅ Saved!');
        clearForm();
        loadShipments();
      } else {
        alert('❌ Error saving');
      }
    });
  });

  document.getElementById('cancelBtn').addEventListener('click', clearForm);

  function clearForm() {
    editingCode = null;
    ['f_code', 'f_status', 'f_origin', 'f_destination', 'f_recipient',
     'f_phone', 'f_email', 'f_item', 'f_weight', 'f_pieces',
     'f_images', 'f_note_big', 'f_note'].forEach(function (id) { setVal(id, ''); });
    document.getElementById('editBanner').classList.remove('show');
    document.getElementById('cancelBtn').style.display = 'none';
    document.getElementById('formTitle').textContent = '➕ Add / Update Shipment';
    document.getElementById('saveBtn').textContent = '💾 Save Shipment';
  }

  function editShipment(code) {
    fetch('/api/admin/shipment/' + code + '?password=' + encodeURIComponent(password))
      .then(function (r) {
        if (!r.ok) throw new Error('Could not load');
        return r.json();
      })
      .then(function (d) {
        setVal('f_code', d.code);
        setVal('f_status', d.status);
        setVal('f_origin', d.origin);
        setVal('f_destination', d.destination);
        setVal('f_recipient', d.recipient);
        setVal('f_phone', d.phone);
        setVal('f_email', d.email);
        setVal('f_item', d.item);
        setVal('f_weight', d.weight);
        setVal('f_pieces', d.pieces);
        setVal('f_images', (d.images || []).join('\n'));
        setVal('f_note_big', d.note_big);
        setVal('f_note', '');

        editingCode = code;
        document.getElementById('editingCode').textContent = code;
        document.getElementById('editBanner').classList.add('show');
        document.getElementById('cancelBtn').style.display = 'block';
        document.getElementById('formTitle').textContent = '✏️ Edit Shipment';
        document.getElementById('saveBtn').textContent = '💾 Update Shipment';
        window.scrollTo({ top: 0, behavior: 'smooth' });
      })
      .catch(function (e) { alert('❌ ' + e.message); });
  }

  function loadShipments() {
    fetch('/api/admin/shipments?password=' + encodeURIComponent(password))
      .then(function (r) { return r.json(); })
      .then(function (list) {
        var container = document.getElementById('shipmentList');
        if (!list.length) {
          container.innerHTML = '<p class="empty">No shipments yet</p>';
          return;
        }
        container.innerHTML = list.map(function (s) {
          return '<div class="shipment-item"><div><strong>' + s.code +
            '</strong><br><small>' + s.status + ' — ' + (s.destination || '') +
            '</small></div><div class="shipment-actions">' +
            '<button class="btn-edit" onclick="editShipment(\'' + s.code + '\')">✏️ Edit</button>' +
            '<button class="btn-del" onclick="del(\'' + s.code + '\')">🗑️</button>' +
            '</div></div>';
        }).join('');
      });
  }

  function del(code) {
    if (!confirm('Delete ' + code + '?')) return;
    fetch('/api/admin/shipment/' + code + '?password=' + encodeURIComponent(password), {
      method: 'DELETE'
    }).then(function () {
      if (editingCode === code) clearForm();
      loadShipments();
    });
  }

  window.del = del;
  window.editShipment = editShipment;
})();
