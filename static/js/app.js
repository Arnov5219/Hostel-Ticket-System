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
  window.initIcons = function() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  };

  initIcons();
  setTimeout(initIcons, 50);
  setTimeout(initIcons, 200);

  document.addEventListener('alpine:initialized', initIcons);
  window.addEventListener('load', initIcons);


  // Global modal helper functions
  window.openModal = function(modalId) {
    const el = typeof modalId === 'string' ? document.getElementById(modalId) : modalId;
    if (!el) return;
    el.style.display = 'flex';
    el.classList.add('active');
    document.body.classList.add('modal-open');
    if (window.lucide) {
      window.lucide.createIcons();
    }
    const focusable = el.querySelector('input:not([type="hidden"]), select, textarea, button:not(.app-modal-close)');
    if (focusable) {
      setTimeout(() => focusable.focus(), 60);
    }
  };

  window.closeModal = function(modalId) {
    const el = typeof modalId === 'string' ? document.getElementById(modalId) : modalId;
    if (!el) return;
    el.style.display = 'none';
    el.classList.remove('active');
    const openModals = Array.from(document.querySelectorAll('.app-modal-backdrop, .command-palette-backdrop'))
      .filter(m => m.classList.contains('active') || (m.style.display === 'flex' && window.getComputedStyle(m).display === 'flex'));
    if (openModals.length === 0) {
      document.body.classList.remove('modal-open');
    }
  };

  window.closeAllModals = function() {
    document.querySelectorAll('.app-modal-backdrop, .command-palette-backdrop').forEach(m => {
      m.style.display = 'none';
      m.classList.remove('active');
    });
    document.body.classList.remove('modal-open');
  };

  // Global keyboard shortcuts
  window.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (activeTag !== 'input' && activeTag !== 'textarea' && activeTag !== 'select') {
        e.preventDefault();
        const toggleBtn = document.querySelector('.sidebar-toggle-btn');
        if (toggleBtn) toggleBtn.click();
      }
    }
    if (e.key === 'Escape') {
      closeAllModals();
      // Close dropdowns
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    }
  });

  // Backdrop click listener to close modals
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('app-modal-backdrop') || e.target.classList.contains('command-palette-backdrop')) {
      closeModal(e.target);
    }
  });

  // Guard against duplicate modal form submissions
  document.addEventListener('submit', function(e) {
    const form = e.target;
    const modal = form.closest('.app-modal-backdrop, .command-palette-backdrop, .app-modal-dialog, .command-palette-modal');
    if (modal && !form.hasAttribute('data-no-disable')) {
      const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        setTimeout(() => {
          submitBtn.disabled = true;
          submitBtn.style.opacity = '0.7';
          submitBtn.style.cursor = 'not-allowed';
        }, 10);
      }
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

  // Live Instant Search for Command Palette
  const searchInput = document.getElementById('search-input');
  const paletteResults = document.getElementById('palette-results');
  const paletteHint = document.getElementById('palette-hint');
  let searchTimer = null;

  if (searchInput && paletteResults) {
    const defaultNavHtml = paletteResults.innerHTML;

    searchInput.addEventListener('input', function() {
      const q = this.value.trim();
      clearTimeout(searchTimer);

      if (q.length < 2) {
        paletteResults.innerHTML = defaultNavHtml;
        if (paletteHint) paletteHint.textContent = 'Quick navigation: Dashboard, Tickets, Kanban, Profile';
        if (window.lucide) window.lucide.createIcons();
        return;
      }

      searchTimer = setTimeout(() => {
        if (paletteHint) paletteHint.textContent = `Searching for "${q}"...`;
        fetch(`/tickets/search-quick/?q=${encodeURIComponent(q)}`)
          .then(res => res.json())
          .then(data => {
            if (!data.results || data.results.length === 0) {
              paletteResults.innerHTML = `
                <div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: var(--fs-xs);">
                  No tickets found matching "${q}". Press Enter to search everywhere.
                </div>
              `;
              if (paletteHint) paletteHint.textContent = 'Press Enter to open full search results';
              return;
            }

            if (paletteHint) paletteHint.textContent = `${data.results.length} result(s) found (Click or press Enter)`;
            paletteResults.innerHTML = data.results.map(t => `
              <a href="${t.url}" class="dropdown-item" style="border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; text-decoration: none;">
                <div style="display: flex; flex-direction: column; gap: 2px; overflow: hidden;">
                  <span style="font-weight: 600; font-size: var(--fs-xs); color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
                    ${t.title}
                  </span>
                  <span style="font-size: 11px; color: var(--text-muted);">
                    ${t.ticket_no} • ${t.category || 'General'} • ${t.hostel || ''}
                  </span>
                </div>
                <span class="status-pill ${t.status.toLowerCase().replace('_', '-')}" style="font-size: 10px; padding: 1px 6px;">
                  ${t.status_display}
                </span>
              </a>
            `).join('');
          })
          .catch(() => {
            if (paletteHint) paletteHint.textContent = 'Search failed';
          });
      }, 250);
    });
  }
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

// Theme management
function getThemePreference() {
  const userTheme = document.documentElement.getAttribute('data-user-theme');
  const storedTheme = localStorage.getItem('theme');
  return (userTheme || storedTheme || 'SYSTEM').toUpperCase();
}

function setTheme(theme) {
  theme = (theme || 'SYSTEM').toUpperCase();
  document.documentElement.classList.add('theme-switching');
  localStorage.setItem('theme', theme);
  document.documentElement.setAttribute('data-user-theme', theme);

  let isDark = false;
  if (theme === 'DARK') {
    isDark = true;
  } else if (theme === 'LIGHT') {
    isDark = false;
  } else {
    isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  const themeValue = isDark ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', themeValue);
  document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';

  const meta = document.getElementById('meta-theme-color');
  if (meta) {
    meta.setAttribute('content', isDark ? '#0F1115' : '#F7F8FA');
  }

  // Persist to backend if authenticated
  const csrf = getCookie('csrftoken');
  if (csrf) {
    fetch('/accounts/theme/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrf,
      },
      body: 'theme=' + encodeURIComponent(theme),
    }).catch(() => {});
  }

  window.dispatchEvent(new CustomEvent('themechange', {
    detail: { theme: themeValue, preference: theme, isDark: isDark }
  }));

  document.querySelectorAll('[data-theme-btn]').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-theme-btn') === theme);
  });

  setTimeout(() => {
    document.documentElement.classList.remove('theme-switching');
  }, 150);
}

