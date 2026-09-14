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
      password
