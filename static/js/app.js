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
