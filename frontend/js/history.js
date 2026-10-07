/**
 * History Page Controller
 */

let allBills = [];

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  await loadBills();
  setupFilters();
  setupEditModal();
  setupExportCSV();
});

async function loadBills(filters = {}) {
  const tbody = document.getElementById('bills-tbody');
  
  let query = '';
  if (filters.year) query += `?year=${filters.year}`;

  try {
    const res = await apiFetch(`/bills${query}`);
    allBills = res.data || [];
    renderBillsTable(allBills);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--accent-rose); padding:1.5rem;">Failed to load bills.</td></tr>`;
  }
}

function renderBillsTable(bills) {
  const tbody = document.getElementById('bills-tbody');

  if (bills.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:3rem 1rem; color:var(--text-muted);">
          No bill records found. <a href="/add-bill.html">Add a bill</a>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = bills.map(b => {
    const sourceBadge = b.source === 'upload' 
      ? `<span class="badge badge-emerald">📄 Upload</span>` 
      : `<span class="badge badge-blue">✏️ Manual</span>`;

    const variance = (b.actual_total && b.calculated_total) 
      ? (b.actual_total - b.calculated_total) 
      : 0;

    const varianceText = Math.abs(variance) > 1 
      ? `<span style="font-size:0.75rem; color:${variance > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)'};">(${variance > 0 ? '+' : ''}${variance.toFixed(1)})</span>` 
      : '';

    return `
      <tr>
        <td><strong>${b.month}</strong></td>
        <td>${b.previous_reading || 0} → ${b.current_reading || 0}</td>
        <td><span class="badge badge-blue" style="font-size:0.85rem;">${b.units} kWh</span></td>
        <td><strong>${formatCurrency(b.calculated_total)}</strong></td>
        <td>${formatCurrency(b.actual_total)} ${varianceText}</td>
        <td>${sourceBadge}</td>
        <td style="text-align:right;">
          <a href="/bill-detail.html?id=${b.id}" class="btn btn-secondary btn-sm" title="View Detailed Breakdown">🔍 Details</a>
          <button class="btn btn-secondary btn-sm" onclick="openEditModal('${b.id}')" title="Edit Bill">✏️</button>
          <button class="btn btn-danger btn-sm" onclick="deleteBill('${b.id}', '${b.month}')" title="Delete Bill">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

function setupFilters() {
  const searchInput = document.getElementById('filter-search');
  const yearSelect = document.getElementById('filter-year');
  const filterBtn = document.getElementById('apply-filters-btn');
  const clearBtn = document.getElementById('clear-filters-btn');

  filterBtn?.addEventListener('click', () => {
    const year = yearSelect.value;
    const term = searchInput.value.trim().toLowerCase();

    let filtered = allBills;
    if (year) {
      filtered = filtered.filter(b => b.month.startsWith(year));
    }
    if (term) {
      filtered = filtered.filter(b => b.month.toLowerCase().includes(term));
    }
    renderBillsTable(filtered);
  });

  clearBtn?.addEventListener('click', () => {
    searchInput.value = '';
    yearSelect.value = '';
    renderBillsTable(allBills);
  });
}

function openEditModal(billId) {
  const bill = allBills.find(b => b.id === billId);
  if (!bill) return;

  document.getElementById('edit-bill-id').value = bill.id;
  document.getElementById('edit-prev').value = bill.previous_reading || 0;
  document.getElementById('edit-curr').value = bill.current_reading || 0;
  document.getElementById('edit-units').value = bill.units || 0;
  document.getElementById('edit-actual').value = bill.actual_total || bill.calculated_total || 0;
  document.getElementById('edit-rebate').value = bill.breakdown?.rebate || 0;
  document.getElementById('edit-other').value = bill.breakdown?.other_charges || 0;

  document.getElementById('edit-modal').classList.add('show');
}

function setupEditModal() {
  const modal = document.getElementById('edit-modal');
  const closeBtn = document.getElementById('close-edit-modal');
  const form = document.getElementById('edit-bill-form');

  closeBtn?.addEventListener('click', () => modal.classList.remove('show'));

  // Auto-recalculate units when readings change in modal
  document.getElementById('edit-prev')?.addEventListener('input', updateEditUnits);
  document.getElementById('edit-curr')?.addEventListener('input', updateEditUnits);

  function updateEditUnits() {
    const p = parseFloat(document.getElementById('edit-prev').value) || 0;
    const c = parseFloat(document.getElementById('edit-curr').value) || 0;
    if (c >= p) {
      document.getElementById('edit-units').value = c - p;
    }
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const billId = document.getElementById('edit-bill-id').value;
    const prev = parseFloat(document.getElementById('edit-prev').value);
    const curr = parseFloat(document.getElementById('edit-curr').value);
    const units = parseFloat(document.getElementById('edit-units').value);
    const actual_total = parseFloat(document.getElementById('edit-actual').value);
    const rebate = parseFloat(document.getElementById('edit-rebate').value) || 0;
    const other_charges = parseFloat(document.getElementById('edit-other').value) || 0;

    try {
      await apiFetch(`/bills/${billId}`, {
        method: 'PUT',
        body: JSON.stringify({
          previous_reading: prev,
          current_reading: curr,
          units,
          actual_total,
          rebate,
          other_charges
        })
      });

      modal.classList.remove('show');
      showToast('Bill updated and recalculated!', 'success');
      await loadBills();
    } catch (err) {
      console.error(err);
    }
  });
}

async function deleteBill(billId, month) {
  if (!confirm(`Are you sure you want to delete the bill for ${month}?`)) {
    return;
  }

  try {
    await apiFetch(`/bills/${billId}`, { method: 'DELETE' });
    showToast(`Bill for ${month} deleted`, 'info');
    await loadBills();
  } catch (err) {
    console.error(err);
  }
}

function setupExportCSV() {
  document.getElementById('export-csv-btn')?.addEventListener('click', () => {
    if (allBills.length === 0) {
      showToast('No bills to export', 'warning');
      return;
    }

    const headers = ['Month', 'Previous Reading', 'Current Reading', 'Units (kWh)', 'Calculated Amount (INR)', 'Actual Amount (INR)', 'Energy Charge', 'Fixed Charge', 'Duty', 'Source'];
    const rows = allBills.map(b => [
      b.month,
      b.previous_reading || 0,
      b.current_reading || 0,
      b.units || 0,
      b.calculated_total || 0,
      b.actual_total || 0,
      b.breakdown?.energy_charge || 0,
      b.breakdown?.fixed_charge || 0,
      b.breakdown?.duty || 0,
      b.source || 'manual'
    ]);

    let csvContent = 'data:text/csv;charset=utf-8,' 
      + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Electricity_Bills_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  });
}
