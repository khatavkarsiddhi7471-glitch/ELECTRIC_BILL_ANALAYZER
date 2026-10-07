/**
 * Appliances Controller
 */

let catalogPresets = [];

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  await loadPresets();
  await loadAppliances();
  setupLiveAppliancePreview();
  setupFormSubmit();
});

async function loadPresets() {
  try {
    const res = await apiFetch('/appliances/catalog');
    catalogPresets = res.data || [];
    
    const select = document.getElementById('preset-select');
    if (!select) return;

    catalogPresets.forEach((p, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.innerText = `${p.name} (${p.watts}W)`;
      select.appendChild(opt);
    });

    select.addEventListener('change', () => {
      const selectedIdx = select.value;
      if (selectedIdx === '') return;
      const p = catalogPresets[parseInt(selectedIdx, 10)];
      if (p) {
        document.getElementById('app-name').value = p.name;
        document.getElementById('app-watts').value = p.watts;
        document.getElementById('app-hours').value = p.typical_hours;
        document.getElementById('app-qty').value = 1;
        document.getElementById('app-days').value = 30;
        updatePreview();
      }
    });
  } catch (err) {
    console.error('Error loading preset catalog:', err);
  }
}

async function loadAppliances() {
  try {
    const res = await apiFetch('/appliances/summary');
    const data = res.data;

    document.getElementById('app-total-count').innerText = data.total_appliances || 0;
    document.getElementById('app-total-kwh').innerText = `${data.total_estimated_kwh || 0} kWh`;
    document.getElementById('app-total-cost').innerText = formatCurrency(data.total_estimated_cost || 0);
    
    if (data.top_consumer) {
      document.getElementById('app-top-consumer').innerText = data.top_consumer.name;
      document.getElementById('app-top-share').innerText = `${data.top_consumer.share_percent}% of total usage`;
    } else {
      document.getElementById('app-top-consumer').innerText = '--';
      document.getElementById('app-top-share').innerText = 'No data';
    }

    renderTable(data.rankings || []);
  } catch (err) {
    console.error('Error loading appliances:', err);
  }
}

function renderTable(rankings) {
  const tbody = document.getElementById('app-tbody');
  if (rankings.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center; padding:3rem 1rem; color:var(--text-muted);">
          No appliances added yet. Add appliances using the form on the left!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = rankings.map(a => {
    const highBadge = a.is_high_consumer 
      ? `<span class="badge badge-rose" style="margin-left:6px;">High Load</span>` 
      : '';

    return `
      <tr>
        <td><strong>${a.name}</strong> ${highBadge}</td>
        <td style="color:var(--text-secondary); font-size:0.85rem;">${a.watts}W • ${a.hours_per_day || ''}h/day</td>
        <td><strong style="color:var(--accent-blue);">${a.monthly_kwh} kWh</strong></td>
        <td><strong style="color:var(--accent-emerald);">${formatCurrency(a.estimated_cost)}</strong></td>
        <td>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <div style="flex:1; background:rgba(255,255,255,0.06); height:6px; border-radius:3px; overflow:hidden; min-width:50px;">
              <div style="background:var(--accent-blue); width:${a.share_percent}%; height:100%;"></div>
            </div>
            <span style="font-size:0.8rem; font-weight:600;">${a.share_percent}%</span>
          </div>
        </td>
        <td style="text-align:right;">
          <button class="btn btn-danger btn-sm" onclick="deleteAppliance('${a.id}', '${a.name}')" title="Delete">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

function setupLiveAppliancePreview() {
  const wattsIn = document.getElementById('app-watts');
  const hoursIn = document.getElementById('app-hours');
  const daysIn = document.getElementById('app-days');
  const qtyIn = document.getElementById('app-qty');

  [wattsIn, hoursIn, daysIn, qtyIn].forEach(el => el?.addEventListener('input', updatePreview));
}

function updatePreview() {
  const watts = parseFloat(document.getElementById('app-watts').value) || 0;
  const hours = parseFloat(document.getElementById('app-hours').value) || 0;
  const days = parseFloat(document.getElementById('app-days').value) || 0;
  const qty = parseInt(document.getElementById('app-qty').value, 10) || 1;

  const kwh = (watts * hours * days * qty) / 1000.0;
  const cost = kwh * 8.5; // marginal avg rate

  document.getElementById('preview-app-kwh').innerText = `${kwh.toFixed(1)} kWh/mo`;
  document.getElementById('preview-app-cost').innerText = formatCurrency(cost);
}

function setupFormSubmit() {
  const form = document.getElementById('appliance-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('add-app-btn');
    btn.disabled = true;

    const name = document.getElementById('app-name').value.trim();
    const watts = parseFloat(document.getElementById('app-watts').value);
    const hours_per_day = parseFloat(document.getElementById('app-hours').value);
    const days_per_month = parseInt(document.getElementById('app-days').value, 10) || 30;
    const quantity = parseInt(document.getElementById('app-qty').value, 10) || 1;

    try {
      await apiFetch('/appliances', {
        method: 'POST',
        body: JSON.stringify({ name, watts, hours_per_day, days_per_month, quantity })
      });

      showToast(`Added "${name}" successfully`, 'success');
      form.reset();
      document.getElementById('app-qty').value = 1;
      document.getElementById('app-days').value = 30;
      updatePreview();
      await loadAppliances();
    } catch (err) {
      console.error(err);
    } finally {
      btn.disabled = false;
    }
  });
}

async function deleteAppliance(appId, name) {
  if (!confirm(`Remove "${name}" from appliance inventory?`)) return;

  try {
    await apiFetch(`/appliances/${appId}`, { method: 'DELETE' });
    showToast(`Removed "${name}"`, 'info');
    await loadAppliances();
  } catch (err) {
    console.error(err);
  }
}
