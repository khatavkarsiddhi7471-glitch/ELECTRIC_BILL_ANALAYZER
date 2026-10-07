/**
 * Central API Client and Auth Token Manager
 */

const API_BASE = '/api/v1';

const TokenManager = {
  getToken() {
    return localStorage.getItem('token');
  },
  setToken(token) {
    localStorage.setItem('token', token);
  },
  getUser() {
    const userStr = localStorage.getItem('user');
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  },
  setUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },
  isAuthenticated() {
    return !!this.getToken();
  }
};

async function apiFetch(endpoint, options = {}) {
  const token = TokenManager.getToken();
  const headers = options.headers || {};

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    
    // Handle binary responses (e.g. PDF report download)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/pdf')) {
      if (!response.ok) {
        throw new Error('Failed to generate PDF report');
      }
      return response.blob();
    }

    const data = await response.json();

    if (!response.ok) {
      if (response.status === 401) {
        TokenManager.clear();
        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html') && window.location.pathname !== '/') {
          window.location.href = '/login.html';
        }
      }
      const errMsg = data?.error?.message || 'An error occurred';
      showToast(errMsg, 'error');
      throw new Error(errMsg);
    }

    return data;
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let icon = '⚡';
  if (type === 'error') icon = '❌';
  if (type === 'success') icon = '✅';
  if (type === 'warning') icon = '⚠️';

  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function formatCurrency(amt) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  }).format(amt || 0);
}
