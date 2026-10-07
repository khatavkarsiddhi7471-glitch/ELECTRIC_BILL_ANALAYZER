/**
 * Dashboard Controller
 */

let trendChartInstance = null;
let barChartInstance = null;
let applianceChartInstance = null;
let stackedChartInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  const user = TokenManager.getUser();
  if (user && user.name) {
    document.getElementById('welcome-msg').innerText = `Welcome back, ${user.name} • Monitoring your energy consumption`;
  }

  await loadDashboardData();
  setupDownloadButton();
});

async function loadDashboardData() {
  try {
    // 1. Fetch Summary
    const summaryRes = await apiFetch('/analytics/summary');
    const summary = summaryRes.data;

    if (summary.total_bills === 0) {
      document.getElementById('empty-state').style.display = 'block';
      document.getElementById('kpi-section').style.opacity = '0.4';
    } else {
      document.getElementById('empty-state').style.display = 'none';
      document.getElementById('kpi-units').innerText = `${summary.latest_units} kWh`;
      document.getElementById('kpi-month-label').innerText = `Month: ${summary.latest_month}`;
      document.getElementById('kpi-amount').innerText = formatCurrency(summary.latest_amount);
      
      const momSign = summary.mom_cost_change_pct > 0 ? '+' : '';
      const momClass = summary.mom_cost_change_pct > 0 ? 'text-rose' : 'text-emerald';
      document.getElementById('kpi-mom-cost').innerHTML = `<span class="${momClass}">${momSign}${summary.mom_cost_change_pct}% MoM change</span>`;
      
      document.getElementById('kpi-rate').innerText = `₹${summary.avg_cost_per_kwh.toFixed(2)}/kWh`;
      document.getElementById('kpi-total-bills').innerText = `Based on ${summary.total_bills} bill cycles`;
    }

    // 2. Fetch Charts Datasets
    const chartsRes = await apiFetch('/analytics/charts');
    const chartData = chartsRes.data;

    // Destroy existing instances if any
    trendChartInstance?.destroy();
    barChartInstance?.destroy();
    applianceChartInstance?.destroy();
    stackedChartInstance?.destroy();

    if (chartData.trend.labels.length > 0) {
      trendChartInstance = initTrendChart('trendChart', chartData.trend.labels, chartData.trend.units, chartData.trend.amounts);
      barChartInstance = initMonthlyBarChart('barChart', chartData.trend.labels, chartData.trend.amounts);
      stackedChartInstance = initStackedComposition(
        'stackedChart',
        chartData.composition.labels,
        chartData.composition.energy_charge,
        chartData.composition.fixed_charge,
        chartData.composition.duty
      );
    }

    if (chartData.appliances.labels.length > 0) {
      applianceChartInstance = initApplianceDoughnut('applianceChart', chartData.appliances.labels, chartData.appliances.kwh);
    } else {
      const appCanvas = document.getElementById('applianceChart');
      if (appCanvas && appCanvas.parentElement) {
        appCanvas.parentElement.innerHTML = '<div style="display:flex; height:100%; align-items:center; justify-content:center; color:var(--text-muted); font-size:0.85rem;">No appliances added yet. <a href="/appliances.html" style="margin-left:6px;">Add appliances</a></div>';
      }
    }

    // 3. Fetch Prediction
    const predRes = await apiFetch('/predict');
    const pred = predRes.data;
    renderForecastCard(pred);

    // 4. Fetch Savings Tips
    const tipsRes = await apiFetch('/tips');
    renderTopTips(tipsRes.data.tips || []);

  } catch (err) {
    console.error('Error loading dashboard:', err);
  }
}

function renderForecastCard(pred) {
  const container = document.getElementById('forecast-content');
  const kpiPred = document.getElementById('kpi-prediction');
  const badge = document.getElementById('forecast-badge');

  if (pred.status === 'insufficient_data') {
    kpiPred.innerText = '3+ bills needed';
    badge.innerText = 'Need Data';
    badge.className = 'badge badge-amber';
    container.innerHTML = `
      <div style="background:rgba(245, 158, 11, 0.08); border:1px dashed var(--accent-amber); border-radius:var(--radius-md); padding:1rem;">
        <p style="color:var(--text-primary); font-weight:600; font-size:0.95rem;">⚡ Unlock ML Prediction</p>
        <p style="color:var(--text-secondary); font-size:0.85rem; margin-top:0.3rem;">${pred.message}</p>
        <p style="font-size:0.8rem; color:var(--text-muted); margin-top:0.5rem;">Current data points: ${pred.data_points_count}/3</p>
      </div>
    `;
    return;
  }

  kpiPred.innerText = formatCurrency(pred.predicted_amount);
  badge.innerText = pred.method;
  badge.className = 'badge badge-emerald';

  const range = pred.confidence_range;
  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem;">
      <div>
        <div style="font-size:1.8rem; font-weight:700; color:var(--accent-blue);">${formatCurrency(pred.predicted_amount)}</div>
        <div style="font-size:0.85rem; color:var(--text-secondary);">Estimated next month bill (~${pred.predicted_units} kWh)</div>
      </div>
      <span class="badge badge-blue">±${range.margin_percent}% Confidence</span>
    </div>

    <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:0.85rem; font-size:0.85rem;">
      <div style="display:flex; justify-content:space-between; margin-bottom:0.35rem;">
        <span style="color:var(--text-secondary);">Forecast Range:</span>
        <strong style="color:var(--accent-emerald);">${formatCurrency(range.amount_range[0])} — ${formatCurrency(range.amount_range[1])}</strong>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span style="color:var(--text-secondary);">Model Method:</span>
        <span style="color:var(--text-primary);">${pred.method}</span>
      </div>
    </div>
  `;
}

function renderTopTips(tips) {
  const container = document.getElementById('top-tips-list');
  if (!tips || tips.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem;">No recommendations generated yet.</p>';
    return;
  }

  const top3 = tips.slice(0, 3);
  container.innerHTML = top3.map(t => `
    <div style="padding:0.75rem; border-radius:var(--radius-md); background:rgba(255,255,255,0.02); border:1px solid var(--border-color); margin-bottom:0.75rem;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong style="font-size:0.9rem; color:var(--text-primary);">${t.title}</strong>
        <span class="badge badge-emerald">Save ~${formatCurrency(t.estimated_monthly_savings_inr)}/mo</span>
      </div>
      <p style="color:var(--text-secondary); font-size:0.8rem; margin-top:0.3rem;">${t.tip}</p>
    </div>
  `).join('');
}

function setupDownloadButton() {
  document.getElementById('download-report-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('download-report-btn');
    btn.disabled = true;
    btn.innerText = '⏳ Generating PDF...';

    try {
      const blob = await apiFetch('/reports/pdf');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Electricity_Report_${new Date().toISOString().slice(0, 7)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('PDF report downloaded successfully!', 'success');
    } catch (err) {
      console.error(err);
    } finally {
      btn.disabled = false;
      btn.innerText = '📥 Download PDF Report';
    }
  });
}
