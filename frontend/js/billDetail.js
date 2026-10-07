/**
 * Bill Detail Page Controller
 */

let currentBill = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  const urlParams = new URLSearchParams(window.location.search);
  const billId = urlParams.get('id');

  if (!billId) {
    showToast('No bill specified', 'error');
    window.location.href = '/history.html';
    return;
  }

  await loadBillDetails(billId);
  setupPdfDownload(billId);
});

async function loadBillDetails(billId) {
  try {
    const res = await apiFetch(`/bills/${billId}`);
    currentBill = res.data;
    renderBill(currentBill);
  } catch (err) {
    console.error(err);
  }
}

function renderBill(b) {
  document.getElementById('bill-heading').innerText = `Bill Receipt — ${b.month}`;
  document.getElementById('detail-month').innerText = b.month;
  document.getElementById('detail-total').innerText = formatCurrency(b.calculated_total);

  const variance = (b.actual_total && b.calculated_total) ? (b.actual_total - b.calculated_total) : 0;
  if (Math.abs(variance) > 0.01) {
    document.getElementById('detail-variance').innerText = `Actual: ${formatCurrency(b.actual_total)} (Variance: ₹${variance.toFixed(2)})`;
  }

  document.getElementById('detail-source-badge').innerHTML = b.source === 'upload' 
    ? `<span class="badge badge-emerald">📄 OCR Uploaded Bill</span>` 
    : `<span class="badge badge-blue">✏️ Manual Meter Entry</span>`;

  document.getElementById('detail-prev').innerText = b.previous_reading || 0;
  document.getElementById('detail-curr').innerText = b.current_reading || 0;
  document.getElementById('detail-units').innerText = `${b.units} kWh`;
  
  const avgCost = b.units > 0 ? (b.calculated_total / b.units).toFixed(2) : '0.00';
  document.getElementById('detail-avg-cost').innerText = `₹${avgCost}/kWh`;

  // Slabs table
  const slabTbody = document.getElementById('detail-slab-tbody');
  const slabCharges = b.breakdown?.slab_charges || [];

  if (slabCharges.length === 0) {
    slabTbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No slab lines recorded.</td></tr>`;
  } else {
    slabTbody.innerHTML = slabCharges.map(s => `
      <tr>
        <td><strong>Slab ${s.range} Units</strong></td>
        <td>${s.units} kWh</td>
        <td>₹${s.rate.toFixed(2)}</td>
        <td style="text-align:right;"><strong>₹${s.amount.toFixed(2)}</strong></td>
      </tr>
    `).join('');
  }

  // Breakdown sub-charges
  document.getElementById('detail-energy').innerText = formatCurrency(b.breakdown?.energy_charge || 0);
  document.getElementById('detail-fixed').innerText = formatCurrency(b.breakdown?.fixed_charge || 0);
  document.getElementById('detail-duty').innerText = formatCurrency(b.breakdown?.duty || 0);
  
  const rebate = b.breakdown?.rebate || 0;
  if (rebate > 0) {
    document.getElementById('detail-rebate').innerText = `-₹${rebate.toFixed(2)}`;
    document.getElementById('detail-rebate-row').style.display = 'flex';
  } else {
    document.getElementById('detail-rebate-row').style.display = 'none';
  }

  document.getElementById('detail-calc-total').innerText = formatCurrency(b.calculated_total);
}

function setupPdfDownload(billId) {
  document.getElementById('download-bill-pdf')?.addEventListener('click', async () => {
    const btn = document.getElementById('download-bill-pdf');
    btn.disabled = true;
    btn.innerText = 'Generating PDF...';

    try {
      const blob = await apiFetch(`/reports/pdf?bill_id=${billId}`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Electricity_Bill_${currentBill?.month || 'receipt'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('PDF downloaded successfully!', 'success');
    } catch (err) {
      console.error(err);
    } finally {
      btn.disabled = false;
      btn.innerText = '📥 Download Month PDF Report';
    }
  });
}
