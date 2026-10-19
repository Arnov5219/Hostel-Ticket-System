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

// ==========================================================================
// Mobile In-App Navigation, Overlays, Unsaved Form Changes & History Tracker
// ==========================================================================

// 1. Overlay & Dialog dismissal utility (Modals, Drawers, Sheets, Dropdowns)
window.dismissOpenOverlays = function() {
  // A. Mobile bottom sheet modal (e.g. "More" bottom sheet)
  const bottomSheetBackdrop = document.querySelector('.bottom-sheet-backdrop:not([style*="display: none"])');
  if (bottomSheetBackdrop) {
    const closeBtn = bottomSheetBackdrop.querySelector('button[aria-label="Close sheet"], button.btn-ghost');
    if (closeBtn) {
      closeBtn.click();
    } else {
      bottomSheetBackdrop.click();
    }
    return true;
  }

  // B. Standard modals, dialogs, drawers, command palette
  const openModals = Array.from(document.querySelectorAll('.app-modal-backdrop, .command-palette-backdrop, [data-modal], dialog[open]'))
    .filter(function(el) {
      if (el.classList.contains('active') || el.classList.contains('show') || el.hasAttribute('open')) return true;
      try {
        const style = window.getComputedStyle(el);
        return style.display === 'flex' || style.display === 'block';
      } catch (e) {
        return false;
      }
    });

  if (openModals.length > 0) {
    let closedAny = false;
    openModals.forEach(function(modal) {
      if (modal.id && typeof window.closeModal === 'function') {
        window.closeModal(modal.id);
        closedAny = true;
      } else {
        const closeBtn = modal.querySelector('.app-modal-close, [data-modal-close], button[aria-label="Close"], button.close');
        if (closeBtn) {
          closeBtn.click();
          closedAny = true;
        } else {
          modal.style.display = 'none';
          closedAny = true;
        }
      }
    });
    document.body.classList.remove('modal-open');
    if (closedAny) return true;
  }

  // C. Active dropdown menus, popovers, or open Alpine state menus
  const activeDropdowns = Array.from(document.querySelectorAll('.dropdown-menu.show, [x-show="dropdownOpen"]:not([style*="display: none"]), [x-show="open"]:not([style*="display: none"])'));
  if (activeDropdowns.length > 0) {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
    return true;
  }

  return false;
};

// 2. Unsaved form changes confirmation utility
window.hasUnsavedChanges = function() {
  const forms = document.querySelectorAll('form:not([method="get"]):not([data-no-unsaved-check])');
  for (let i = 0; i < forms.length; i++) {
    const form = forms[i];
    if (form.dataset.hfSubmitted === 'true') continue;

    const elements = form.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]), textarea, select');
    for (let j = 0; j < elements.length; j++) {
      const el = elements[j];
      if (el.disabled || el.dataset.ignoreDirty) continue;

      if (el.type === 'checkbox' || el.type === 'radio') {
        if (el.checked !== el.defaultChecked) return true;
      } else if (el.tagName === 'SELECT') {
        for (let k = 0; k < el.options.length; k++) {
          if (el.options[k].selected !== el.options[k].defaultSelected) return true;
        }
      } else {
        // text, textarea, password, email, number, etc.
        if (el.value !== el.defaultValue && el.value.trim().length > 0) {
          return true;
        }
      }
    }
  }
  return false;
};

window.confirmDiscardChanges = function() {
  if (window.hasUnsavedChanges()) {
    return window.confirm('You have unsaved changes. Are you sure you want to discard them and leave?');
  }
  return true;
};

document.addEventListener('submit', function(e) {
  if (e.target && e.target.tagName === 'FORM') {
    e.target.dataset.hfSubmitted = 'true';
  }
}, true);

// 3. Scroll position and list filter preservation
function saveCurrentScroll() {
  try {
    const key = 'hf_scroll_' + window.location.pathname;
    sessionStorage.setItem(key, String(window.scrollY || window.pageYOffset || 0));
  } catch (e) {}
}

window.addEventListener('beforeunload', saveCurrentScroll);
window.addEventListener('pagehide', saveCurrentScroll);

function restoreScrollPosition() {
  try {
    const key = 'hf_scroll_' + window.location.pathname;
    const saved = sessionStorage.getItem(key);
    if (saved !== null) {
      const top = parseInt(saved, 10);
      if (!isNaN(top) && top > 0) {
        setTimeout(function() {
          window.scrollTo({ top: top, behavior: 'instant' });
        }, 50);
      }
    }
  } catch (e) {}
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', restoreScrollPosition);
} else {
  restoreScrollPosition();
}

