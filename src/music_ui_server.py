#!/usr/bin/env python3
"""
music_ui_server.py — bridge server between the mox CLI (mpv IPC) and music_ui.html

Connects to mpv's Unix domain socket, exposes HTTP endpoints:
  GET  /              → serves music_ui.html
  GET  /api/state     → full player state JSON (title, pos, dur, paused, volume, queue, lyrics…)
  GET  /api/events    → Server-Sent Events stream for state changes
  POST /api/cmd       → send a command (body: {"cmd": "pause"} or {"cmd": "seek +10"})
  POST /api/play      → play by query (body: {"query": "..."})
  GET  /api/v2/search → search tracks for the web UI (query param: q)
  GET  /api/v2/history → paginated play history (page, limit)
  GET  /api/v2/health → lightweight server/mpv health status

Lyrics are fetched from lrclib.net and cached per track. /api/state never blocks on lyrics;
returns cached or "loading" state. Background prefetcher keeps cache warm.
"""

import http.server
import json
import logging
import os
import re
import secrets
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict, deque

# Configure logging
def _setup_logging():
    """Set up logging with safe fallback for test environments."""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Try to add file handler, but don't fail if we can't
    try:
        log_dir = os.path.expanduser('~/music_system/data')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(os.path.join(log_dir, 'server.log')))
    except (OSError, PermissionError):
        # In test environments or restricted environments, just use stdout
        pass
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

_setup_logging()
logger = logging.getLogger('mox-server')

# Secure path handling with validation
def _validate_music_root(path):
    """Validate and sanitize MUSIC_ROOT path."""
    if not path:
        return None
    
    # Reject obvious path traversal attempts
    if '..' in path or path.startswith('/etc/') or path.startswith('/root/'):
        return None
    
    # Expand user path safely
    expanded = os.path.expanduser(path)
    
    # Resolve to absolute path
    try:
        resolved = os.path.abspath(expanded)
    except (OSError, ValueError):
        return None
    
    # In test mode, allow any path for testing purposes
    if os.environ.get('MOX_TEST_MODE'):
        return resolved
    
    # Ensure it's within user's home directory for security
    home_dir = os.path.expanduser("~")
    if not resolved.startswith(home_dir):
        return None
    
    return resolved

# Validate MUSIC_ROOT path
music_root_env = os.environ.get("MUSIC_ROOT", "~/music_system")
MUSIC_ROOT = _validate_music_root(music_root_env)
if not MUSIC_ROOT:
    print("❌ Error: Invalid MUSIC_ROOT path", file=sys.stderr)
    sys.exit(1)

SOCKET_PATH = os.path.join(MUSIC_ROOT, "socket", "mpv.sock")
HISTORY_FILE = os.path.join(MUSIC_ROOT, "data", "history")
HTML_DIR = os.path.dirname(os.path.abspath(__file__))
CSRF_TOKEN = secrets.token_urlsafe(32)
AUTH_TOKEN = secrets.token_urlsafe(32)
UXI_AUTH_ENABLED = os.environ.get("UXI_AUTH") == "1"
UXI_AUTH_PIN = f"{secrets.randbelow(1000000):06d}" if UXI_AUTH_ENABLED else ""
CSP_HEADER = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "script-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://img.youtube.com; "
    "connect-src 'self' https: http:; "
    "media-src 'self' https: http: blob:; "
    "frame-ancestors 'none'"
)

# Validate port number
try:
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7700
    if PORT < 1024 or PORT > 65535:
        print("❌ Error: Port must be between 1024-65535", file=sys.stderr)
        sys.exit(1)
except (ValueError, IndexError):
    if os.environ.get('MOX_TEST_MODE'):
        PORT = 7700
    else:
        print("❌ Error: Invalid port number", file=sys.stderr)
        sys.exit(1)


def _allowed_origin():
    return f"http://127.0.0.1:{PORT}"

