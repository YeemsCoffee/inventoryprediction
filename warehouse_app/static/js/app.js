// Warehouse Replenishment App - V1 JS

function toggleBreakdown(targetId) {
    var row = document.getElementById(targetId);
    if (!row) return;
    if (row.style.display === 'none') {
        row.style.display = '';
    } else {
        row.style.display = 'none';
    }
}