// 4. In-app session navigation stack & bottom-nav deduplication
(function() {
  function recordNavigation() {
    const path = window.location.pathname + window.location.search;
    if (path.startsWith('/accounts/login') || path.startsWith('/accounts/logout') || path.startsWith('/health')) {
      return;
    }
    try {
      let stack = JSON.parse(sessionStorage.getItem('hf_nav_stack') || '[]');
      if (!Array.isArray(stack)) stack = [];

      // Avoid consecutive duplicate entries
      if (stack.length === 0 || stack[stack.length - 1] !== path) {
        if (stack.length >= 2 && stack[stack.length - 2] === path) {
          stack.pop();
        } else {
          stack.push(path);
          if (stack.length > 30) stack.shift();
        }
        sessionStorage.setItem('hf_nav_stack', JSON.stringify(stack));
      }
    } catch (e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', recordNavigation);
  } else {
    recordNavigation();
  }

  // Prevent bottom nav tab cycling / duplicate history loops
  document.addEventListener('click', function(e) {
    const navItem = e.target.closest('.mobile-bottom-nav .bottom-nav-item:not(.raise-center-btn)');
    if (!navItem || !navItem.getAttribute('href')) return;

    const targetHref = navItem.getAttribute('href');
    if (targetHref.startsWith('#') || targetHref.startsWith('javascript:')) return;

    try {
      const url = new URL(targetHref, window.location.origin);
      const targetPath = url.pathname;

      // When tapping Home / Dashboard: Reset stack to Dashboard root
      if (targetPath === '/' || targetPath === '/dashboard/') {
        sessionStorage.setItem('hf_nav_stack', JSON.stringify(['/dashboard/']));
      } else {
        // Root tabs (Tickets, Kanban, Notices, Profile):
        // Reset stack to [Dashboard, Target] so Back always goes to Dashboard without ping-pong
        sessionStorage.setItem('hf_nav_stack', JSON.stringify(['/dashboard/', targetPath]));
      }
    } catch (err) {}
  });
})();

// 5. Global handler for mobile back button in headers
window.handleMobileBack = function(btn) {
  // Priority 1: Check and dismiss any open modals, drawers, bottom sheets, or overlays
  if (window.dismissOpenOverlays && window.dismissOpenOverlays()) {
    return;
  }

  // Priority 2: Confirm discarding unsaved changes in forms
  if (window.confirmDiscardChanges && !window.confirmDiscardChanges()) {
    return;
  }

  // Priority 3: Navigate back using in-app session navigation history
  const currentPath = window.location.pathname + window.location.search;
  try {
    let stack = JSON.parse(sessionStorage.getItem('hf_nav_stack') || '[]');
    if (Array.isArray(stack) && stack.length > 0) {
      // Pop current page if on top of stack
      while (stack.length > 0 && (stack[stack.length - 1] === currentPath || stack[stack.length - 1] === window.location.pathname)) {
        stack.pop();
      }
      if (stack.length > 0) {
        const targetUrl = stack.pop();
        sessionStorage.setItem('hf_nav_stack', JSON.stringify(stack));
        window.location.href = targetUrl;
        return;
      }
    }
  } catch (e) {}

  // Priority 4: Safe same-origin referrer check
  if (document.referrer && document.referrer.indexOf(window.location.origin) === 0) {
    try {
      const refUrl = new URL(document.referrer);
      const refPath = refUrl.pathname + refUrl.search;
      if (refPath !== currentPath &&
          !refPath.startsWith('/accounts/login') &&
          !refPath.startsWith('/accounts/logout') &&
          !refPath.startsWith('/accounts/register') &&
          !refPath.startsWith('/health')) {
        window.location.href = document.referrer;
        return;
      }
    } catch (e) {}
  }

  // Priority 5: Fallback to context-specific parent URL or dashboard
  let fallback = btn ? btn.getAttribute('data-fallback') : null;
  if (!fallback) {
    fallback = '/dashboard/';
  }
  window.location.href = fallback;
};

// ==========================================================================
// App Launch / Initialization Screen Controller
// ==========================================================================
window.initAppLaunchScreen = function() {
  const launchScreen = document.getElementById('app-launch-screen');
  if (!launchScreen) return;

  let alreadyLaunched = false;
  try {
    alreadyLaunched = sessionStorage.getItem('hf_app_launched') === 'true';
  } catch (e) {}

  if (alreadyLaunched) {
    launchScreen.style.display = 'none';
    return;
  }

  const progressBar = document.getElementById('launch-progress-bar');
  const statusText = document.getElementById('launch-status-text');
  const fallbackBox = document.getElementById('launch-fallback-box');
  const fallbackMsg = document.getElementById('launch-fallback-msg');

  let currentPercent = 15;
  if (progressBar) progressBar.style.width = currentPercent + '%';

  const progressTimer = setInterval(function() {
    if (currentPercent < 85) {
      currentPercent += Math.floor(Math.random() * 10) + 6;
      if (currentPercent > 85) currentPercent = 85;
      if (progressBar) progressBar.style.width = currentPercent + '%';
    }
  }, 160);

  const safetyTimeout = setTimeout(function() {
    clearInterval(progressTimer);
    if (fallbackBox) {
      fallbackBox.style.display = 'flex';
      if (!navigator.onLine && fallbackMsg) {
        fallbackMsg.textContent = 'You appear to be offline. Please check your connection.';
      }
    }
    if (statusText) statusText.style.display = 'none';
  }, 7500);

  function completeLaunch() {
    clearTimeout(safetyTimeout);
    clearInterval(progressTimer);

    if (progressBar) progressBar.style.width = '100%';
    if (statusText) statusText.textContent = 'Ready';

    try {
      sessionStorage.setItem('hf_app_launched', 'true');
    } catch (e) {}

    if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.SplashScreen) {
      try {
        window.Capacitor.Plugins.SplashScreen.hide().catch(function() {});
      } catch (e) {}
    }

    setTimeout(function() {
      launchScreen.classList.add('launch-screen-fadeout');
      setTimeout(function() {
        launchScreen.style.display = 'none';
      }, 320);
    }, 180);
  }

  if (document.readyState === 'complete') {
    completeLaunch();
  } else {
    window.addEventListener('load', completeLaunch);
  }
};