window.setTheme = setTheme;
window.getThemePreference = getThemePreference;

// Hide bottom navigation on mobile when form inputs are focused to prevent keyboard overlap (Section 5.2)
document.addEventListener('focusin', function(e) {
  if (window.innerWidth < 768 && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) {
    const nav = document.querySelector('.mobile-bottom-nav');
    if (nav) nav.style.display = 'none';
  }
});

document.addEventListener('focusout', function(e) {
  if (window.innerWidth < 768 && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) {
    const nav = document.querySelector('.mobile-bottom-nav');
    if (nav) nav.style.display = '';
  }
});

// Android Native / Capacitor Integration (Phases 3, 4, 7, 8)
(function() {
  function initCapacitorBridge() {
    if (!window.Capacitor || !window.Capacitor.Plugins) return;

    const { App, SplashScreen, StatusBar, Network } = window.Capacitor.Plugins;

    // 1. Hide splash screen once page is ready
    if (SplashScreen) {
      setTimeout(function() {
        SplashScreen.hide().catch(function() {});
      }, 350);
    }

    // 2. Hardware Back Button Handling
    let lastBackPressTime = 0;
    if (App) {
      App.addListener('backButton', function(state) {
        // A. Priority 1: Close open modals
        const activeModal = document.querySelector('.modal.active, .app-modal-backdrop.active, [x-show="open"]:not([style*="display: none"])');
        if (activeModal) {
          const closeBtn = activeModal.querySelector('.app-modal-close, [data-modal-close], button[aria-label="Close"]');
          if (closeBtn) {
            closeBtn.click();
            return;
          }
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
          return;
        }

        // B. Priority 2: Close active dropdowns / popovers
        const activeDropdown = document.querySelector('[x-show="dropdownOpen"]:not([style*="display: none"])');
        if (activeDropdown) {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
          return;
        }

        // C. Priority 3: Navigate back in history if not at root
        const pathname = window.location.pathname;
        const isRoot = pathname === '/' || pathname === '/dashboard/' || pathname === '/accounts/login/';

        if (state && state.canGoBack && !isRoot && window.history.length > 1) {
          window.history.back();
          return;
        }

        // D. Priority 4: Double-tap to exit on root or no history
        const now = Date.now();
        if (now - lastBackPressTime < 2000) {
          App.exitApp();
        } else {
          lastBackPressTime = now;
          if (window.showToast) {
            window.showToast('Press back again to exit', 'info');
          }
        }
      });
    }

    // 3. Network Offline / Online Listener
    if (Network) {
      Network.addListener('networkStatusChange', function(status) {
        if (!status.connected) {
          if (window.showToast) {
            window.showToast('No internet connection. Please check Wi-Fi or mobile data.', 'error');
          }
        } else {
          if (window.showToast) {
            window.showToast('Back online.', 'success');
          }
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCapacitorBridge);
  } else {
    initCapacitorBridge();
  }
})();

