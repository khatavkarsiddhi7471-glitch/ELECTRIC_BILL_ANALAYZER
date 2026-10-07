/**
 * Universal Navigation and Notification Bell Dropdown
 */

document.addEventListener('DOMContentLoaded', () => {
  renderNavbar();
  if (TokenManager.isAuthenticated()) {
    initNotifications();
  }
});

function renderNavbar() {
  const navContainer = document.getElementById('main-nav');
  if (!navContainer) return;

  const currentPath = window.location.pathname;
  const isAuth = TokenManager.isAuthenticated();
  const user = TokenManager.getUser();

  if (!isAuth) {
    navContainer.innerHTML = `
      <div class="navbar">
        <a href="/" class="nav-brand">
          <span class="logo-bolt">⚡</span> Smart Electricity Analyzer
        </a>
        <div class="nav-user-actions">
          <a href="/login.html" class="btn btn-secondary btn-sm">Login</a>
          <a href="/register.html" class="btn btn-primary btn-sm">Sign Up Free</a>
        </div>
      </div>
    `;
    return;
  }

  const links = [
    { name: 'Dashboard', path: '/dashboard.html', icon: '📊' },
    { name: 'Add Bill', path: '/add-bill.html', icon: '➕' },
    { name: 'Bill History', path: '/history.html', icon: '📜' },
    { name: 'Appliances', path: '/appliances.html', icon: '🔌' },
    { name: 'Analytics', path: '/analysis.html', icon: '📈' },
    { name: 'Saving Tips', path: '/tips.html', icon: '💡' },
    { name: 'Tariffs', path: '/tariff.html', icon: '⚙️' }
  ];

  const linksHtml = links.map(l => {
    const isActive = currentPath.includes(l.path) || (currentPath === '/' && l.path === '/dashboard.html');
    return `<li><a href="${l.path}" class="nav-link ${isActive ? 'active' : ''}">${l.icon} ${l.name}</a></li>`;
  }).join('');

  navContainer.innerHTML = `
    <div class="navbar">
      <a href="/dashboard.html" class="nav-brand">
        <span class="logo-bolt">⚡</span> VoltWise
      </a>
      <ul class="nav-links">
        ${linksHtml}
      </ul>
      <div class="nav-user-actions">
        <!-- Notification Bell -->
        <div class="notif-wrapper">
          <button class="notif-btn" id="notif-bell" title="Notifications">
            🔔
            <span class="notif-badge" id="notif-count" style="display:none;">0</span>
          </button>
          <div class="notif-dropdown" id="notif-dropdown">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
              <strong style="font-size:0.9rem;">Alerts & Insights</strong>
              <button id="mark-all-read" class="btn-sm btn-secondary" style="font-size:0.75rem; padding:2px 6px; cursor:pointer;">Mark all read</button>
            </div>
            <div id="notif-list" style="max-height:260px; overflow-y:auto;">
              <p style="color:var(--text-muted); font-size:0.8rem; text-align:center; padding:1rem 0;">No active alerts.</p>
            </div>
          </div>
        </div>

        <a href="/profile.html" class="nav-link" title="Profile Settings">👤 ${user?.name ? user.name.split(' ')[0] : 'Profile'}</a>
        <button id="logout-btn" class="btn btn-secondary btn-sm" style="padding: 0.4rem 0.75rem;">Logout</button>
      </div>
    </div>
  `;

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    TokenManager.clear();
    showToast('Logged out successfully', 'info');
    window.location.href = '/login.html';
  });

  const bell = document.getElementById('notif-bell');
  const dropdown = document.getElementById('notif-dropdown');
  bell?.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown?.classList.toggle('show');
  });

  document.addEventListener('click', (e) => {
    if (!dropdown?.contains(e.target) && e.target !== bell) {
      dropdown?.classList.remove('show');
    }
  });

  document.getElementById('mark-all-read')?.addEventListener('click', async () => {
    try {
      await apiFetch('/alerts/read-all', { method: 'POST' });
      initNotifications();
    } catch (e) {
      console.error(e);
    }
  });
}

async function initNotifications() {
  try {
    const res = await apiFetch('/alerts');
    const countBadge = document.getElementById('notif-count');
    const notifList = document.getElementById('notif-list');
    
    if (!countBadge || !notifList) return;

    const unreadCount = res.data.unread_count || 0;
    if (unreadCount > 0) {
      countBadge.innerText = unreadCount;
      countBadge.style.display = 'block';
    } else {
      countBadge.style.display = 'none';
    }

    const alerts = res.data.alerts || [];
    if (alerts.length === 0) {
      notifList.innerHTML = `<p style="color:var(--text-muted); font-size:0.8rem; text-align:center; padding:1rem 0;">No alerts found.</p>`;
      return;
    }

    notifList.innerHTML = alerts.map(a => `
      <div class="notif-item ${!a.is_read ? 'unread' : ''}" style="cursor:pointer;" onclick="markSingleRead('${a.id}')">
        <div style="font-weight:600; font-size:0.82rem; color:${!a.is_read ? 'var(--accent-amber)' : 'var(--text-primary)'};">${a.title}</div>
        <div style="font-size:0.78rem; color:var(--text-secondary); margin-top:2px;">${a.message}</div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading notifications:', err);
  }
}

async function markSingleRead(alertId) {
  try {
    await apiFetch(`/alerts/${alertId}/read`, { method: 'PATCH' });
    initNotifications();
  } catch (e) {
    console.error(e);
  }
}
