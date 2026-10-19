# Hostel Ticket System — Android App Architecture & Migration Plan

## 1. Executive Summary & Approach Decision

### Decision: Capacitor Android Native Wrapper
We selected **Capacitor 7** as the native container to wrap the existing Django-powered, mobile-ready Hostel Ticket System.

### Why Capacitor?
1. **Preserves 100% of Backend & Logic**: Zero rewriting of Django views, models, forms, authentication sessions, CSRF protection, role-based access (L0–L5), ticket lifecycle, SLA calculation, and escalation workflows.
2. **Preserves Unified Frontend Design System**: The recent UI cleanup and dark mode work (tokens, Alpine.js, Lucide icons, safe areas, responsive bottom bar) runs directly in the Android WebView without UI divergence.
3. **Robust Cookie & Session Persistence**: Android WebView's `CookieManager` persists Django `sessionid` and `csrftoken` securely across app closures and device restarts.
4. **Native Android Capabilities**: Directly handles Android hardware Back button, splash screen, status bar, offline state detection, and native file pickers.
5. **No Second Frontend Framework**: Avoids fragmenting the codebase into a separate React/Flutter client requiring duplicate API endpoints and validation logic.

---

## 2. Dependency List

### Core Native & Build Tools:
- **Node.js**: v24.15.0+ (installed)
- **npm**: 11.12.1+ (installed)
- **Java Development Kit**: OpenJDK 21 (installed)
- **Android SDK**: `C:\Users\arnov\AppData\Local\Android\Sdk`
  - Platforms: Android 36, Android 37
  - Build Tools: 35.0.0, 36.0.0
  - Platform Tools: `adb`

### Capacitor Packages (npm):
- `@capacitor/core`: ^7.0.0
- `@capacitor/cli`: ^7.0.0
- `@capacitor/android`: ^7.0.0
- `@capacitor/app`: ^7.0.0 (Back button handling, lifecycle events)
- `@capacitor/splash-screen`: ^7.0.0 (Startup splash screen control)
- `@capacitor/status-bar`: ^7.0.0 (Native status bar styling)
- `@capacitor/network`: ^7.0.0 (Connection state monitoring)

---

## 3. Application Identity & Configuration

- **Application Name**: Hostel Ticket System
- **Package ID / Application ID**: `com.hostelflow.tickets`
- **Initial Version**: `1.0.0`
- **Version Code**: `1`
- **Target SDK**: `35` (Android 15)
- **Minimum SDK**: `24` (Android 7.0 Nougat — covering >98% of active Android devices)
- **Environment Endpoints**:
  - **Development / Emulator**: `http://10.0.2.2:4000` or local LAN IP `http://192.168.x.x:4000` (cleartext allowed for debug builds only).
  - **Production Release**: `https://hosteltickets.example.com` (enforces HTTPS only, cleartext disabled).

---

## 4. Route & Feature Inventory

| Route / Feature | In-App Handling | Native Integration / Considerations |
| :--- | :--- | :--- |
| `/accounts/login/` | In-App WebView | Cookie session storage; auto-login on restart |
| `/accounts/profile/` | In-App WebView | Profile viewing & settings |
| `/tickets/` | In-App WebView | Filter chips, search bar, status tabs |
| `/tickets/create/` | In-App WebView | File picker `<input type="file">` for photos/PDFs |
| `/tickets/<id>/` | In-App WebView | Timeline history, actions, status transitions |
| `/tickets/kanban/` | In-App WebView | Touch-friendly drag/scroll board |
| `/dashboard/` | In-App WebView | Role-based dashboard (L0–L5) |
| `/announcements/` | In-App WebView | Broadcast notices |
| External URLs | System Browser | Handled via URL scheme filter or Browser plugin |
| `tel:` / `mailto:` | System Apps | Handled via Android Intent handler |

---

## 5. Native Integration Points

1. **Hardware Back Button**:
   - Close open modals / dropdowns first.
   - If history exists within current app session, call `window.history.back()`.
   - If on the root dashboard/home page, show exit toast / confirm or exit.
2. **Startup & Splash**:
   - Branded splash screen with app icon, primary brand background (`#0f172a` dark / `#2563eb` primary).
   - Dismiss splash once initial page load or local shell is ready.
3. **Offline & Network Recovery**:
   - Local fallback shell (`www/index.html`) loaded if network is unavailable on startup.
   - Network listener displays unobtrusive offline banner with a Retry action.
4. **File Handling**:
   - Native Android file chooser enabled via WebChromeClient.
   - Secure FileProvider configured for downloads and camera access if needed.

---

## 6. Migration Plan & Release Gates

- **Phase 1**: Repository Audit, Architecture Decision, app conversion branch. *(Current)*
- **Phase 2**: App Identity, Capacitor initialization, Android project scaffolding, environment separation.
- **Phase 3**: Branded splash screen and startup loading state.
- **Phase 4**: Android Back navigation, modal interceptor, in-app back buttons.
- **Phase 5**: Mobile UI & safe area verification in Android WebView.
- **Phase 6**: Authentication session persistence, CSRF validation, role testing.
- **Phase 7**: Offline fallback shell, network retry banner.
- **Phase 8**: File upload `<input type="file">` and external link handling.
- **Phase 9**: Production HTTPS backend configuration & security flags.
- **Phase 10**: Lifecycle background/resume & performance check.
- **Phase 11**: End-to-end testing & release candidate verification.
- **Phase 12**: Release APK generation and build documentation.