# ── dependency and environment checks ─────────────────────────────────────────
def check_dependencies():
    """Check for required dependencies and environment setup."""
    errors = []
    
    # Check Python version
    if sys.version_info < (3, 6):
        errors.append("Python 3.6 or higher is required")
    
    # Check if music system directory exists
    if not os.path.exists(MUSIC_ROOT):
        try:
            os.makedirs(MUSIC_ROOT, mode=0o755, exist_ok=True)
            os.makedirs(os.path.join(MUSIC_ROOT, "socket"), mode=0o755, exist_ok=True)
            os.makedirs(os.path.join(MUSIC_ROOT, "data"), mode=0o755, exist_ok=True)
            logger.info(f"Created music system directory: {MUSIC_ROOT}")
        except OSError as e:
            errors.append(f"Cannot create music system directory {MUSIC_ROOT}: {e}")
    
    # Check if socket directory exists and is writable
    socket_dir = os.path.dirname(SOCKET_PATH)
    if not os.path.exists(socket_dir):
        try:
            os.makedirs(socket_dir, mode=0o755, exist_ok=True)
        except OSError as e:
            errors.append(f"Cannot create socket directory {socket_dir}: {e}")
    
    # Test write permissions
    try:
        test_file = os.path.join(MUSIC_ROOT, "data", ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except (OSError, IOError) as e:
        errors.append(f"No write permission in music system directory: {e}")
    
    if errors:
        logger.error("Environment check failed")
        for error in errors:
            logger.error(f"  {error}")
        print("❌ Environment check failed:", file=sys.stderr)
        for error in errors:
            print(f"   {error}", file=sys.stderr)
        print("\nPlease run the installation script: ./install.sh", file=sys.stderr)
        sys.exit(1)
    
    logger.info("Environment check passed")

# Run dependency check on import (unless in test mode)
if not os.environ.get('MOX_TEST_MODE'):
    check_dependencies()

# ── mpv IPC (with request_id for multi-line response handling) ─────────────────

_mpv_request_id = 0
_mpv_request_id_lock = threading.Lock()
_mpv_persistent_lock = threading.Lock()
_mpv_persistent_sock = None
_mpv_persistent_buf = b""


def _next_request_id():
    global _mpv_request_id
    with _mpv_request_id_lock:
        _mpv_request_id += 1
        return _mpv_request_id


def mpv_command(cmd_list, timeout=5):
    """
    Send a JSON command to mpv IPC socket, return parsed response.
    mpv can emit multiple JSON lines (event notifications) before the response.
    Read lines in a loop until finding one with request_id or error matching our request.
    """
    if not isinstance(cmd_list, list) or not cmd_list:
        logger.error(f"Invalid command list: {cmd_list}")
        return {"error": "invalid command format"}
    
    req_id = _next_request_id()
    sock = None
    
    try:
        # Validate socket path exists
        if not os.path.exists(SOCKET_PATH):
            logger.warning(f"MPV socket not found: {SOCKET_PATH}")
            return {"error": "mpv socket not found"}
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(SOCKET_PATH)
        
        payload = json.dumps({"command": cmd_list, "request_id": req_id}) + "\n"
        sock.sendall(payload.encode('utf-8'))
        
        logger.debug(f"Sent MPV command: {cmd_list}")

        buf = b""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    
                    try:
                        obj = json.loads(line.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"Failed to parse MPV response: {e}")
                        continue
                    
                    # Response has request_id; events typically don't
                    if obj.get("request_id") == req_id:
                        logger.debug(f"MPV response: {obj}")
                        return obj
                    # Error response may have request_id
                    if "error" in obj and obj.get("request_id") == req_id:
                        logger.warning(f"MPV error response: {obj}")
                        return obj
            except socket.timeout:
                logger.warning("MPV command timeout")
                break
        
        logger.warning("MPV command timeout - no response received")
        return {"error": "mpv timeout"}
        
    except (socket.error, OSError, ConnectionRefusedError) as e:
        logger.error(f"MPV connection error: {e}")
        return {"error": "mpv unreachable", "detail": str(e)}
    except Exception as e:
        logger.error(f"MPV command error: {e}")
        return {"error": "mpv error", "detail": str(e)}
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def mpv_get(prop):
    """Get a single mpv property."""
    resp = mpv_command(["get_property", prop])
    if "error" in resp and resp.get("error") not in ("success", None):
        return None
    return resp.get("data")


def mpv_get_batch(props):
    """
    Get multiple mpv properties in a single socket session.
    Returns a dict {prop: value}. Missing/errored props map to None.
    """
    if not props:
        return {}
    if not os.path.exists(SOCKET_PATH):
        return {p: None for p in props}

    global _mpv_persistent_sock, _mpv_persistent_buf
    results = {}
    req_id_to_prop = {}

    try:
        with _mpv_persistent_lock:
            if _mpv_persistent_sock is None:
                _mpv_persistent_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                _mpv_persistent_sock.settimeout(5)
                _mpv_persistent_sock.connect(SOCKET_PATH)
            sock = _mpv_persistent_sock

            # Send all requests back-to-back without waiting for responses.
            for prop in props:
                req_id = _next_request_id()
                req_id_to_prop[req_id] = prop
                payload = json.dumps({"command": ["get_property", prop], "request_id": req_id}) + "\n"
                sock.sendall(payload.encode("utf-8"))

            deadline = time.time() + 5
            while len(results) < len(props) and time.time() < deadline:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    _mpv_persistent_buf += chunk
                    while b"\n" in _mpv_persistent_buf:
                        line, _mpv_persistent_buf = _mpv_persistent_buf.split(b"\n", 1)
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        rid = obj.get("request_id")
                        if rid in req_id_to_prop:
                            prop_name = req_id_to_prop[rid]
                            err = obj.get("error")
                            results[prop_name] = obj.get("data") if err in ("success", None) else None
                except socket.timeout:
                    break
    except (socket.error, OSError, ConnectionRefusedError) as e:
        logger.error(f"MPV batch get error: {e}")
        with _mpv_persistent_lock:
            try:
                if _mpv_persistent_sock:
                    _mpv_persistent_sock.close()
            except Exception:
                pass
            _mpv_persistent_sock = None
            _mpv_persistent_buf = b""

    # Fill in any props that got no response
    for p in props:
        if p not in results:
            results[p] = None
    return results


def mpv_set(prop, value):
    resp = mpv_command(["set_property", prop, value])
    return resp


def mpv_alive():
    return os.path.exists(SOCKET_PATH)


# ── Lyrics cache ─────────────────────────────────────────────────────────────

_LYRICS_CACHE_MAX = 50
_lyrics_cache = OrderedDict()  # {title: result} — bounded to _LYRICS_CACHE_MAX entries
_lyrics_lock = threading.Lock()

LYRICS_LOADING = "loading"      # fetch in progress
LYRICS_NOT_FOUND = "not_found"  # fetch completed, nothing found


def _lyrics_cache_set(title, value):
    """Insert/update a lyrics cache entry, evicting the least recently used."""
    _lyrics_cache.pop(title, None)
    _lyrics_cache[title] = value
    _lyrics_cache.move_to_end(title)
    while len(_lyrics_cache) > _LYRICS_CACHE_MAX:
        oldest, _ = _lyrics_cache.popitem(last=False)
        _lyrics_retry_count.pop(oldest, None)


def _lyrics_cache_pop(title):
    _lyrics_cache.pop(title, None)


def _parse_lrc(lrc_text):
    """Parse LRC format into list of {t: seconds, text: str}."""
    lines = []
    for raw_line in lrc_text.split("\n"):
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)", raw_line)
        if m:
            mins, secs, text = m.groups()
            t = int(mins) * 60 + float(secs)
            lines.append({"t": round(t, 2), "text": text.strip()})
    lines.sort(key=lambda x: x["t"])
    return lines