window.retryAppLaunch = function() {
  const fallbackBox = document.getElementById('launch-fallback-box');
  const statusText = document.getElementById('launch-status-text');
  if (fallbackBox) fallbackBox.style.display = 'none';
  if (statusText) {
    statusText.style.display = 'block';
    statusText.textContent = 'Retrying connection...';
  }
  fetch('/health/', { method: 'GET', cache: 'no-store' })
    .then(function(res) {
      if (res.ok) {
        window.location.reload();
      } else {
        throw new Error('Service status ' + res.status);
      }
    })
    .catch(function() {
      window.location.reload();
    });
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', window.initAppLaunchScreen);
} else {
  window.initAppLaunchScreen();
}

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

    // 2. Hardware Back Button Handling (Capacitor App plugin)
    let lastBackPressTime = 0;
    if (App) {
      App.addListener('backButton', function(state) {
        // Priority 1: Dismiss open overlays, modals, bottom sheets, or menus first
        if (window.dismissOpenOverlays && window.dismissOpenOverlays()) {
          return;
        }

        // Priority 2: Confirm discarding unsaved form changes before navigating
        if (window.confirmDiscardChanges && !window.confirmDiscardChanges()) {
          return;
        }

        const pathname = window.location.pathname;

        // Priority 3: On auth pages (login/register), double-tap to exit and NEVER return to authenticated pages
        if (pathname.startsWith('/accounts/login') || pathname.startsWith('/accounts/register')) {
          const now = Date.now();
          if (now - lastBackPressTime < 2000) {
            App.exitApp();
          } else {
            lastBackPressTime = now;
            if (window.showToast) {
              window.showToast('Press back again to exit', 'info');
            }
          }
          return;
        }

        // Priority 4: Root / Dashboard: Double-tap to exit
        if (pathname === '/' || pathname === '/dashboard/') {
          const now = Date.now();
          if (now - lastBackPressTime < 2000) {
            App.exitApp();
          } else {
            lastBackPressTime = now;
            if (window.showToast) {
              window.showToast('Press back again to exit', 'info');
            }
          }
          return;
        }

        // Priority 5: Inner pages - navigate backward through meaningful screens
        if (typeof window.handleMobileBack === 'function') {
          window.handleMobileBack();
        } else {
          window.location.href = '/dashboard/';
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

