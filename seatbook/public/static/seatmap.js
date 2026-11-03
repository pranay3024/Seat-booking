(function () {
  var cfg = window.SEATMAP || { max: 50, min: 1, preselect: [] };
  var hall = document.getElementById('hall');
  var selected = [];

  var $ = function (id) { return document.getElementById(id); };

  if (!hall) return;

  function toast(msg) {
    var box = $('toasts');
    if (!box) return;
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
    var seatCountEl = $('seatCount');
    return seatCountEl ? parseInt(seatCountEl.value, 10) : 1;
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

  function selectFromAnchor(anchor, section, block) {
    var count = seatCount();
    var seats = Array.prototype.slice.call(hall.querySelectorAll('.seat-grid .seat[data-seat]'))
      .filter(function (seat) {
        return seat.dataset.sec === section && seat.dataset.block === block;
      })
      .sort(function (a, b) { return rowOrder(a.dataset.seat) - rowOrder(b.dataset.seat); });
    var anchorIndex = seats.findIndex(function (seat) { return seat.dataset.seat === anchor; });
    if (anchorIndex === -1) return;

    var available = seats.slice(anchorIndex).filter(function (seat) {
      return !seat.classList.contains('booked');
    }).slice(0, count);
    available.forEach(function (seat) { setSelected(seat.dataset.seat, true); });
    if (available.length < count) {
      toast('Only ' + available.length + ' seats are available in this block from there onward. Select more seats manually or choose fewer.');
    }
  }

  function toggleSeat(label) {
    if (selected.indexOf(label) !== -1) {
      setSelected(label, false);
      return false;
    }
    if (selected.length >= seatCount()) {
      toast('Deselect a seat first, or increase the number of seats.');
      return false;
    }
    return setSelected(label, true);
  }

  function render() {
    var sorted = selected.slice().sort(function (a, b) { return rowOrder(a) - rowOrder(b); });
    var seatsInput = $('seatsInput');
    if (seatsInput) seatsInput.value = sorted.join(',');

    var nStallEl = $('nStall');
    var nBalcEl = $('nBalc');
    var totalEl = $('tTotal');
    var counterEl = $('counter');
    var mCountEl = $('mCount');
    var mobileBarEl = $('mobileBar');
    var chips = $('chips');
    var chipsEmpty = $('chipsEmpty');
    var clearSel = $('clearSel');
    var submitBtn = $('submitBtn');

    var nStall = 0, nBalc = 0;
    sorted.forEach(function (l) {
      var b = btnFor(l);
      if (b && b.dataset.sec === 'balcony') nBalc++; else nStall++;
    });
    if (nStallEl) nStallEl.textContent = nStall;
    if (nBalcEl) nBalcEl.textContent = nBalc;
    if (totalEl) totalEl.textContent = sorted.length;

    var requested = seatCount();
    if (counterEl) {
      counterEl.innerHTML = '<b>' + sorted.length + '</b> / ' + requested;
      counterEl.classList.toggle('full', sorted.length === requested);
    }
    if (mCountEl) mCountEl.textContent = sorted.length;
    if (mobileBarEl) mobileBarEl.classList.toggle('show', sorted.length > 0);

    if (chips) {
      chips.querySelectorAll('.chip').forEach(function (c) { c.remove(); });
    }
    if (chipsEmpty) {
      chipsEmpty.hidden = sorted.length > 0;
      chipsEmpty.textContent = sorted.length ? '' : 'Click an available seat to select your group.';
    }
    if (clearSel) clearSel.hidden = sorted.length === 0;

    if (chips) {
      sorted.forEach(function (l) {
        var c = document.createElement('button');
        c.type = 'button';
        c.className = 'chip';
        c.title = 'Remove ' + l;
        c.innerHTML = l + ' <span aria-hidden="true">?</span>';
        c.addEventListener('click', function () { setSelected(l, false); render(); });
        chips.appendChild(c);
      });
    }

    if (submitBtn) {
      var ok = sorted.length === requested;
      submitBtn.disabled = !ok;
      submitBtn.textContent = ok
        ? 'Confirm booking ? ' + sorted.length + ' seat' + (sorted.length > 1 ? 's' : '')
        : 'Select ' + (requested - sorted.length) + ' more seat' + (requested - sorted.length === 1 ? '' : 's');
    }
  }

  hall.addEventListener('click', function (e) {
    var b = e.target.closest('button.seat');
    if (!b) return;
    if (selected.length === 0) {
      selectFromAnchor(b.dataset.seat, b.dataset.sec, b.dataset.block);
    } else {
      toggleSeat(b.dataset.seat);
    }
    render();
  });

  var seatCountEl = $('seatCount');
  if (seatCountEl) {
    seatCountEl.addEventListener('change', function () {
      selected.slice().forEach(function (label) { setSelected(label, false); });
      render();
    });
  }

  var clearSel = $('clearSel');
  if (clearSel) {
    clearSel.addEventListener('click', function () {
      selected.slice().forEach(function (l) { setSelected(l, false); });
      render();
    });
  }

  var bookForm = $('bookForm');
  if (bookForm) {
    bookForm.addEventListener('submit', function (e) {
      if (selected.length !== seatCount()) {
        e.preventDefault();
        toast('Select exactly ' + seatCount() + ' seats.');
        return;
      }
      var submitBtn = $('submitBtn');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Booking?';
      }
    });
  }

  var zoom = 1;
  var scroll = $('hallScroll');
  function fit() {
    hall.style.setProperty('--z', 1);
    var natural = hall.scrollWidth;
    var avail = scroll ? (scroll.clientWidth - 8) : 900;
    if (!natural) return;
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

  hall.querySelectorAll('button.seat').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });

  (cfg.preselect || []).forEach(function (l) { setSelected(l, true); });
  if (window.innerWidth > 1100) fit();
  render();
})();
