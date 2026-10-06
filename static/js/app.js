// Application JavaScript

// Helper to get CSRF cookie
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// HTMX CSRF configuration
document.addEventListener('DOMContentLoaded', function() {
  document.body.addEventListener('htmx:configRequest', function(evt) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      evt.detail.headers['X-CSRFToken'] = csrfToken;
    }
  });

  // Re-run Lucide icons on HTMX DOM swap
  document.body.addEventListener('htmx:afterSwap', function() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  });

  // Handle HTMX response error toasts
  document.body.addEventListener('htmx:responseError', function(evt) {
    let errorMsg = 'An unexpected error occurred.';
    try {
      const data = JSON.parse(evt.detail.xhr.responseText);
      if (data.error || data.detail) {
        errorMsg = data.error || data.detail;
      }
    } catch (e) {
      if (evt.detail.xhr.status === 403) {
        errorMsg = 'Permission denied.';
      } else if (evt.detail.xhr.status === 404) {
        errorMsg = 'Resource not found.';
      }
    }
    showToast(errorMsg, 'error');
  });

  // Initialize Lucide icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Global ⌘K / Ctrl+K search handler
  window.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const palette = document.getElementById('command-palette');
      if (palette) {
        const isHidden = palette.style.display === 'none' || palette.classList.contains('hidden');
        if (isHidden) {
          palette.style.display = 'flex';
          const input = palette.querySelector('input');
          if (input) input.focus();
        } else {
          palette.style.display = 'none';
        }
      }
    }
    if (e.key === 'Escape') {
      const palette = document.getElementById('command-palette');
      if (palette) palette.style.display = 'none';
      // Close dropdowns
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    }
  });

  // Dropdown toggle listeners
  document.addEventListener('click', function(e) {
    const trigger = e.target.closest('[data-dropdown-toggle]');
    if (trigger) {
      const dropdown = trigger.closest('.dropdown');
      if (dropdown) {
        const isOpen = dropdown.classList.contains('open');
        document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
        if (!isOpen) dropdown.classList.add('open');
      }
      return;
    }
    if (!e.target.closest('.dropdown-menu')) {
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    }
  });
});

// Toast notification function
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Window global helper
window.showToast = showToast;
