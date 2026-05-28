# Mox — Transformation Blueprint (Updated)

> **Project:** mox-cli v7.2.2 — Terminal music CLI with web UI, mpv backend  
> **Status:** Phase 1 ✅ Complete · Phase 2 🔄 ~70% · Phase 3 📋 Planned  
> **Last updated:** May 2026

---

## Overall Progress

```
Phase 1 — Critical Stabilization    ████████████████████ 100%
Phase 2 — UI/UX Modernization       ██████████████░░░░░░  70%
Phase 3 — Feature Expansion         ░░░░░░░░░░░░░░░░░░░░   0%
Phase 4 — Architecture              ░░░░░░░░░░░░░░░░░░░░   0%
```

---

## Phase 1 — Critical Stabilization ✅ COMPLETE

All 6 original critical security fixes + all performance fixes + bonus hardening items done.

### Security Fixes (All Complete)

| ID | Fix | File | Status |
|----|-----|------|--------|
| C1 | Lock race condition — two-phase `ln` steal + Linux `flock` path | [mox.sh:219–268](file:///c:/Users/kg060/Desktop/projects/mox/src/mox.sh#L219-L268) | ✅ |
| C2 | Config sandbox — whitelist-only `_load_config()` parser replaces `source` | [mox.sh:103–145](file:///c:/Users/kg060/Desktop/projects/mox/src/mox.sh#L103-L145) | ✅ |
| C2b | Two bypass `source "$CONFIG_FILE"` calls fixed in `do_auto_restart_toggle` + `do_reload_config` | [mox.sh:1327](file:///c:/Users/kg060/Desktop/projects/mox/src/mox.sh#L1327), [mox.sh:3555](file:///c:/Users/kg060/Desktop/projects/mox/src/mox.sh#L3555) | ✅ |
| C3 | CSRF / auth token separation — independent `CSRF_TOKEN` and `AUTH_TOKEN` | [server.py:98–99](file:///c:/Users/kg060/Desktop/projects/mox/src/music_ui_server.py#L98-L99) | ✅ |
| C3b | `mox_auth` cookie uses `HttpOnly` flag | [server.py:1340](file:///c:/Users/kg060/Desktop/projects/mox/src/music_ui_server.py#L1340) | ✅ |
| C4 | Play query sanitization via `_validate_query()` before `subprocess.run()` | [server.py:1427](file:///c:/Users/kg060/Desktop/projects/mox/src/music_ui_server.py#L1427) | ✅ |
| C5 | `pkill -f` fallback removed — only kills by PID file | [mox.sh:1268–1290](file:///c:/Users/kg060/Desktop/projects/mox/src/mox.sh#L1268-L1290) | ✅ |
| C6 | CSP + X-Frame-Options + X-Content-Type-Options + X-XSS-Protection on all responses | [server.py:102–110](file:///c:/Users/kg060/Desktop/projects/mox/src/music_ui_server.py#L102-L110) | ✅ |

### Performance Fixes (All Complete)

| ID | Fix | Status |
|----|-----|--------|
| H1 | `_get_multi()` batches all IPC in one socat session (was N separate connections) | ✅ |
| H6 | `do_bar()` uses `printf -v` arithmetic — zero awk forks per frame | ✅ |
| H8 | `_validate_config()` double-check pattern cleaned up | ✅ |

### Bonus Hardening (Done Beyond Original Plan)

| Item | Details | Status |
|------|---------|--------|
| Per-IP rate limiting | `_rate_limit_buckets` dict keyed by IP — one client can't starve others | ✅ |
| Search timeout extended | 15s → 30s with helpful error message pointing to `YOUTUBE_API_KEY` | ✅ |
| `_serve_manifest()` endpoint | `/manifest.webmanifest` served in-process (no static asset pipeline needed) | ✅ |
| Buffer progress in `do_bar()` | Shows `buf:X%` from `demuxer-cache-state` seekable-ranges | ✅ |

---

## Phase 2 — UI/UX Modernization 🔄 ~70% Complete

### Done

| Feature | Details | Status |
|---------|---------|--------|
| Toast notification system | Bottom-right animated stack, color-coded by type, auto-dismiss 3s | ✅ |
| Command palette (⌘K / Ctrl+K) | Floating modal with fuzzy search over all commands | ✅ |
| Search-and-play panel | `/api/v2/search` endpoint + search results UI with play/queue buttons | ✅ |
| EQ preset UI | flat / bass / treble / vocal / loudness / normalize buttons | ✅ |
| Loading skeletons | Shimmer animation for search results loading state | ✅ |
| Drag-and-drop queue (visual) | `draggable`, `ondragstart`, `ondragover` on queue items | ✅ |
| PWA manifest link | `<link rel="manifest">` in HTML + `_serve_manifest()` endpoint | ✅ |
| API v2 versioned endpoints | `/api/v2/state`, `/api/v2/events`, `/api/v2/cmd`, `/api/v2/play`, `/api/v2/search`, `/api/v2/health` | ✅ |

### Remaining Phase 2 Items

#### P2-R1: Complete Drag-and-Drop Backend Sync
**Current state:** Visual reorder works but the `ondrop` handler doesn't call the backend, so mpv's queue doesn't actually change.  
**Fix:** Add `ondrop` + `ondragend` handlers to queue items. On drop, call `POST /api/v2/cmd` with `qmove {fromIdx} {toIdx}`. Trigger a state refresh after.  
**Effort:** ~30 min

#### P2-R2: Command Palette Auto-Focus
**Current state:** Palette opens but user must click the input to type.  
**Fix:** Add `document.getElementById('palette-input').focus()` to the palette open handler.  
**Effort:** 5 min

#### P2-R3: Waveform / Frequency Visualizer
**Approach:** Web Audio API `AnalyserNode` reading from the stream URL. Draw 16 frequency bars in a `<canvas>` at 30fps. Falls back gracefully when audio context unavailable.  
**Effort:** ~2 hrs

#### P2-R4: Mobile Responsive Layout
**Current state:** Grid breaks below 768px.  
**Approach:** Media queries — `<900px`: sidebar becomes slide-in drawer; `<600px`: single-column with sticky bottom player. Minimum tap targets 44px.  
**Effort:** ~1 hr

#### P2-R5: History Timeline View
**Approach:** New `Queue | Lyrics | Search | History` tab. Backed by new `GET /api/v2/history` endpoint reading `$HISTORY_FILE`. Shows reverse-chronological list with timestamps, play count badges, and click-to-replay.  
**Effort:** ~3 hrs (server endpoint + UI tab)

#### P2-R6: Playback Speed UI Control
**Current state:** Speed shown as text, no UI control to change it.  
**Fix:** Add speed preset buttons (`0.5× 0.75× 1× 1.25× 1.5× 2×`) or a range slider in the Now Playing card.  
**Effort:** ~30 min

#### P2-R7: Auto-DJ Status & Toggle in Web UI
**Current state:** Auto-DJ only accessible via CLI.  
**Fix:** Show toggle button in sidebar. When active, show "Auto-DJ: ON — seeded from [track]".  
**Effort:** ~30 min

---

## Phase 3 — Feature Expansion 📋 Planned

### Tier 1 — High Impact, Low Effort

| Feature | Why | Effort |
|---------|-----|--------|
| **Queue dedup O(1)** | Replace O(n²) scan in `do_queue_dedup` with awk associative array | 10 min |
| **Live search suggestions** | Debounced as-you-type suggestions below cmd-bar via `/api/v2/search?q=&limit=5` | 1 hr |
| **Keyboard shortcut help panel** | Press `?` to show all shortcuts — improves discoverability | 30 min |
| **`/api/v2/history` endpoint** | Returns paginated play history JSON — needed for history tab | 1 hr |
| **Speed UI control** | (see P2-R6 above) | 30 min |

### Tier 2 — High Impact, Medium Effort

| Feature | Why | Effort |
|---------|-----|--------|
| **Waveform visualizer** | Visual feedback; major UX differentiator | 2 hrs |
| **Mobile responsive layout** | Large % of users browse from phone | 1 hr |
| **Offline PWA caching** | Service worker for HTML/CSS/JS; localStorage for state | 3 hrs |
| **Drag-and-drop backend sync** | Queue reorder must persist to mpv | 30 min |
| **Shareable links** | Generate URLs that open mox at a specific track/queue (base64 encoded state) | 2 hrs |
| **Smart queue — related track append** | Auto-append related tracks when queue near end (extend Auto-DJ) | 2 hrs |
| **Playback history timeline** | Scrollable listening history with filter, search, replay | 3 hrs |

### Tier 3 — Architecture & Long-term

| Feature | Why | Effort |
|---------|-----|--------|
| **Modularize mox.sh → lib/** | Split 4,552-line monolith into ~15 focused modules | 1–2 days |
| **Structured API error codes** | Add `"code"` field to all error responses for programmatic handling | 2 hrs |
| **Plugin manifest system v1** | Structured plugin declarations with permission scope | 3 days |
| **Schedule/alarm UI** | Web UI for `mox schedule` — play music at specific times | 2 hrs |
| **OTP auth for web UI** | TOTP-based auth instead of static PIN | 4 hrs |
| **Equalizer visual UI** | SVG frequency band sliders driving mpv `af` filter chain | 4 hrs |
| **Desktop app wrapper (Tauri)** | System tray, global hotkeys, media key integration | 1–2 weeks |

---

## Remaining Issues Tracker

### 🔴 Must Fix (Security / Correctness)

None. All critical issues are resolved.

### 🟠 Should Fix (UX Gaps)

| # | Issue | Fix | Effort |
|---|-------|-----|--------|
| U1 | Drag-and-drop is visual-only — queue doesn't actually reorder in mpv | Add `ondrop` → `qmove` API call | 30 min |
| U2 | Command palette doesn't auto-focus input on open | One-line JS fix | 5 min |
| U3 | `window.moxSearchResults` is a global collision risk | Scope to a module closure | 15 min |

### 🟡 Nice to Fix (Tech Debt)

| # | Issue | Fix | Effort |
|---|-------|-----|--------|
| T1 | `do_queue_dedup` is O(n²) | Replace with awk associative array | 10 min |
| T2 | `search_tracks()` calls `mox search` subprocess — slow if no API key | Could call search functions directly if server had access to YouTube API key | Medium |
| T3 | mox.sh is still a 4,552-line monolith | Modularize into `src/lib/` | 1–2 days |
| T4 | Google Fonts loaded from CDN (privacy + offline) | Self-host woff2 files | 1 hr |
| T5 | No `X-Request-ID` or structured request logging | Add UUID logging for request tracing | 30 min |

---

## Architecture — Current vs. Target

### Current Architecture
```
mox.sh (4,552 lines) ──────────── single zsh monolith
    └── mpv (IPC via socat + Unix socket)
    └── yt-dlp / YouTube API / Invidious

music_ui_server.py (1,610 lines) ── Python HTTP bridge
    └── reads mpv socket directly
    └── serves music_ui.html

music_ui.html (2,297 lines) ────── single-file SPA
    └── inline CSS + JS
    └── SSE for real-time updates
```

### Target Architecture (Phase 4)
```
src/
├── mox.sh              ── dispatcher only (~200 lines)
├── lib/
│   ├── core.sh         ── paths, config, logging, colors
│   ├── lock.sh         ── locking primitives
│   ├── daemon.sh       ── daemon lifecycle
│   ├── ipc.sh          ── IPC helpers
│   ├── search.sh       ── YouTube/Invidious/yt-dlp search
│   ├── queue.sh        ── queue operations
│   ├── playback.sh     ── transport controls
│   ├── lyrics.sh       ── lyrics sync
│   ├── history.sh      ── history/likes/bookmarks
│   ├── playlist.sh     ── txt/m3u playlists
│   ├── audio.sh        ── volume/EQ/normalize
│   ├── ui.sh           ── bar/status/art terminal UI
│   ├── web.sh          ── uxi/browser management
│   └── plugins.sh      ── plugin loader
├── music_ui_server.py  ── (unchanged location)
└── music_ui.html       ── (unchanged location, or split to src/web/)
```

---

## API Surface — Current

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | — | Serves `music_ui.html` with CSRF cookie |
| GET | `/api/state` `/api/v2/state` | CSRF | Full player state JSON |
| GET | `/api/events` `/api/v2/events` | CSRF | SSE stream |
| POST | `/api/cmd` `/api/v2/cmd` | CSRF + Auth | Send command |
| POST | `/api/play` `/api/v2/play` | CSRF + Auth | Play by query |
| GET | `/api/v2/search?q=` | CSRF | Search tracks |
| GET | `/api/v2/health` | — | Health check |
| GET | `/api/auth` | — | Auth status |
| POST | `/api/auth` | — | Submit PIN |
| GET | `/manifest.webmanifest` | — | PWA manifest |

## API Surface — Planned (Phase 3)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/history?page=&limit=` | Paginated play history |
| POST | `/api/v2/queue/reorder` | Drag-and-drop queue move |
| GET | `/api/v2/playlists` | List saved playlists |
| GET | `/api/v2/likes` | Liked tracks |

---

## Security Model — Current State

```
Browser ──[HTTPS (localhost)]──► Python server
         X-Mox-Token: <CSRF_TOKEN>        ← validates every mutating request
         Cookie: mox_token=<CSRF_TOKEN>   ← JS-readable, set by server on page load
         Cookie: mox_auth=<AUTH_TOKEN>    ← HttpOnly, only set after valid PIN

Python server ──[Unix socket]──► mpv
             JSON IPC commands             ← explicit arg arrays, no shell=True
```

**Headers on all responses:**
- `Content-Security-Policy` (strict, no external scripts)
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`

**Rate limiting:** 10 req/sec per IP (sliding window)

---

## AI Agent Execution Instructions

### Coding Standards
- **Shell:** `local` for all function vars. Quote all expansions. Never `source "$CONFIG_FILE"` directly — always use `_load_config`.
- **Python:** Type hints on all functions. Docstrings for public functions. PEP 8.
- **JS:** Vanilla only. No frameworks. `data-*` attributes for state. CSS custom properties for all colors.

### Non-Negotiable Safety Rules
1. **Never `source "$CONFIG_FILE"` directly** — always call `_load_config`
2. **Never add `shell=True`** to subprocess calls in the Python server
3. **All mutating web API calls go through `_validate_csrf()`**
4. **All mpv property queries in `do_bar()` use `_get_multi()`** — never individual `_get()` calls in the hot loop
5. **Never change existing file paths in `~/music_system/`** — backward compatibility is mandatory
6. **Never break existing CLI commands** — all 80+ commands must continue working
7. **Run `py -m py_compile music_ui_server.py`** before committing any server changes

### Where Things Live
- Shell lib modules → `src/lib/*.sh` (Phase 4)
- Web component files → `src/web/` (Phase 4)
- Tests → `tests/` with `test-` prefix
- Scratch/temp → `~/music_system/data/` (never `/tmp` for persistent state)

### Commit Format
`[area] brief description`  
e.g.: `[security] replace global rate limiter with per-IP sliding window`

---

## Next Actions (Prioritized)

1. **P2-R2 — Command palette auto-focus** (5 min) — one JS line
2. **P2-R1 — Drag-and-drop backend sync** (30 min) — `ondrop` → `qmove` API
3. **P2-R6 — Speed UI control** (30 min) — preset buttons in Now Playing card  
4. **P2-R7 — Auto-DJ toggle in web UI** (30 min) — sidebar toggle button
5. **P2-R4 — Mobile responsive layout** (1 hr) — media queries
6. **P2-R5 — History timeline** (3 hrs) — new tab + `/api/v2/history`
7. **P2-R3 — Waveform visualizer** (2 hrs) — Web Audio API canvas
8. **T1 — Queue dedup O(1)** (10 min) — awk associative array

> **Approve any item above to begin execution immediately.**
