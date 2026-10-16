# Dark Mode Diagnosis Report (Phase F0)

## 1. Current Theme Toggle Behavior
- **DOM Attribute Changed:**
  - `document.documentElement.setAttribute('data-theme', 'dark' | 'light')`
  - `document.documentElement.setAttribute('data-user-theme', 'DARK' | 'LIGHT' | 'SYSTEM')`
  - Sets `document.documentElement.style.colorScheme = 'dark' | 'light'`
  - Sets `<meta name="theme-color" id="meta-theme-color">` to `#0F1115` (dark) or `#F7F8FA` (light)
- **Storage Key:** `localStorage.getItem('theme')` / `localStorage.setItem('theme', theme)`
- **Backend Sync Endpoint:**
  - `POST /accounts/theme/` with body `theme=DARK|LIGHT|SYSTEM` and CSRF header `X-CSRFToken`
  - Returns HTTP 204 No Content on success
  - Updates `request.user.theme` in database
- **Inconsistencies Identified:**
  - Multiple fragmented theme switcher implementations:
    - `base.html` user menu dropdown: segmented control labeled "Light", "Dark", "Auto"
    - `profile.html`: 3 vertical button cards labeled "Light", "Dark", "System"
    - `_bottom_nav.html` mobile "More" sheet: segmented control labeled "Light", "Dark", "Auto"
    - `login.html`: two-state icon toggle (DARK/LIGHT only)
    - Desktop topbar: icon toggle button with `c === 'DARK' ? 'LIGHT' : 'DARK'`
  - The switcher instances do not share a single partial or state manager, causing desynchronization across the UI.
  - Active state visual feedback in `profile.html` and `_bottom_nav.html` used inline styles without proper focus/hover tokens, looking like unstyled buttons.

## 2. Where Dark Values Live
- Dark values live exclusively in `static/css/tokens.css` under the `:root[data-theme="dark"]` selector.
- `tokens.css` is loaded in `<head>` in `templates/base.html`, which is inherited by all layouts including auth (`login.html`, `register.html`), hosteler layouts, and staff layouts.
- However, several components (category chips in `create.html`, urgency cards, appearance buttons, avatar tiles) relied on default button styling or ad-hoc background rules that failed to contrast properly in dark mode or caused invisible text on light backgrounds.
- Specifically:
  - `--primary` in dark mode was set to `#3B82F6` (insufficient contrast ~3.8:1 with white text instead of the required `#2F6FEB` which achieves 4.6:1).
  - Dark mode status chips in Kanban had `background: var(--ink)` and `color: var(--white)`. In dark mode, `--ink` is `#E6EAF2` (near-white), leading to invisible white text on white/near-white chips.

## 3. CSS Variables & Evaluation
- `:root` defines light tokens; `:root[data-theme="dark"]` defines dark overrides.
- In `base.html`, the inline head script immediately evaluates:
  `var pref = document.documentElement.getAttribute('data-user-theme') || localStorage.getItem('theme') || 'SYSTEM';`
  and sets `data-theme="dark"` or `"light"`.
- When `data-theme="dark"` is set on `<html>`, `getComputedStyle(document.documentElement).getPropertyValue('--bg-app')` resolves to `#0B1220`.
- The target architecture requires standardizing on `data-theme-pref="light|dark|system"` and `data-theme="light|dark"`, alongside a dedicated controller `static/js/theme.js`.

## 4. Color Literals & Legacy Token Count
- `static/css/tokens.css`: Only file where raw color literals (`#hex`, `rgba(...)`) are permitted.
- `static/css/base.css`, `layout.css`, `components.css`, `kanban.css`, `dashboard.css`:
  - 0 hardcoded hex/rgb color literals (verified by `tests/test_no_hardcoded_colors.py`).
  - Legacy token usage: `--accent`, `--accent-hover`, `--accent-light`, `--accent-glow` are still referenced in 16 places across `base.css`, `layout.css`, `components.css`, and `kanban.css`.
  - Old blue reference `#1D5FB4` existed as fallback in `static/js/charts.js`.

## 5. Chart.js Theme Integration
- `static/js/charts.js` uses `getChartThemeTokens()` reading CSS variables dynamically via `getComputedStyle(document.documentElement)`.
- It already listens to the `themechange` event on `window`.
- Rebuilding needs to ensure fallback colors match the updated `#2F6FEB` / `#2563EB` tokens rather than `#1D5FB4`.

## 6. Root Cause of Empty Kanban & List Data
- Standard demo accounts L0..L5 created by `seed_demo_accounts` were assigned to hostel `MH` ("Mandakini Hostel").
- Meanwhile, `seed_demo_data` created all sample tickets under `hostel_a` (`BH-1`) and `hostel_b` (`BH-2`).
- As a result, when logging in as L0 (Hosteler) or L1 (Caretaker), all ticket queries filter by the user's assigned hostel (`MH`), resulting in 0 tickets across all statuses in both Kanban and list views.
- Fix: Standardize demo seeding so L0 and L1 share the same hostel (`BH-1` / Boys Hostel 1), and tickets are distributed realistically across all statuses (Open, Assigned, In Progress, On Hold, Resolved, Closed).
