(function () {
  var cfg = window.SEATMAP;
  var hall = document.getElementById('hall');
  var selected = [];               // seat labels in click order
  var lastClicked = null;

  var $ = function (id) { return document.getElementById(id); };

  function toast(msg) {
    var box = $('toasts');
    var t = document.createElement('div');
    t.className = 'toast toast-error';
    t.textContent = msg;
    box.appendChild(t);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 400); }, 2600);
  }

  function btnFor(label) { return hall.querySelector('button.seat[data-seat="' + label + '"]'); }

  function rowOrder(label) {
    return label.charCodeAt(0) * 1000 + parseInt(label.slice(1), 10);
  }

  function setSelected(label, on) {
    var b = btnFor(label);
    if (!b) return false;
    var i = selected.indexOf(label);
    if (on && i === -1) {
      if (selected.length >= cfg.max) { toast('Maximum ' + cfg.max + ' seats per booking.'); return false; }
      selected.push(label);
      b.classList.add('sel');
      b.setAttribute('aria-pressed', 'true');
    } else if (!on && i !== -1) {
      selected.splice(i, 1);
      b.classList.remove('sel');
      b.setAttribute('aria-pressed', 'false');
    }
    return true;
  }

  function render() {
    var sorted = selected.slice().sort(function (a, b) { return rowOrder(a) - rowOrder(b); });
    $('seatsInput').value = sorted.join(',');

    var nStall = 0, nBalc = 0;
    sorted.forEach(function (l) {
      var b = btnFor(l);
      if (b && b.dataset.sec === 'balcony') nBalc++; else nStall++;
    });
    $('nStall').textContent = nStall;
    $('nBalc').textContent = nBalc;
    $('tTotal').textContent = sorted.length;
    $('counter').innerHTML = '<b>' + sorted.length + '</b> / ' + cfg.max;
    $('counter').classList.toggle('full', sorted.length >= cfg.max);
    $('mCount').textContent = sorted.length;
    $('mobileBar').classList.toggle('show', sorted.length > 0);

    // chips grouped by row: "A 5 6 7"
    var chips = $('chips');
    chips.querySelectorAll('.chip').forEach(function (c) { c.remove(); });
    $('chipsEmpty').hidden = sorted.length > 0;
    $('clearSel').hidden = sorted.length === 0;
    sorted.forEach(function (l) {
      var c = document.createElement('button');
      c.type = 'button';
      c.className = 'chip';
      c.title = 'Remove ' + l;
      c.innerHTML = l + ' <span aria-hidden="true">×</span>';
      c.addEventListener('click', function () { setSelected(l, false); render(); });
      chips.appendChild(c);
    });

    var btn = $('submitBtn');
    var ok = sorted.length >= cfg.min && sorted.length <= cfg.max;
    btn.disabled = !ok;
    btn.textContent = ok
      ? 'Confirm booking · ' + sorted.length + ' seat' + (sorted.length > 1 ? 's' : '')
      : 'Select seats to book';
  }

  hall.addEventListener('click', function (e) {
    var b = e.target.closest('button.seat');
    if (!b) return;
    var label = b.dataset.seat;

    // Shift+click: select range within the same row
    if (e.shiftKey && lastClicked && lastClicked[0] === label[0] && lastClicked !== label) {
      var row = label[0];
      var a = parseInt(lastClicked.slice(1), 10), z = parseInt(label.slice(1), 10);
      var lo = Math.min(a, z), hi = Math.max(a, z);
      for (var n = lo; n <= hi; n++) {
        if (!setSelected(row + n, true)) { if (selected.length >= cfg.max) break; }
      }
    } else {
      setSelected(label, selected.indexOf(label) === -1);
    }
    lastClicked = label;
    render();
  });

  $('clearSel').addEventListener('click', function () {
    selected.slice().forEach(function (l) { setSelected(l, false); });
    render();
  });


  $('bookForm').addEventListener('submit', function (e) {
    if (selected.length < cfg.min || selected.length > cfg.max) {
      e.preventDefault();
      toast('Select between ' + cfg.min + ' and ' + cfg.max + ' seats.');
      return;
    }
    $('submitBtn').disabled = true;
    $('submitBtn').textContent = 'Booking…';
  });

  // Zoom
  var zoom = 1;
  var scroll = $('hallScroll');
  function fit() {
    hall.style.setProperty('--z', 1);
    var natural = hall.scrollWidth;
    var avail = scroll.clientWidth - 8;
    zoom = Math.max(0.45, Math.min(1.4, avail / natural));
    hall.style.setProperty('--z', zoom.toFixed(3));
  }
  document.querySelectorAll('[data-zoom]').forEach(function (b) {
    b.addEventListener('click', function () {
      var d = parseInt(b.dataset.zoom, 10);
      if (d === 0) return fit();
      zoom = Math.max(0.45, Math.min(1.8, zoom + d * 0.15));
      hall.style.setProperty('--z', zoom.toFixed(3));
    });
  });

  // keyboard: buttons are already focusable; Enter/Space toggles natively
  hall.querySelectorAll('button.seat').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });

  (cfg.preselect || []).forEach(function (l) { setSelected(l, true); });
  if (window.innerWidth > 1100) fit();
  render();
})();
