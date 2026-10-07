/**
 * Analysis Page Controller
 */

let analysisChartInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  await loadAnalytics();
  setupSimulator();
});

async function loadAnalytics() {
  try {
    const sumRes = await apiFetch('/analytics/summary');
    const s = sumRes.data;

    document.getElementById('ana-avg-units').innerText = `${s.avg_monthly_units} kWh`;
    document.getElementById('ana-avg-bill').innerText = `Avg ${formatCurrency(s.avg_monthly_bill)} / month`;

    if (s.highest_month) {
      document.getElementById('ana-high-units').innerText = `${s.highest_month.units} kWh`;
      document.getElementById('ana-high-month').innerText = `${s.highest_month.month} (${formatCurrency(s.highest_month.amount)})`;
    }

    if (s.lowest_month) {
      document.getElementById('ana-low-units').innerText = `${s.lowest_month.units} kWh`;
      document.getElementById('ana-low-month').innerText = `${s.lowest_month.month} (${formatCurrency(s.lowest_month.amount)})`;
    }

    document.getElementById('ana-effective-rate').innerText = `₹${s.avg_cost_per_kwh.toFixed(2)}/kWh`;

    // Load Charts
    const chartRes = await apiFetch('/analytics/charts');
    const chartData = chartRes.data;
    
    analysisChartInstance?.destroy();
    if (chartData.trend.labels.length > 0) {
      analysisChartInstance = initTrendChart('analysisTrendChart', chartData.trend.labels, chartData.trend.units, chartData.trend.amounts);
    }
  } catch (err) {
    console.error('Error loading analytics:', err);
  }
}

function setupSimulator() {
  const unitsInput = document.getElementById('sim-units');
  let debounceTimer;

  async function calculateSim() {
    const units = parseFloat(unitsInput.value) || 0;
    try {
      const res = await apiFetch('/bills/calculate', {
        method: 'POST',
        body: JSON.stringify({ units })
      });

      const d = res.data;
      const linesEl = document.getElementById('sim-lines');
      linesEl.innerHTML = d.lines.map(l => `
        <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem; font-size:0.8rem; color:var(--text-secondary);">
          <span>Slab ${l.range} (${l.units}u @ ₹${l.rate}):</span>
          <strong>₹${l.amount.toFixed(2)}</strong>
        </div>
      `).join('') + `
        <div style="display:flex; justify-content:space-between; margin-top:0.4rem; font-size:0.8rem; color:var(--text-secondary);">
          <span>Fixed + Duty (${d.duty_percent}%):</span>
          <span>${formatCurrency(d.fixed_charge + d.duty)}</span>
        </div>
      `;

      document.getElementById('sim-total').innerText = formatCurrency(d.total);
    } catch (e) {
      console.error(e);
    }
  }

  unitsInput?.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(calculateSim, 250);
  });

  calculateSim();
}
