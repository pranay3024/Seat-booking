(function () {
  var cfg = window.SEATMAP;
  var hall = document.getElementById('hall');
  var selected = [];               // seat labels in click order

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

  function seatCount() {
    return parseInt($('seatCount').value, 10);
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

  function groupFrom(anchor, count) {
    var row = Array.prototype.slice.call(hall.querySelectorAll('.seat-grid .seat[data-seat]'))
      .filter(function (seat) { return seat.dataset.seat[0] === anchor[0]; })
      .sort(function (a, b) { return rowOrder(a.dataset.seat) - rowOrder(b.dataset.seat); });
    var anchorIndex = row.findIndex(function (seat) { return seat.dataset.seat === anchor; });
    if (anchorIndex === -1 || count > row.length) return null;

    var firstStart = Math.min(anchorIndex, row.length - count);
    var lastStart = Math.max(0, anchorIndex - count + 1);
    for (var start = firstStart; start >= lastStart; start--) {
      var group = row.slice(start, start + count);
      var consecutive = group.every(function (seat, index) {
        return index === 0 || parseInt(seat.dataset.seat.slice(1), 10) ===
          parseInt(group[index - 1].dataset.seat.slice(1), 10) + 1;
      });
      var available = group.every(function (seat) {
        return !seat.classList.contains('booked');
      });
      if (consecutive && available) return group.map(function (seat) { return seat.dataset.seat; });
    }
    return null;
  }

  function selectGroup(anchor) {
    var count = seatCount();
    var group = groupFrom(anchor, count);
    if (!group) {
      toast('Could not find ' + count + ' consecutive available seats in that row. Try another seat or choose fewer seats.');
      return false;
    }
    selected.slice().forEach(function (label) { setSelected(label, false); });
    group.forEach(function (label) { setSelected(label, true); });
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
    var requested = seatCount();
    $('counter').innerHTML = '<b>' + sorted.length + '</b> / ' + requested;
    $('counter').classList.toggle('full', sorted.length === requested);
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
    var ok = sorted.length === requested;
    btn.disabled = !ok;
    btn.textContent = ok
      ? 'Confirm booking · ' + sorted.length + ' seat' + (sorted.length > 1 ? 's' : '')
      : 'Select ' + requested + ' seat' + (requested === 1 ? '' : 's');
  }

  hall.addEventListener('click', function (e) {
    var b = e.target.closest('button.seat');
    if (!b) return;
    selectGroup(b.dataset.seat);
    render();
  });

  $('seatCount').addEventListener('change', function () {
    if (selected.length) {
      var anchor = selected[0];
      if (!selectGroup(anchor)) {
        selected.slice().forEach(function (label) { setSelected(label, false); });
      }
    }
    render();
  });

  $('clearSel').addEventListener('click', function () {
    selected.slice().forEach(function (l) { setSelected(l, false); });
    render();
  });


  $('bookForm').addEventListener('submit', function (e) {
    if (selected.length !== seatCount()) {
      e.preventDefault();
      toast('Select exactly ' + seatCount() + ' seats.');
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
