/**
 * HostelFlow Centralized Theme Controller
 * Single source of truth for Light, Dark, and System theme handling.
 * Complies with UI Completion & Dark Mode Fix Plan Section 3.2.
 */

(function () {
  'use strict';

  function getCookie(name) {
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  }

  function getResolvedDark(pref) {
    if (pref === 'dark') return true;
    if (pref === 'light') return false;
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  function getThemePreference() {
    const userTheme = document.documentElement.getAttribute('data-user-theme');
    const stored = localStorage.getItem('theme');
    const elPref = document.documentElement.getAttribute('data-theme-pref');
    const raw = (userTheme || stored || elPref || 'system').toLowerCase();
    if (raw === 'dark' || raw === 'light' || raw === 'system') {
      return raw;
    }
    return 'system';
  }

  function updateSwitcherElements(pref) {
    // Update all theme switcher partials
    const switchers = document.querySelectorAll('[data-theme-switcher]');
    switchers.forEach(function (sw) {
      const buttons = sw.querySelectorAll('[data-theme-option]');
      buttons.forEach(function (btn) {
        const opt = btn.getAttribute('data-theme-option');
        const isActive = opt === pref;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-checked', isActive ? 'true' : 'false');
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });
    });

    // Update legacy data-theme-btn elements if any
    document.querySelectorAll('[data-theme-btn]').forEach(function (btn) {
      const opt = (btn.getAttribute('data-theme-btn') || '').toLowerCase();
      btn.classList.toggle('active', opt === pref);
    });
  }

  function setThemePreference(pref) {
    pref = (pref || 'system').toLowerCase();
    if (pref !== 'light' && pref !== 'dark' && pref !== 'system') {
      pref = 'system';
    }

    // Suppress CSS transitions during switch
    document.documentElement.classList.add('theme-switching');

    // Persist to local storage
    try {
      localStorage.setItem('theme', pref);
    } catch (e) {}

    const isDark = getResolvedDark(pref);
    const resolvedTheme = isDark ? 'dark' : 'light';

    // Synchronize HTML attributes
    document.documentElement.setAttribute('data-theme-pref', pref);
    document.documentElement.setAttribute('data-user-theme', pref.toUpperCase());
    document.documentElement.setAttribute('data-theme', resolvedTheme);
    document.documentElement.style.colorScheme = resolvedTheme;

    // Update meta theme-color for browser chromes and mobile status bars
    const meta = document.getElementById('meta-theme-color');
    if (meta) {
      meta.setAttribute('content', isDark ? '#0B1220' : '#F6F8FC');
    }

    // Sync UI controls
    updateSwitcherElements(pref);

    // Persist to backend if authenticated
    const csrfToken = getCookie('csrftoken');
    if (csrfToken && document.documentElement.hasAttribute('data-user-theme')) {
      fetch('/accounts/theme/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrfToken,
        },
        body: 'theme=' + encodeURIComponent(pref.toUpperCase()),
      }).catch(function () {});
    }

    // Dispatch global themechange event for Charts and dynamic components
    window.dispatchEvent(
      new CustomEvent('themechange', {
        detail: { theme: resolvedTheme, pref: pref, isDark: isDark },
      })
    );

    // Remove transition suppression after render frame
    requestAnimationFrame(function () {
      setTimeout(function () {
        document.documentElement.classList.remove('theme-switching');
      }, 50);
    });
  }

  // System color scheme change listener
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemChange = function () {
      if (getThemePreference() === 'system') {
        setThemePreference('system');
      }
    };
    if (mq.addEventListener) {
      mq.addEventListener('change', handleSystemChange);
    } else if (mq.addListener) {
      mq.addListener(handleSystemChange);
    }
  }

  // Initial sync on DOM ready and after HTMX swaps
  document.addEventListener('DOMContentLoaded', function () {
    const currentPref = getThemePreference();
    updateSwitcherElements(currentPref);
  });

  document.body && document.body.addEventListener('htmx:afterSwap', function () {
    const currentPref = getThemePreference();
    updateSwitcherElements(currentPref);
  });

  // Cycle helper (for compact desktop / mobile icon buttons)
  function cycleTheme() {
    const current = getThemePreference();
    if (current === 'light') {
      setThemePreference('dark');
    } else if (current === 'dark') {
      setThemePreference('system');
    } else {
      setThemePreference('light');
    }
  }

  // Expose globals
  window.setThemePreference = setThemePreference;
  window.getThemePreference = getThemePreference;
  window.cycleTheme = cycleTheme;

  // Backward-compatible alias
  window.setTheme = function (theme) {
    setThemePreference((theme || 'system').toLowerCase());
  };
})();
