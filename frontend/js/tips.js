/**
 * Tips Page Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  await loadTips();
});

async function loadTips() {
  try {
    const res = await apiFetch('/tips');
    const data = res.data;

    document.getElementById('total-savings-inr').innerText = formatCurrency(data.total_potential_monthly_savings_inr);
    document.getElementById('total-savings-kwh').innerText = `${data.total_potential_kwh_savings} kWh / month`;

    const container = document.getElementById('tips-grid');
    const tips = data.tips || [];

    if (tips.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);">No recommendations available at this moment.</p>';
      return;
    }

    container.innerHTML = tips.map(t => {
      let priorityClass = 'badge-blue';
      if (t.priority === 'Critical') priorityClass = 'badge-rose';
      if (t.priority === 'High') priorityClass = 'badge-amber';

      return `
        <div class="card" style="display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
              <span class="badge ${priorityClass}">${t.priority} Priority</span>
              <span class="badge badge-emerald">Save ~${formatCurrency(t.estimated_monthly_savings_inr)}/mo</span>
            </div>
            <h3 style="font-size:1.15rem; margin-bottom:0.5rem; color:var(--text-primary);">${t.title}</h3>
            <p style="color:var(--text-secondary); font-size:0.9rem; line-height:1.5;">${t.tip}</p>
          </div>

          <div style="margin-top:1.25rem; padding-top:0.75rem; border-top:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:var(--text-muted);">
            <span>Category: <strong>${t.category}</strong></span>
            <span>Tag: <strong style="color:var(--accent-cyan);">${t.tag}</strong></span>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading tips:', err);
  }
}
