/**
 * applianceEstimator.js
 * Estimates appliance-wise energy consumption from total kWh consumed in a bill.
 * Uses typical Indian household usage profiles.
 */

// ─── Appliance Catalog ────────────────────────────────────────────────────────
// Each appliance has:
//  name, icon, watts (typical), typical_hours_per_day, days_per_month,
//  color (CSS var or hex), category share weight (relative to others)
const APPLIANCE_PROFILES = [
  {
    name: 'Air Conditioner',
    icon: '❄️',
    watts: 1500,
    hours: 6,
    days: 25,
    color: '#3b82f6',
    category: 'cooling'
  },
  {
    name: 'Refrigerator',
    icon: '🧊',
    watts: 150,
    hours: 24,
    days: 30,
    color: '#06b6d4',
    category: 'cooling'
  },
  {
    name: 'Water Heater (Geyser)',
    icon: '🚿',
    watts: 2000,
    hours: 1,
    days: 25,
    color: '#f59e0b',
    category: 'heating'
  },
  {
    name: 'Washing Machine',
    icon: '🫧',
    watts: 500,
    hours: 1,
    days: 15,
    color: '#8b5cf6',
    category: 'laundry'
  },
  {
    name: 'Television',
    icon: '📺',
    watts: 120,
    hours: 6,
    days: 30,
    color: '#10b981',
    category: 'entertainment'
  },
  {
    name: 'Ceiling Fans',
    icon: '🌀',
    watts: 75,
    hours: 10,
    days: 30,
    color: '#64748b',
    category: 'cooling'
  },
  {
    name: 'Lighting (LED)',
    icon: '💡',
    watts: 40,
    hours: 6,
    days: 30,
    color: '#fbbf24',
    category: 'lighting'
  },
  {
    name: 'Microwave / OTG',
    icon: '🍳',
    watts: 1200,
    hours: 0.5,
    days: 25,
    color: '#f97316',
    category: 'kitchen'
  },
  {
    name: 'Iron',
    icon: '👔',
    watts: 1000,
    hours: 0.5,
    days: 15,
    color: '#a78bfa',
    category: 'laundry'
  },
  {
    name: 'Laptop / Computer',
    icon: '💻',
    watts: 80,
    hours: 5,
    days: 25,
    color: '#60a5fa',
    category: 'electronics'
  },
  {
    name: 'Water Pump / Motor',
    icon: '💧',
    watts: 750,
    hours: 1.5,
    days: 30,
    color: '#22d3ee',
    category: 'utilities'
  },
  {
    name: 'Mixer / Grinder',
    icon: '⚙️',
    watts: 750,
    hours: 0.25,
    days: 25,
    color: '#fb923c',
    category: 'kitchen'
  }
];

/**
 * Computes per-appliance kWh from total bill kWh using proportional distribution.
 * @param {number} totalKwh  – Total units from the bill
 * @param {number} ratePerKwh – Avg rate used to compute cost per appliance
 * @returns {Array} – Sorted appliance breakdown array
 */
function estimateApplianceUsage(totalKwh, ratePerKwh = 8.5) {
  if (!totalKwh || totalKwh <= 0) return [];

  // Step 1: Compute raw monthly kWh for each appliance
  const raw = APPLIANCE_PROFILES.map(a => ({
    ...a,
    rawKwh: (a.watts * a.hours * a.days) / 1000
  }));

  const totalRaw = raw.reduce((s, a) => s + a.rawKwh, 0);

  // Step 2: Normalise to actual bill kWh
  const result = raw.map(a => {
    const share = totalRaw > 0 ? a.rawKwh / totalRaw : 0;
    const kwh   = parseFloat((share * totalKwh).toFixed(2));
    const cost  = parseFloat((kwh * ratePerKwh).toFixed(2));
    return {
      ...a,
      kwh,
      cost,
      sharePct: parseFloat((share * 100).toFixed(1))
    };
  });

  // Step 3: Sort by descending kWh
  return result.sort((a, b) => b.kwh - a.kwh);
}

/**
 * Renders appliance tiles into a target grid element.
 * @param {string} gridId    – ID of the <div> to render tiles into
 * @param {number} totalKwh  – From bill
 * @param {number} totalCost – Total bill amount (for cost ratio)
 * @param {string} labelId   – ID of the badge label to update with kWh
 * @param {string} sectionId – ID of the wrapper section to show/hide
 */
function renderApplianceTiles(gridId, totalKwh, totalCost, labelId, sectionId) {
  if (!totalKwh || totalKwh <= 0) return;

  const section = document.getElementById(sectionId);
  const grid    = document.getElementById(gridId);
  const label   = document.getElementById(labelId);

  if (!section || !grid) return;

  // Derive avg cost rate
  const avgRate = totalKwh > 0 ? (totalCost / totalKwh) : 8.5;
  const breakdown = estimateApplianceUsage(totalKwh, avgRate);

  if (label) label.innerText = totalKwh.toFixed(1);
  section.style.display = 'block';

  grid.innerHTML = breakdown.map(a => `
    <div class="app-tile" style="--tile-color:${a.color};">
      <div class="app-icon">${a.icon}</div>
      <div class="app-name">${a.name}</div>
      <div class="app-kwh">${a.kwh} kWh</div>
      <div class="app-cost">₹${a.cost.toFixed(0)}</div>
      <div class="app-bar-row">
        <div class="app-bar-fill" style="width:${a.sharePct}%;"></div>
      </div>
      <div class="app-pct">${a.sharePct}% of bill</div>
    </div>
  `).join('');
}
