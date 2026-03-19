/* Warehouse Replenishment App — JS helpers */

/* ── Breakdown toggle (pick list) ──────────────────────── */
function toggleBreakdown(targetId) {
    var row = document.getElementById(targetId);
    if (!row) return;
    var btn = document.querySelector('[data-target="' + targetId + '"]');
    if (row.style.display === 'none') {
        row.style.display = '';
        if (btn) btn.textContent = '\u2212';
    } else {
        row.style.display = 'none';
        if (btn) btn.textContent = '+';
    }
}

/* ── Toast notifications ───────────────────────────────── */
var _toastEl = null;
var _toastTimer = null;

function showToast(message, type) {
    if (!_toastEl) {
        _toastEl = document.createElement('div');
        _toastEl.className = 'toast';
        document.body.appendChild(_toastEl);
    }
    clearTimeout(_toastTimer);
    _toastEl.textContent = message;
    _toastEl.className = 'toast toast-' + (type || 'success') + ' show';
    _toastTimer = setTimeout(function() {
        _toastEl.classList.remove('show');
    }, 2500);
}

/* ── Auto-dismiss flash alerts ─────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('.alert-success, .alert-info');
    for (var i = 0; i < alerts.length; i++) {
        (function(alert) {
            setTimeout(function() {
                alert.style.transition = 'opacity 0.4s';
                alert.style.opacity = '0';
                setTimeout(function() { alert.style.display = 'none'; }, 400);
            }, 4000);
        })(alerts[i]);
    }
});