def _clean_lyrics_title(title):
    """Aggressively clean a YouTube title for lyrics search."""
    t = title
    # Strip common YouTube suffixes (parenthetical and bracketed)
    for pat in [
        r'\(Official[^)]*\)', r'\(Lyrics[^)]*\)', r'\(Audio[^)]*\)',
        r'\(Video[^)]*\)', r'\(Visuali[sz]er[^)]*\)', r'\(Full Song[^)]*\)',
        r'\(HD[^)]*\)', r'\(HQ[^)]*\)',
        r'\[Official[^]]*\]', r'\[Lyrics[^]]*\]', r'\[Audio[^]]*\]',
        r'\[Video[^]]*\]', r'\[HD[^]]*\]', r'\[HQ[^]]*\]',
    ]:
        t = re.sub(pat, '', t, flags=re.IGNORECASE)
    # Replace underscores with spaces (common in Bollywood YouTube titles)
    t = t.replace('_', ' ')
    # Remove year patterns like (1971) or standalone 4-digit years
    t = re.sub(r'\(\d{4}\)', '', t)
    t = re.sub(r'\b(19|20)\d{2}\b', '', t)
    # Remove everything after pipe
    t = t.split('|')[0]
    # Remove hashtags
    t = re.sub(r'#\S+', '', t)
    # Remove "a trib..." suffixes, "full movie/song"
    t = re.sub(r'\ba trib\w*\b.*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bfull movie\b.*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bfull song\b.*', '', t, flags=re.IGNORECASE)
    # Collapse whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _lrclib_request(url):
    """Make a request to lrclib.net. Returns parsed JSON or None.
    Falls back to curl if urllib hits SSL cert issues (common on macOS)."""
    # Try urllib first
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mox-cli/6.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except ssl.SSLError:
        pass
    except urllib.error.URLError as e:
        if "SSL" not in str(e) and "CERTIFICATE" not in str(e).upper():
            return None
    except Exception:
        return None
    # Fallback: use curl (uses system cert store, works reliably on macOS)
    try:
        result = subprocess.run(
            ["curl", "-sf", "--max-time", "8", "-H", "User-Agent: mox-cli/6.0", url],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def _try_lyrics_search(query, artist=""):
    """Try lyrics search on lrclib.net. Returns (synced_lrc, plain_lrc) or (None, None)."""
    enc_q = urllib.parse.quote(query)

    # Try search endpoint
    api_url = f"https://lrclib.net/api/search?q={enc_q}"
    if artist:
        api_url += f"&artist_name={urllib.parse.quote(artist)}"
    data = _lrclib_request(api_url)
    if data and isinstance(data, list) and len(data) > 0:
        synced = data[0].get("syncedLyrics") or ""
        plain = data[0].get("plainLyrics") or ""
        if synced or plain:
            return synced, plain

    # Try direct-get endpoint (exact match, often more reliable)
    if artist:
        get_url = f"https://lrclib.net/api/get?artist_name={urllib.parse.quote(artist)}&track_name={enc_q}"
        data = _lrclib_request(get_url)
        if data and isinstance(data, dict):
            synced = data.get("syncedLyrics") or ""
            plain = data.get("plainLyrics") or ""
            if synced or plain:
                return synced, plain

    return None, None


def fetch_lyrics(title):
    """
    Fetch lyrics from lrclib.net with multi-attempt title cleaning. Cache result.
    Never blocks /api/state — call only from background thread.
    """
    with _lyrics_lock:
        if title in _lyrics_cache:
            _lyrics_cache.move_to_end(title)
            return _lyrics_cache[title]

    if not title:
        return None

    cleaned = _clean_lyrics_title(title)

    # Split "Artist - Title" if present
    artist = ""
    track = cleaned
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        artist = parts[0].strip()
        track = parts[1].strip()

    # Multi-attempt search: progressively simpler queries
    synced_lrc, plain_lrc = None, None
    attempts = [
        (track, artist),
        (cleaned, ""),
    ]
    words = cleaned.split()
    if len(words) > 8:
        attempts.append((' '.join(words[:8]), ""))
    if cleaned != title:
        attempts.append((title, ""))

    for q, a in attempts:
        synced_lrc, plain_lrc = _try_lyrics_search(q, a)
        if synced_lrc or plain_lrc:
            break

    result = LYRICS_NOT_FOUND
    if synced_lrc:
        lines = _parse_lrc(synced_lrc)
        if lines:
            result = {"synced": True, "lines": lines}
    if result == LYRICS_NOT_FOUND and plain_lrc:
        result = {
            "synced": False,
            "lines": [{"t": 0, "text": line} for line in plain_lrc.split("\n") if line.strip()]
        }

    with _lyrics_lock:
        _lyrics_cache_set(title, result)
    return result


def get_lyrics_cached(title):
    """Return cached lyrics for title, or LYRICS_LOADING sentinel. Never blocks."""
    with _lyrics_lock:
        if title in _lyrics_cache:
            _lyrics_cache.move_to_end(title)
            return _lyrics_cache[title]
    return LYRICS_LOADING


# ── Background lyrics prefetcher ─────────────────────────────────────────────

_last_lyrics_title = ""
_lyrics_retry_count = {}  # {title: int} — how many retries for LYRICS_NOT_FOUND


def _lyrics_bg_fetch():
    """Runs in background thread — prefetches lyrics when track changes.
    Only polls mpv when the SSE state indicates something is playing,
    avoiding wasted socket connections when idle."""
    global _last_lyrics_title
    while True:
        try:
            # Only open a socket if mpv is alive and something is playing.
            # Use the cached state from the SSE poll loop to avoid an extra
            # socket connection every 3 s when idle.
            if mpv_alive() and _last_state_json:
                try:
                    cached_state = json.loads(_last_state_json)
                    title = cached_state.get("title", "")
                    is_playing = cached_state.get("playing", False)
                except (json.JSONDecodeError, TypeError):
                    title = ""
                    is_playing = False

                if is_playing and title and title != "nothing playing":
                    cached = get_lyrics_cached(title)
                    title_changed = (title != _last_lyrics_title)
                    retries = _lyrics_retry_count.get(title, 0)
                    should_retry = (cached == LYRICS_NOT_FOUND and retries < 3)
                    if title_changed or should_retry:
                        if title_changed:
                            with _lyrics_lock:
                                _lyrics_cache_pop(title)
                            _lyrics_retry_count[title] = 0
                        else:
                            _lyrics_retry_count[title] = retries + 1
                            with _lyrics_lock:
                                _lyrics_cache_pop(title)
                        _last_lyrics_title = title
                        fetch_lyrics(title)
        except Exception:
            pass
        time.sleep(3)


threading.Thread(target=_lyrics_bg_fetch, daemon=True).start()


# ── Build full state (never blocks on lyrics) ─────────────────────────────────

def _fetch_full_state():
    """
    Return a dict with the full player state for the UI.
    Uses a single socket session to fetch all mpv properties (batch).
    Lyrics: returns cached value or LYRICS_LOADING -- never blocks on fetch.
    """
    if not mpv_alive():
        return {
            "alive": False, "playing": False, "paused": True,
            "title": "nothing playing", "pos": 0, "dur": 0,
            "volume": 80, "speed": 1.0, "queue": [], "currentIdx": -1,
            "repeat": False, "loopOne": False, "autoDj": False,
            "autoDjSeed": "", "lyrics": None, "bufferPct": 0,
        }

    # Fetch all properties in one socket session.
    props = mpv_get_batch([
        "media-title", "time-pos", "duration", "pause",
        "volume", "speed", "loop-playlist", "loop-file", "playlist-playing-pos",
        "playlist", "demuxer-cache-state",
    ])

    title        = props.get("media-title") or ""
    pos          = props.get("time-pos") or 0
    dur          = props.get("duration") or 0
    paused       = props.get("pause")
    volume       = props.get("volume") or 80
    speed        = props.get("speed") or 1.0
    loop_playlist = props.get("loop-playlist") or "no"
    loop_file    = props.get("loop-file") or "no"
    playlist_pos = props.get("playlist-playing-pos")
    cache_state  = props.get("demuxer-cache-state") or {}

    pl_data = props.get("playlist") or []
    if not isinstance(pl_data, list):
        pl_data = []

    queue = []
    for item in pl_data:
        t = item.get("title") or item.get("filename", "")
        queue.append({"title": t, "url": item.get("filename", ""), "current": item.get("current", False)})

    try:
        pos = float(pos)
    except (TypeError, ValueError):
        pos = 0
    try:
        dur = float(dur)
    except (TypeError, ValueError):
        dur = 0
    try:
        volume = float(volume)
    except (TypeError, ValueError):
        volume = 80
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        speed = 1.0

    current_idx = -1
    if playlist_pos is not None:
        try:
            current_idx = int(playlist_pos)
        except (TypeError, ValueError):
            current_idx = -1

    is_paused = paused is True or paused == "true" or paused == "yes"
    is_playing = bool(title) and title != "nothing playing"
    buffer_pct = 0
    if isinstance(cache_state, dict) and dur:
        ranges = cache_state.get("seekable-ranges") or []
        if ranges:
            try:
                cache_end = float(ranges[-1].get("end", 0))
                buffer_pct = max(0, min(100, round(cache_end / dur * 100)))
            except (TypeError, ValueError, ZeroDivisionError):
                buffer_pct = 0

    autodj = os.path.exists(os.path.join(MUSIC_ROOT, "data", "autodj_enabled"))
    autodj_seed = _latest_history_title()

    # Never block: use cache or loading sentinel
    lyrics_data = get_lyrics_cached(title) if title else None

    return {
        "alive": True,
        "playing": is_playing,
        "paused": is_paused,
        "title": title or "nothing playing",
        "pos": round(pos, 1),
        "dur": round(dur, 1),
        "volume": round(volume),
        "speed": round(speed, 2),
        "queue": queue,
        "currentIdx": current_idx,
        "repeat": loop_playlist not in ("no", "", False),
        "loopOne": loop_file not in ("no", "", False),
        "autoDj": autodj,
        "autoDjSeed": autodj_seed,
        "lyrics": lyrics_data,
        "bufferPct": buffer_pct,
    }


RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 1.0  # seconds

# Per-IP rate limiting: each IP gets its own sliding window.
_rate_limit_buckets = {}  # {ip_str: deque[float]}
_rate_limit_lock = threading.Lock()


def _check_rate_limit(client_ip="unknown"):
    """Return True if request is allowed, False if rate limited (per-IP sliding window)."""
    now = time.monotonic()
    with _rate_limit_lock:
        if client_ip not in _rate_limit_buckets:
            _rate_limit_buckets[client_ip] = deque()
        bucket = _rate_limit_buckets[client_ip]
        while bucket and now - bucket[0] >= RATE_LIMIT_WINDOW:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_REQUESTS:
            return False
        bucket.append(now)
        return True


class MpvStateCache:
    def __init__(self, ttl=0.25):
        self._state = None
        self._expires_at = 0
        self._ttl = ttl
        self._lock = threading.Lock()

    def invalidate(self):
        with self._lock:
            self._expires_at = 0

    def get(self):
        now = time.monotonic()
        with self._lock:
            if self._state is None or now >= self._expires_at:
                self._state = _fetch_full_state()
                self._expires_at = now + self._ttl
            return dict(self._state)


_state_cache = MpvStateCache()


def get_full_state():
    return _state_cache.get()

BLOCKED_QUERY_PATTERNS = (
    r'[;&|`$]',     # shell metacharacters
    r'\.\./',       # path traversal
    r'<[^>]+>',     # HTML tags
    r'javascript:', # JS injection
    r'data:',       # data URIs
    r'\x00',        # null bytes
)


def _validate_query(query):
    if not isinstance(query, str) or not query.strip():
        return False, "empty query"
    if len(query) > 500:
        return False, "query too long"
    for pattern in BLOCKED_QUERY_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "invalid characters in query"
    return True, None


def _parse_search_output(stdout):
    """Parse mox search table-ish output into title/duration/url rows."""
    results = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or "http" not in line:
            continue
        parts = [part.strip() for part in line.split(" | ")]
        if len(parts) >= 3:
            title, duration, url = parts[0], parts[1], parts[-1]
        else:
            url_match = re.search(r'https?://\S+', line)
            if not url_match:
                continue
            url = url_match.group(0)
            title = line[:url_match.start()].strip(" -|\t") or url
            duration = ""
        if re.match(r'^https?://', url):
            results.append({"title": title, "duration": duration, "url": url})
    return results[:20]


def search_tracks(query):
    """Run the CLI search path and return structured rows for the web UI."""
    valid, err = _validate_query(query)
    if not valid:
        return {"ok": False, "msg": err, "results": []}

    try:
        result = subprocess.run(
            ["mox", "search", query],
            capture_output=True,
            text=True,
            timeout=30,  # yt-dlp can be slow; 30s gives enough headroom
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": "search timed out (try setting YOUTUBE_API_KEY for instant results)", "results": []}
    except Exception as e:
        logger.error(f"Search command failed: {e}")
        return {"ok": False, "msg": "search failed", "results": []}

    rows = _parse_search_output(result.stdout)
    if result.returncode != 0 and not rows:
        return {"ok": False, "msg": "search failed", "results": []}
    return {"ok": True, "msg": "ok", "results": rows}


def _read_history_rows() -> list:
    """Read the mox TSV history file into normalized dictionaries."""
    rows = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line = raw_line.rstrip("\n")
                if not line:
                    continue
                parts = line.split("\t", 2)
                if len(parts) != 3:
                    continue
                played_at, title, url = parts
                rows.append({
                    "playedAt": played_at,
                    "title": title or "unknown",
                    "url": url,
                })
    except FileNotFoundError:
        return []
    except OSError as e:
        logger.error(f"Failed to read history: {e}")
        return []
    return rows


def _latest_history_title() -> str:
    """Return the most recent history title for Auto-DJ seed display."""
    rows = _read_history_rows()
    return rows[-1]["title"] if rows else ""


def get_history(page: int = 1, limit: int = 50) -> dict:
    """Return paginated reverse-chronological play history."""
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        limit = 50

    rows = _read_history_rows()
    counts = {}
    for item in rows:
        key = (item["url"] or item["title"]).lower()
        counts[key] = counts.get(key, 0) + 1

    ordered = list(reversed(rows))
    start = (page - 1) * limit
    page_rows = ordered[start:start + limit]
    for item in page_rows:
        key = (item["url"] or item["title"]).lower()
        item["playCount"] = counts.get(key, 1)

    return {
        "ok": True,
        "page": page,
        "limit": limit,
        "total": len(rows),
        "results": page_rows,
    }


ALLOWED_CMD_ACTIONS = frozenset([
    "pause", "pp", "next", "mn", "prev", "mb", "stop", "seek", "vol", "volume",
    "speed", "repeat", "rp", "repeat-one", "ro", "shuffle", "playlist-play-index",
    "clear", "norm", "like", "autodj", "eq", "play", "add", "mox", "qrm", "qmove",
])


def _validate_cmd(cmd_str):
    """Return (valid, error_msg). Valid means cmd action is whitelisted and safe."""
    cmd_str = (cmd_str or "").strip()
    if not cmd_str:
        return False, "empty command"

    # Strict command length limit
    if len(cmd_str) > 200:
        return False, "command too long"
    
    # Block shell injection metacharacters and control characters.
    # Using a blocklist (not allowlist) so non-ASCII arguments (e.g. song titles
    # with accented or CJK characters) are not rejected.
    BLOCKED_CMD_CHARS = set('&|;`$(){}[]<>"\'\\\n\r\t\x00')
    if any(ch in BLOCKED_CMD_CHARS for ch in cmd_str):
        return False, "invalid characters in command"
    
    parts = cmd_str.split()
    action = parts[0]
    if action not in ALLOWED_CMD_ACTIONS:
        return False, f"command not allowed: {action}"
    
    # Validate arguments for specific commands
    if action in ("seek", "vol", "volume", "speed"):
        if len(parts) > 1:
            arg = parts[1]
            # Only allow numeric values with optional +/- prefix
            if not re.match(r'^[+-]?[0-9]+(\.[0-9]+)?$', arg):
                return False, f"invalid argument for {action}: {arg}"
    elif action == "qmove":
        if len(parts) != 3 or not all(re.match(r'^[0-9]+$', arg) for arg in parts[1:]):
            return False, "qmove needs positive integer positions"
    
    return True, None


# ── Handle commands from the UI ──────────────────────────────────────────────

def handle_cmd(cmd_str):
    """Execute an m-style command string against mpv."""
    valid, err = _validate_cmd(cmd_str)
    if not valid:
        return {"ok": False, "msg": err}

    parts = cmd_str.strip().split()
    action = parts[0]

    if action in ("pause", "pp"):
        mpv_command(["cycle", "pause"])
        return {"ok": True, "msg": "toggled pause"}

    elif action in ("next", "mn"):
        mpv_command(["playlist-next"])
        return {"ok": True, "msg": "next track"}

    elif action in ("prev", "mb"):
        mpv_command(["playlist-prev"])
        return {"ok": True, "msg": "previous track"}

    elif action == "stop":
        mpv_command(["stop"])
        return {"ok": True, "msg": "stopped"}

    elif action == "seek":
        if len(parts) > 1:
            arg = parts[1]
            if arg.startswith("+") or arg.startswith("-"):
                mpv_command(["seek", arg, "relative"])
            else:
                mpv_command(["seek", arg, "absolute"])
            return {"ok": True, "msg": f"seek {arg}"}
        return {"ok": False, "msg": "seek needs argument"}

    elif action in ("vol", "volume"):
        if len(parts) > 1:
            arg = parts[1]
            if arg.startswith("+") or arg.startswith("-"):
                cur = mpv_get("volume") or 80
                try:
                    new_vol = max(0, min(150, float(cur) + float(arg)))
                except (TypeError, ValueError):
                    new_vol = 80
                mpv_set("volume", new_vol)
            else:
                try:
                    mpv_set("volume", max(0, min(150, float(arg))))
                except ValueError:
                    pass
            return {"ok": True, "msg": f"volume {arg}"}
        return {"ok": False, "msg": "vol needs argument"}

    elif action == "speed":
        if len(parts) > 1:
            try:
                s = max(0.25, min(4.0, float(parts[1])))
                mpv_set("speed", s)
                return {"ok": True, "msg": f"speed {s}"}
            except ValueError:
                pass
        return {"ok": False, "msg": "speed needs number"}

    elif action in ("repeat", "rp"):
        cur = mpv_get("loop-playlist") or "no"
        new_val = "no" if cur not in ("no", "", False) else "inf"
        mpv_set("loop-playlist", new_val)
        return {"ok": True, "msg": f"repeat {'on' if new_val == 'inf' else 'off'}"}

    elif action in ("repeat-one", "ro"):
        cur = mpv_get("loop-file") or "no"
        new_val = "no" if cur not in ("no", "", False) else "inf"
        mpv_set("loop-file", new_val)
        return {"ok": True, "msg": f"repeat-one {'on' if new_val == 'inf' else 'off'}"}

    elif action == "shuffle":
        mpv_command(["playlist-shuffle"])
        return {"ok": True, "msg": "shuffled"}

    elif action == "add":
        if len(parts) > 1:
            query = " ".join(parts[1:])
            valid, err = _validate_query(query)
            if not valid:
                return {"ok": False, "msg": err}
            try:
                subprocess.run(
                    ["mox", query, "-a"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                    check=False,
                )
                return {"ok": True, "msg": "queued"}
            except subprocess.TimeoutExpired:
                return {"ok": False, "msg": "queue timed out"}
            except Exception as e:
                return {"ok": False, "msg": f"queue failed: {str(e)}"}
        return {"ok": False, "msg": "add needs query"}

    elif action == "playlist-play-index":
        if len(parts) > 1:
            try:
                idx = int(parts[1])
                mpv_set("playlist-pos", idx)
                return {"ok": True, "msg": f"playing track {idx + 1}"}
            except ValueError:
                pass
        return {"ok": False, "msg": "need index"}

    elif action == "qmove":
        if len(parts) > 2:
            try:
                from_idx = int(parts[1]) - 1
                to_idx = int(parts[2]) - 1
                if from_idx < 0 or to_idx < 0:
                    return {"ok": False, "msg": "qmove positions must be positive"}
                mpv_command(["playlist-move", from_idx, to_idx])
                return {"ok": True, "msg": f"moved track {parts[1]} to {parts[2]}"}
            except ValueError:
                pass
        return {"ok": False, "msg": "qmove needs from/to positions"}

    elif action == "clear":
        mpv_command(["playlist-clear"])
        return {"ok": True, "msg": "queue cleared"}

    elif action in ("norm",):
        mpv_command(["af", "toggle", "dynaudnorm"])
        return {"ok": True, "msg": "toggled normalize"}

    elif action == "like":
        # Use subprocess for safer execution
        try:
            subprocess.Popen(["mox", "like"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return {"ok": True, "msg": "liked"}
        except Exception as e:
            return {"ok": False, "msg": f"like failed: {str(e)}"}

    elif action == "autodj":
        # Use subprocess for safer execution
        try:
            subprocess.Popen(["mox", "autodj"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return {"ok": True, "msg": "toggled autodj"}
        except Exception as e:
            return {"ok": False, "msg": f"autodj failed: {str(e)}"}

    elif action == "eq":
        preset = parts[1] if len(parts) > 1 else "flat"
        # Whitelist valid presets
        valid_presets = {"flat", "bass", "treble", "vocal", "loud"}
        if preset not in valid_presets:
            return {"ok": False, "msg": f"invalid eq preset: {preset}"}
        
        mpv_command(["af", "set", ""])
        if preset != "flat":
            try:
                subprocess.Popen(["mox", "eq", preset], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            except Exception as e:
                return {"ok": False, "msg": f"eq failed: {str(e)}"}
        return {"ok": True, "msg": f"eq {preset}"}

    # For other whitelisted commands, use subprocess for safety
    if action in ALLOWED_CMD_ACTIONS:
        try:
            if action == "mox":
                # Special handling for mox subcommands
                rest = cmd_str[len(action):].strip()
                if rest:
                    # Validate subcommand arguments
                    if not re.match(r'^[a-zA-Z0-9\s\-+.:]+$', rest):
                        return {"ok": False, "msg": "invalid mox arguments"}
                    subprocess.Popen(["mox"] + rest.split(), 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["mox"], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
            else:
                # Execute as mox subcommand
                subprocess.Popen(["mox"] + parts, 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            return {"ok": True, "msg": f"executed: {cmd_str}"}
        except Exception as e:
            return {"ok": False, "msg": f"command failed: {str(e)}"}
    
    return {"ok": False, "msg": f"unknown command: {action}"}


# ── SSE: connection state machine ─────────────────────────────────────────────
#
# Each SSE connection moves through these states:
#
#   CONNECTING  → connection accepted, headers sent, initial state not yet delivered
#   SSE_ACTIVE  → initial state delivered, client is receiving broadcasts
#   SSE_FAILED  → write error detected; connection is being torn down
#   POLLING     → client has fallen back to HTTP polling (no SSE connection)
#
# The server tracks every live SSE connection as an _SseClient object.
# _sse_poll_loop broadcasts to all SSE_ACTIVE clients; FAILED ones are pruned.

class _SseState:
    CONNECTING = "CONNECTING"
    SSE_ACTIVE  = "SSE_ACTIVE"
    SSE_FAILED  = "SSE_FAILED"
    POLLING     = "POLLING"


class _SseClient:
    """Represents one live SSE connection with its state machine."""
    __slots__ = ("wfile", "state", "connected_at")

    def __init__(self, wfile):
        self.wfile = wfile
        self.state = _SseState.CONNECTING
        self.connected_at = time.monotonic()

    def activate(self):
        """Transition CONNECTING → SSE_ACTIVE after initial state is delivered."""
        if self.state == _SseState.CONNECTING:
            self.state = _SseState.SSE_ACTIVE

    def fail(self):
        """Transition any state → SSE_FAILED on write error."""
        self.state = _SseState.SSE_FAILED

    def is_active(self):
        return self.state == _SseState.SSE_ACTIVE

    def send(self, msg_bytes):
        """Write bytes; transitions to SSE_FAILED on any I/O error."""
        try:
            self.wfile.write(msg_bytes)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.fail()
            raise


# Registry of live SSE connections (keyed by id(wfile) for O(1) lookup).
_sse_clients: list[_SseClient] = []
_sse_clients_lock = threading.Lock()
_last_state_json = None
_state_poll_interval = 0.5


def _sse_register(client: _SseClient):
    with _sse_clients_lock:
        _sse_clients.append(client)


def _sse_unregister(client: _SseClient):
    client.fail()
    with _sse_clients_lock:
        try:
            _sse_clients.remove(client)
        except ValueError:
            pass


def _sse_broadcast(data):
    """Send JSON to all SSE_ACTIVE clients; prune failed ones."""
    msg = f"data: {json.dumps(data)}\n\n".encode()
    with _sse_clients_lock:
        dead = []
        for client in _sse_clients:
            if not client.is_active():
                if client.state == _SseState.SSE_FAILED:
                    dead.append(client)
                continue
            try:
                client.send(msg)
            except OSError:
                dead.append(client)
        for c in dead:
            try:
                _sse_clients.remove(c)
            except ValueError:
                pass


def _sse_poll_loop():
    """Background thread: poll mpv state, broadcast on change to SSE_ACTIVE clients."""
    global _last_state_json
    while True:
        try:
            state = get_full_state()
            state_json = json.dumps(state, sort_keys=True)
            if _last_state_json is not None and state_json != _last_state_json:
                _sse_broadcast(state)
            _last_state_json = state_json
        except Exception:
            pass
        time.sleep(_state_poll_interval)


threading.Thread(target=_sse_poll_loop, daemon=True).start()


# ── HTTP Server (ThreadingHTTPServer) ────────────────────────────────────────

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class UXIHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Log to our logger instead of stderr
        logger.info(f"{self.address_string()} - {format % args}")
    
    def log_error(self, format, *args):
        logger.error(f"{self.address_string()} - {format % args}")
    
    def handle_exception(self, e):
        """Handle exceptions in request processing."""
        logger.error(f"Request handling error: {e}", exc_info=True)
        try:
            self.send_error(500, "Internal server error")
        except Exception:
            pass  # Connection might be closed

    def _csrf_enabled(self):
        return not os.environ.get("MOX_TEST_MODE")

    def _read_cookie(self, name):
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            if "=" not in part:
                continue
            key, value = part.strip().split("=", 1)
            if key == name:
                return value
        return None

    def _validate_csrf(self):
        if not self._csrf_enabled():
            return True
        header_token = self.headers.get("X-Mox-Token", "")
        cookie_token = self._read_cookie("mox_token")
        return (
            header_token
            and cookie_token
            and secrets.compare_digest(header_token, CSRF_TOKEN)
            and secrets.compare_digest(cookie_token, CSRF_TOKEN)
        )

    def _validate_auth(self):
        if not UXI_AUTH_ENABLED or os.environ.get("MOX_TEST_MODE"):
            return True
        return secrets.compare_digest(self._read_cookie("mox_auth") or "", AUTH_TOKEN)

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # Validate path to prevent directory traversal
            if '..' in path or path.startswith('//'):
                logger.warning(f"Suspicious path access attempt: {path}")
                self.send_error(400, "Bad request")
                return

            if path == "/" or path == "/index.html":
                self._serve_html()
            elif path in ("/api/state", "/api/v2/state"):
                self._json_response(get_full_state())
            elif path == "/api/auth":
                self._json_response({"authRequired": UXI_AUTH_ENABLED, "authenticated": self._validate_auth()})
            elif path in ("/api/events", "/api/v2/events"):
                self._serve_sse()
            elif path == "/api/v2/search":
                params = urllib.parse.parse_qs(parsed.query)
                query = (params.get("q") or [""])[0]
                self._json_response(search_tracks(query))
            elif path == "/api/v2/history":
                params = urllib.parse.parse_qs(parsed.query)
                page = (params.get("page") or ["1"])[0]
                limit = (params.get("limit") or ["50"])[0]
                self._json_response(get_history(page, limit))
            elif path == "/api/v2/health":
                self._json_response({"ok": True, "mpv": mpv_alive(), "time": int(time.time())})
            elif path in ("/manifest.json", "/manifest.webmanifest"):
                self._serve_manifest()
            else:
                logger.warning(f"404 - Path not found: {path}")
                self.send_error(404)
        except Exception as e:
            self.handle_exception(e)

    def _serve_manifest(self):
        """Serve a tiny PWA manifest without adding a static asset pipeline."""
        body = json.dumps({
            "name": "mox",
            "short_name": "mox",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0a0a0b",
            "theme_color": "#c8ff5a",
            "icons": [],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/manifest+json")
        self.send_header("Content-Length", len(body))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _serve_sse(self):
        """Serve Server-Sent Events stream using the _SseClient state machine."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", _allowed_origin())
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        # CONNECTING: connection accepted, headers sent
        client = _SseClient(self.wfile)
        _sse_register(client)

        # CONNECTING → SSE_ACTIVE: deliver initial state immediately
        try:
            state = get_full_state()
            client.send(f"data: {json.dumps(state)}\n\n".encode())
            client.activate()   # state: SSE_ACTIVE
        except OSError:
            # CONNECTING → SSE_FAILED: client disconnected before first byte
            _sse_unregister(client)
            return

        # SSE_ACTIVE: keep connection open; _sse_poll_loop handles broadcasts.
        # This thread only sends keepalive pings and detects disconnects.
        try:
            while client.is_active():
                time.sleep(30)
                try:
                    client.send(b": keepalive\n\n")
                except OSError:
                    # SSE_ACTIVE → SSE_FAILED
                    break
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            # SSE_FAILED: unregister and let client fall back to POLLING
            _sse_unregister(client)

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # Validate path
            if '..' in path or path.startswith('//'):
                logger.warning(f"Suspicious POST path: {path}")
                self.send_error(400, "Bad request")
                return

            if not self._validate_csrf():
                logger.warning(f"CSRF validation failed for {self.address_string()}")
                self._json_response({"ok": False, "msg": "invalid session token"}, 403)
                return

            if path == "/api/auth":
                self._handle_auth_request()
            elif not self._validate_auth():
                self._json_response({"ok": False, "msg": "PIN required"}, 401)
            elif path in ("/api/cmd", "/api/v2/cmd"):
                self._handle_cmd_request()
            elif path in ("/api/play", "/api/v2/play"):
                self._handle_play_request()
            else:
                logger.warning(f"404 - POST path not found: {path}")
                self.send_error(404)
        except Exception as e:
            self.handle_exception(e)

    def _handle_auth_request(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode(errors="replace") if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json_response({"ok": False, "msg": "invalid JSON"}, 400)
            return
        pin = str(data.get("pin", ""))
        if UXI_AUTH_ENABLED and secrets.compare_digest(pin, UXI_AUTH_PIN):
            self._json_response(
                {"ok": True, "msg": "authenticated"},
                headers={
                    "Set-Cookie": (
                        f"mox_auth={AUTH_TOKEN}; Path=/; SameSite=Strict; HttpOnly"
                    )
                },
            )
        elif not UXI_AUTH_ENABLED:
            self._json_response({"ok": True, "msg": "auth disabled"})
        else:
            self._json_response({"ok": False, "msg": "invalid PIN"}, 401)
    
    def _handle_cmd_request(self):
        """Handle /api/cmd POST requests."""
        try:
            if not _check_rate_limit(self.address_string()):
                logger.warning(f"Rate limit exceeded for {self.address_string()}")
                self._json_response({"ok": False, "msg": "rate limit exceeded"}, 429)
                return
            
            # Validate content length
            length = int(self.headers.get("Content-Length", 0))
            if length > 10000:  # 10KB limit
                logger.warning(f"Request too large: {length} bytes")
                self._json_response({"ok": False, "msg": "request too large"}, 413)
                return
            
            body = self.rfile.read(length).decode(errors="replace") if length else "{}"
            
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in cmd request: {e}")
                self._json_response({"ok": False, "msg": "invalid JSON"}, 400)
                return
            
            # Validate that data is a dict and has cmd field
            if not isinstance(data, dict):
                logger.warning("Request data is not a JSON object")
                self._json_response({"ok": False, "msg": "request must be JSON object"}, 400)
                return
            
            cmd_str = data.get("cmd", "")
            if not cmd_str:
                logger.warning("Missing cmd field in request")
                self._json_response({"ok": False, "msg": "missing cmd field"}, 400)
                return
            
            logger.info(f"Command request: {cmd_str}")
            result = handle_cmd(cmd_str)
            _state_cache.invalidate()
            
            # Return 400 for invalid commands
            if not result.get("ok", False):
                self._json_response(result, 400)
            else:
                self._json_response(result)
            
        except Exception as e:
            logger.error(f"Error handling cmd request: {e}")
            self._json_response({"ok": False, "msg": "internal error"}, 500)
    
    def _handle_play_request(self):
        """Handle /api/play POST requests."""
        try:
            # Validate content length
            length = int(self.headers.get("Content-Length", 0))
            if length > 10000:  # 10KB limit
                logger.warning(f"Play request too large: {length} bytes")
                self._json_response({"ok": False, "msg": "request too large"}, 413)
                return
            
            body = self.rfile.read(length).decode(errors="replace") if length else "{}"
            
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in play request: {e}")
                self._json_response({"ok": False, "msg": "invalid JSON"}, 400)
                return
            
            # Validate that data is a dict
            if not isinstance(data, dict):
                logger.warning("Play request data is not a JSON object")
                self._json_response({"ok": False, "msg": "request must be JSON object"}, 400)
                return
            
            # Check for required query field
            if "query" not in data:
                logger.warning("Missing query field in play request")
                self._json_response({"ok": False, "msg": "missing query field"}, 400)
                return
            
            query = data.get("query", "")
            valid, err = _validate_query(query)
            if valid:
                try:
                    logger.info(f"Play request: {query}")
                    subprocess.run(
                        ["mox", query],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=30,
                        check=False,
                    )
                    _state_cache.invalidate()
                    self._json_response({"ok": True, "msg": f"playing: {query}"})
                except subprocess.TimeoutExpired:
                    self._json_response({"ok": False, "msg": "play timed out"}, 504)
                except Exception as e:
                    logger.error(f"Play command failed: {e}")
                    self._json_response({"ok": False, "msg": f"play failed: {str(e)}"}, 500)
            else:
                self._json_response({"ok": False, "msg": err}, 400)
                
        except Exception as e:
            logger.error(f"Error handling play request: {e}")
            self._json_response({"ok": False, "msg": "internal error"}, 500)

    def _serve_html(self):
        html_path = os.path.join(HTML_DIR, "music_ui.html")
        try:
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Set-Cookie", f"mox_token={CSRF_TOKEN}; Path=/; SameSite=Strict")
            # Security headers
            self.send_header("Content-Security-Policy", CSP_HEADER)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-XSS-Protection", "1; mode=block")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "music_ui.html not found")

    def _json_response(self, data, status=200, headers=None):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", _allowed_origin())
        self.send_header("Cache-Control", "no-cache")
        # Security headers
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", _allowed_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Mox-Token")
        self.end_headers()
    
    def do_PUT(self):
        self.send_error(405, "Method Not Allowed")
    
    def do_DELETE(self):
        self.send_error(405, "Method Not Allowed")
    
    def do_PATCH(self):
        self.send_error(405, "Method Not Allowed")


def main():
    """Main server entry point with comprehensive error handling."""
    server = None
    
    try:
        logger.info("Starting mox UXI server...")
        
        # Check if HTML file exists
        html_path = os.path.join(HTML_DIR, 'music_ui.html')
        if not os.path.exists(html_path):
            logger.error(f"HTML file not found: {html_path}")
            print(f"❌ Error: music_ui.html not found at {html_path}", file=sys.stderr)
            print("Please ensure all files are properly installed.", file=sys.stderr)
            sys.exit(1)
        
        # Validate HTML file is readable
        try:
            with open(html_path, 'r') as f:
                f.read(1)  # Test read
        except (IOError, OSError) as e:
            logger.error(f"Cannot read HTML file: {e}")
            print(f"❌ Error: Cannot read {html_path}: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Try to bind to the port with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                server = ThreadedHTTPServer(("127.0.0.1", PORT), UXIHandler)
                break
            except OSError as e:
                if "Address already in use" in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"Port {PORT} in use, retrying in 2s...")
                        time.sleep(2)
                        continue
                    else:
                        logger.error(f"Port {PORT} still in use after retries")
                        print(f"❌ Error: Port {PORT} is already in use", file=sys.stderr)
                        print(f"Try a different port: python3 {__file__} <port>", file=sys.stderr)
                        sys.exit(1)
                else:
                    raise
        
        logger.info(f"Server bound to port {PORT}")
        print(f"🎵 mox uxi server running → http://127.0.0.1:{PORT}")
        print(f"   mpv socket: {SOCKET_PATH}")
        print(f"   html: {html_path}")
        print(f"   log: ~/music_system/data/server.log")
        print(f"   SSE: GET /api/events")
        if UXI_AUTH_ENABLED:
            print(f"   Web UI PIN: {UXI_AUTH_PIN}")
        print(f"   press Ctrl+C to stop")
        
        # Set up signal handlers for graceful shutdown
        import signal
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            if server:
                server.shutdown()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start server
        logger.info("Server started successfully")
        server.serve_forever()
        
    except OSError as e:
        logger.error(f"OS error starting server: {e}")
        print(f"❌ Error starting server: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("\n🛑 Shutting down server...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if server:
            try:
                logger.info("Shutting down server...")
                server.shutdown()
                server.server_close()
                logger.info("Server shutdown complete")
            except Exception as e:
                logger.error(f"Error during server shutdown: {e}")
        
        # Clean up any remaining resources
        try:
            # Close any open SSE connections
            with _sse_clients_lock:
                _sse_clients.clear()
        except Exception:
            pass


if __name__ == "__main__":
    main()
