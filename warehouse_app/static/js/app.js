// Warehouse Replenishment App - V2 JS

function toggleBreakdown(targetId) {
    var row = document.getElementById(targetId);
    if (!row) return;
    var btn = document.querySelector('[data-target="' + targetId + '"]');
    if (row.style.display === 'none') {
        row.style.display = '';
        if (btn) btn.textContent = '\u2212';  // minus sign
    } else {
        row.style.display = 'none';
        if (btn) btn.textContent = '+';
    }
}

// Keyboard shortcut: Ctrl+P to print (override browser default with window.print)
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        // Let browser handle natively — just ensure print styles apply
    }
});
