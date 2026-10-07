/**
 * Profile Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!TokenManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  await loadProfile();
  setupForm();
});

async function loadProfile() {
  try {
    const res = await apiFetch('/auth/me');
    const u = res.data;

    document.getElementById('prof-name').value = u.name || '';
    document.getElementById('prof-email').value = u.email || '';
    document.getElementById('prof-consumer').value = u.consumer_number || '';
    document.getElementById('prof-distributor').value = u.distributor || 'MSEDCL';

    const s = u.settings || {};
    document.getElementById('prof-unit-threshold').value = s.monthly_unit_threshold ?? 200;
    document.getElementById('prof-budget').value = s.monthly_budget ?? 1500;
    document.getElementById('prof-spike-pct').value = s.alert_increase_pct ?? 20;
  } catch (err) {
    console.error('Error loading profile:', err);
  }
}

function setupForm() {
  const form = document.getElementById('profile-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('save-profile-btn');
    btn.disabled = true;

    const name = document.getElementById('prof-name').value.trim();
    const consumer_number = document.getElementById('prof-consumer').value.trim();
    const distributor = document.getElementById('prof-distributor').value.trim();

    const monthly_unit_threshold = parseFloat(document.getElementById('prof-unit-threshold').value);
    const monthly_budget = parseFloat(document.getElementById('prof-budget').value);
    const alert_increase_pct = parseFloat(document.getElementById('prof-spike-pct').value);

    try {
      const res = await apiFetch('/auth/me', {
        method: 'PUT',
        body: JSON.stringify({
          name,
          consumer_number,
          distributor,
          settings: {
            monthly_unit_threshold,
            monthly_budget,
            alert_increase_pct
          }
        })
      });

      TokenManager.setUser(res.data);
      showToast('Profile and alert triggers updated!', 'success');
    } catch (err) {
      console.error(err);
    } finally {
      btn.disabled = false;
    }
  });
}
