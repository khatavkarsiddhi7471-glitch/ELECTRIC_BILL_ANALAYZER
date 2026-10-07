/**
 * Tariff Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  await loadTariffs();
  setupFormSubmit();
});

async function loadTariffs() {
  const container = document.getElementById('tariffs-list');
  try {
    const res = await apiFetch('/tariffs');
    const tariffs = res.data || [];

    if (tariffs.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);">No tariff profiles available.</p>';
      return;
    }

    container.innerHTML = tariffs.map(t => {
      const activeBadge = t.is_active 
        ? `<span class="badge badge-emerald">Active Profile</span>` 
        : `<button class="btn btn-secondary btn-sm" onclick="setActiveTariff('${t.id}')">Set Active</button>`;

      const slabsSummary = (t.slabs || []).map(s => `
        <span style="display:inline-block; margin-right:8px; background:rgba(255,255,255,0.04); padding:2px 8px; border-radius:4px; font-size:0.8rem;">
          ${s.from}-${s.to || '∞'}: <strong>₹${s.rate}/u</strong>
        </span>
      `).join('');

      return `
        <div style="background:rgba(255,255,255,0.02); border:1px solid ${t.is_active ? 'var(--accent-blue)' : 'var(--border-color)'}; border-radius:var(--radius-md); padding:1.25rem; margin-bottom:1rem;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
            <div>
              <h4 style="font-size:1.1rem; color:var(--text-primary);">${t.name}</h4>
              <p style="color:var(--text-muted); font-size:0.85rem;">Distributor: ${t.distributor || 'General'} • Fixed: ₹${t.fixed_charge} • Duty: ${t.duty_percent}%</p>
            </div>
            <div>${activeBadge}</div>
          </div>

          <div style="margin-top:0.5rem;">
            <div style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:4px;">Slabs Configuration:</div>
            <div>${slabsSummary}</div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading tariffs:', err);
  }
}

async function setActiveTariff(tariffId) {
  try {
    await apiFetch('/tariffs/active', {
      method: 'PUT',
      body: JSON.stringify({ tariff_id: tariffId })
    });
    showToast('Active tariff profile updated!', 'success');
    await loadTariffs();
  } catch (err) {
    console.error(err);
  }
}

function setupFormSubmit() {
  const form = document.getElementById('custom-tariff-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('t-name').value.trim();
    const distributor = document.getElementById('t-distributor').value.trim();
    const fixed_charge = parseFloat(document.getElementById('t-fixed').value);
    const duty_percent = parseFloat(document.getElementById('t-duty').value);

    const slab1_rate = parseFloat(document.getElementById('t-slab1-rate').value);
    const slab2_rate = parseFloat(document.getElementById('t-slab2-rate').value);
    const slab3_rate = parseFloat(document.getElementById('t-slab3-rate').value);

    const slabs = [
      { from: 0, to: 100, rate: slab1_rate },
      { from: 101, to: 300, rate: slab2_rate },
      { from: 301, to: null, rate: slab3_rate }
    ];

    try {
      await apiFetch('/tariffs', {
        method: 'POST',
        body: JSON.stringify({
          name,
          distributor,
          fixed_charge,
          duty_percent,
          slabs
        })
      });

      showToast(`Custom tariff "${name}" created!`, 'success');
      form.reset();
      await loadTariffs();
    } catch (err) {
      console.error(err);
    }
  });
}
