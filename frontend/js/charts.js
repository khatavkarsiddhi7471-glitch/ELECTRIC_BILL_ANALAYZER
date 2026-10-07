/**
 * Chart.js reusable builder module with customized dark-mode themes
 */

const ChartColors = {
  blue: '#3b82f6',
  blueLight: 'rgba(59, 130, 246, 0.2)',
  emerald: '#10b981',
  emeraldLight: 'rgba(16, 185, 129, 0.2)',
  amber: '#f59e0b',
  amberLight: 'rgba(245, 158, 11, 0.2)',
  purple: '#8b5cf6',
  rose: '#f43f5e',
  cyan: '#06b6d4',
  text: '#94a3b8',
  grid: 'rgba(255, 255, 255, 0.06)'
};

function initTrendChart(canvasId, labels, unitsData, amountsData) {
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Units Consumed (kWh)',
          data: unitsData,
          borderColor: ChartColors.blue,
          backgroundColor: ChartColors.blueLight,
          fill: true,
          tension: 0.35,
          yAxisID: 'y'
        },
        {
          label: 'Bill Amount (₹)',
          data: amountsData,
          borderColor: ChartColors.emerald,
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          tension: 0.35,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: ChartColors.text, font: { family: 'Inter', size: 11 } } },
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        x: { grid: { color: ChartColors.grid }, ticks: { color: ChartColors.text } },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          grid: { color: ChartColors.grid },
          ticks: { color: ChartColors.blue },
          title: { display: true, text: 'Units (kWh)', color: ChartColors.blue }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { color: ChartColors.emerald },
          title: { display: true, text: 'Amount (₹)', color: ChartColors.emerald }
        }
      }
    }
  });
}

function initMonthlyBarChart(canvasId, labels, amountsData) {
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Total Bill (₹)',
        data: amountsData,
        backgroundColor: ChartColors.blue,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: '#1e293b' }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: ChartColors.text } },
        y: { grid: { color: ChartColors.grid }, ticks: { color: ChartColors.text } }
      }
    }
  });
}

function initApplianceDoughnut(canvasId, labels, dataValues) {
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;

  const palette = [
    '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316', '#64748b'
  ];

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: palette.slice(0, labels.length),
        borderWidth: 2,
        borderColor: '#111827'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: ChartColors.text, font: { family: 'Inter', size: 10 } }
        }
      }
    }
  });
}

function initStackedComposition(canvasId, labels, energyArr, fixedArr, dutyArr) {
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Energy Charges', data: energyArr, backgroundColor: '#3b82f6' },
        { label: 'Fixed Charges', data: fixedArr, backgroundColor: '#f59e0b' },
        { label: 'Duty / Tax', data: dutyArr, backgroundColor: '#10b981' }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: ChartColors.text } },
        y: { stacked: true, grid: { color: ChartColors.grid }, ticks: { color: ChartColors.text } }
      },
      plugins: {
        legend: { labels: { color: ChartColors.text, font: { size: 11 } } }
      }
    }
  });
}
