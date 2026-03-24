#!/usr/bin/env python3
"""
music_ui_server.py — bridge server between the mox CLI (mpv IPC) and music_ui.html

Connects to mpv's Unix domain socket, exposes HTTP endpoints:
  GET  /              → serves music_ui.html
  GET  /api/state     → full player state JSON (title, pos, dur, paused, volume, queue, lyrics…)
  GET  /api/events    → Server-Sent Events stream for state changes
  POST /api/cmd       → send a command (body: {"cmd": "pause"} or {"cmd": "seek +10"})
  POST /api/play      → play by query (body: {"query": "..."})

Lyrics are fetched from lrclib.net and cached per track. /api/state never blocks on lyrics;
returns cached or "loading" state. Background prefetcher keeps cache warm.
"""

import http.server
import json
import logging
import os
import re
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

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
HTML_DIR = os.path.dirname(os.path.abspath(__file__))

# Validate port number
try:
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7700
    if PORT < 1024 or PORT > 65535:
        print("❌ Error: Port must be between 1024-65535", file=sys.stderr)
        sys.exit(1)
except (ValueError, IndexError):
    print("❌ Error: Invalid port number", file=sys.stderr)
    sys.exit(1)

# ── dependency and environment checks ─────────────────────────────────────────
def check_dependencies():
    """Check for required dependencies and environment setup."""
    errors = []
    
    # Check Python version
    if sys.version_info < (3, 6):
        errors.append("Python 3.6 or higher is required")
    
    # Check required system commands
    required_commands = ['mpv', 'curl', 'jq']
    for cmd in required_commands:
        try:
            subprocess.run([cmd, '--version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True, 
                         timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            errors.append(f"Required command not found or not working: {cmd}")
    
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


def mpv_set(prop, value):
    resp = mpv_command(["set_property", prop, value])
    return resp


def mpv_alive():
    return os.path.exists(SOCKET_PATH)


# ── Lyrics cache ─────────────────────────────────────────────────────────────

_lyrics_cache = {}  # {title: {"synced": bool, "lines": [...]} or sentinel}
_lyrics_lock = threading.Lock()

LYRICS_LOADING = "loading"      # fetch in progress
LYRICS_NOT_FOUND = "not_found"  # fetch completed, nothing found


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
        _lyrics_cache[title] = result
    return result


def get_lyrics_cached(title):
    """Return cached lyrics for title, or LYRICS_LOADING sentinel. Never blocks."""
    with _lyrics_lock:
        if title in _lyrics_cache:
            return _lyrics_cache[title]
    return LYRICS_LOADING


# ── Background lyrics prefetcher ─────────────────────────────────────────────

_last_lyrics_title = ""
_lyrics_retry_count = {}  # {title: int} — how many retries for LYRICS_NOT_FOUND


def _lyrics_bg_fetch():
    """Runs in background thread — prefetches lyrics when track changes."""
    global _last_lyrics_title
    while True:
        try:
            if mpv_alive():
                title = mpv_get("media-title") or ""
                if title:
                    cached = get_lyrics_cached(title)
                    title_changed = (title != _last_lyrics_title)
                    # Retry if not_found and we haven't retried too many times
                    retries = _lyrics_retry_count.get(title, 0)
                    should_retry = (cached == LYRICS_NOT_FOUND and retries < 3)
                    if title_changed or should_retry:
                        if title_changed:
                            with _lyrics_lock:
                                _lyrics_cache.pop(title, None)
                            _lyrics_retry_count[title] = 0
                        else:
                            _lyrics_retry_count[title] = retries + 1
                            with _lyrics_lock:
                                _lyrics_cache.pop(title, None)
                        _last_lyrics_title = title
                        fetch_lyrics(title)
        except Exception:
            pass
        time.sleep(3)


threading.Thread(target=_lyrics_bg_fetch, daemon=True).start()


# ── Build full state (never blocks on lyrics) ─────────────────────────────────

def get_full_state():
    """
    Return a dict with the full player state for the UI.
    Lyrics: returns cached value or LYRICS_LOADING — never blocks on fetch.
    """
    if not mpv_alive():
        return {
            "alive": False, "playing": False, "paused": True,
            "title": "nothing playing", "pos": 0, "dur": 0,
            "volume": 80, "speed": 1.0, "queue": [], "currentIdx": -1,
            "repeat": False, "loopOne": False, "autoDj": False,
            "lyrics": None,
        }

    title = mpv_get("media-title") or ""
    pos = mpv_get("time-pos") or 0
    dur = mpv_get("duration") or 0
    paused = mpv_get("pause")
    volume = mpv_get("volume") or 80
    speed = mpv_get("speed") or 1.0
    loop_playlist = mpv_get("loop-playlist") or "no"
    loop_file = mpv_get("loop-file") or "no"
    playlist_pos = mpv_get("playlist-playing-pos")

    pl_resp = mpv_command(["get_property", "playlist"])
    pl_data = pl_resp.get("data", []) if isinstance(pl_resp, dict) else []

    queue = []
    for i, item in enumerate(pl_data):
        t = item.get("title") or item.get("filename", "")
        queue.append({"title": t, "current": item.get("current", False)})

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

    autodj = os.path.exists(os.path.expanduser("~/music_system/data/autodj_enabled"))

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
        "lyrics": lyrics_data,
    }


# ── Command whitelist and rate limiting ──────────────────────────────────────

ALLOWED_CMD_ACTIONS = frozenset([
    "pause", "pp", "next", "mn", "prev", "mb", "stop", "seek", "vol", "volume",
    "speed", "repeat", "rp", "repeat-one", "ro", "shuffle", "playlist-play-index",
    "clear", "norm", "like", "autodj", "eq", "play", "add", "mox", "qrm",
])

RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 1.0  # seconds

_cmd_timestamps = []
_cmd_timestamps_lock = threading.Lock()


def _check_rate_limit():
    """Return True if request is allowed, False if rate limited."""
    now = time.monotonic()
    with _cmd_timestamps_lock:
        _cmd_timestamps[:] = [t for t in _cmd_timestamps if now - t < RATE_LIMIT_WINDOW]
        if len(_cmd_timestamps) >= RATE_LIMIT_REQUESTS:
            return False
        _cmd_timestamps.append(now)
    return True


def _validate_cmd(cmd_str):
    """Return (valid, error_msg). Valid means cmd action is whitelisted and safe."""
    cmd_str = (cmd_str or "").strip()
    if not cmd_str:
        return False, "empty command"
    
    # Strict command length limit
    if len(cmd_str) > 200:
        return False, "command too long"
    
    # Comprehensive injection protection
    dangerous_chars = ['&', '|', ';', '`', '$', '(', ')', '{', '}', '[', ']', 
                      '<', '>', '"', "'", '\\', '\n', '\r', '\t']
    if any(char in cmd_str for char in dangerous_chars):
        return False, "invalid characters in command"
    
    # Only allow alphanumeric, spaces, hyphens, plus/minus, dots, colons
    import re
    if not re.match(r'^[a-zA-Z0-9\s\-+.:]+$', cmd_str):
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

    elif action == "playlist-play-index":
        if len(parts) > 1:
            try:
                idx = int(parts[1])
                mpv_set("playlist-pos", idx)
                return {"ok": True, "msg": f"playing track {idx + 1}"}
            except ValueError:
                pass
        return {"ok": False, "msg": "need index"}

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


# ── SSE: state change notifications ───────────────────────────────────────────

_sse_clients = []
_sse_clients_lock = threading.Lock()
_last_state_json = None
_state_poll_interval = 0.5


def _sse_broadcast(data):
    """Send JSON to all connected SSE clients."""
    msg = f"data: {json.dumps(data)}\n\n"
    with _sse_clients_lock:
        dead = []
        for wfile in _sse_clients:
            try:
                wfile.write(msg.encode())
                wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                dead.append(wfile)
        for w in dead:
            _sse_clients.remove(w)


def _sse_poll_loop():
    """Background thread: poll state, broadcast on change."""
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
            elif path == "/api/state":
                self._json_response(get_full_state())
            elif path == "/api/events":
                self._serve_sse()
            else:
                logger.warning(f"404 - Path not found: {path}")
                self.send_error(404)
        except Exception as e:
            self.handle_exception(e)

    def _serve_sse(self):
        """Serve Server-Sent Events stream."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        with _sse_clients_lock:
            _sse_clients.append(self.wfile)

        # Send initial state immediately so client doesn't wait for first change
        try:
            state = get_full_state()
            self.wfile.write(f"data: {json.dumps(state)}\n\n".encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            with _sse_clients_lock:
                if self.wfile in _sse_clients:
                    _sse_clients.remove(self.wfile)
            return

        try:
            # Keep connection open; client may disconnect
            while True:
                time.sleep(30)
                # Send keepalive comment
                try:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _sse_clients_lock:
                if self.wfile in _sse_clients:
                    _sse_clients.remove(self.wfile)

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # Validate path
            if '..' in path or path.startswith('//'):
                logger.warning(f"Suspicious POST path: {path}")
                self.send_error(400, "Bad request")
                return

            if path == "/api/cmd":
                self._handle_cmd_request()
            elif path == "/api/play":
                self._handle_play_request()
            else:
                logger.warning(f"404 - POST path not found: {path}")
                self.send_error(404)
        except Exception as e:
            self.handle_exception(e)
    
    def _handle_cmd_request(self):
        """Handle /api/cmd POST requests."""
        try:
            if not _check_rate_limit():
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
            if query:
                # Validate and sanitize query
                if len(query) > 500:
                    self._json_response({"ok": False, "msg": "query too long"}, 400)
                    return
                
                # Basic sanitization - remove dangerous characters
                if not re.match(r'^[a-zA-Z0-9\s\-+.:_()[\]]+$', query):
                    self._json_response({"ok": False, "msg": "invalid characters in query"}, 400)
                    return
                
                try:
                    logger.info(f"Play request: {query}")
                    subprocess.Popen(["mox", query], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    self._json_response({"ok": True, "msg": f"playing: {query}"})
                except Exception as e:
                    logger.error(f"Play command failed: {e}")
                    self._json_response({"ok": False, "msg": f"play failed: {str(e)}"}, 500)
            else:
                self._json_response({"ok": False, "msg": "empty query"}, 400)
                
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
            # Security headers
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-XSS-Protection", "1; mode=block")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "music_ui.html not found")

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        # Security headers
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
