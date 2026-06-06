#!/usr/bin/env zsh
# ============================================================
#  mox — terminal music CLI  (hardened build v8.0.0)
#  All state lives in ~/music_system/
#
#  v5 changes over v4:
#   v5-A  CRITICAL BUG FIX: _wait_prop now yields 0.3s before polling +
#         retries if title looks like a URL → fixes "unknown" on first play
#   v5-B  CRITICAL BUG FIX: _lock stale-steal no longer rmdir's unowned lock
#   v5-C  CRITICAL BUG FIX: txt bg job PID written atomically BEFORE disown
#   v5-D  _wait_prop: distinguishes "property unavailable" vs "still loading"
#         via _get_checked() — no more 60-iteration spin on hard errors
#   v5-E  _clean_url: handles YouTube Shorts (/shorts/ID), SoundCloud,
#         Bandcamp; never calls _clean_url on local files
#   v5-F  do_bar: cursor always restored after loop exit (not just trap)
#   v5-G  do_similar: python3 replaced with jq @uri for URL encoding
#   v5-H  do_export: CSV injection guard (prefix dangerous cells with tab)
#   v5-I  _log_history: rolling dedup — won't log same URL within last 50 entries
#   v5-J  _shuf1: reservoir sampling (O(1) memory, no modulo bias)
#   v5-K  do_bar: single jq parse pass (was 9 forks/frame → 1)
#   v5-L  SPEED: YouTube Data API v3 / Invidious search path (curl+jq, ms not s)
#         Falls back to yt-dlp scrape if API key not set or request fails
#   v5-M  SPEED: fzf --bind change:reload for live async search UI
#   v5-N  SPEED: do_txt parallel resolution — all lines fetched concurrently
#   v5-O  UI: mox art — terminal album art via chafa (falls back gracefully)
#   v5-P  UI: mox lyrics — real-time synced lyrics from lrclib.net
#   v5-Q  UI: mox ui — unified TUI dashboard (queue + art + bar in tmux/split)
#   v5-R  Auto-DJ / radio mode — queue auto-refills from Last.fm when empty
#   v5-S  mox add-next — insert track immediately after current queue position
#   v5-T  mox bookmark — named snapshot of queue + position + timestamp
#   v5-U  mox txt --resume — resume txt playlist from last saved position
#   v5-V  mox reload-config — hot-reload config without killing daemon
#   v5-W  Graceful EXIT trap — always unlocks locks on shell exit
#   v5-X  mox index — scan ~/Music, build local library cache via ffprobe
#   v5-Y  SponsorBlock note added to help (mpv lua script path documented)
#   v5-Z  PIPESTATUS checks in _pick() and _txt_search_and_play_line()
# ============================================================

set -u
set +v +x  # Disable verbose/debug output
setopt NULL_GLOB  # Allow globs to expand to nothing without error

# ── paths ────────────────────────────────────────────────────
MUSIC_ROOT="${MUSIC_ROOT:-$HOME/music_system}"
SOCKET_DIR="$MUSIC_ROOT/socket"
SOCKET="$SOCKET_DIR/mpv.sock"
MPV_PID_FILE="$SOCKET_DIR/mpv.pid"
CACHE_DIR="$MUSIC_ROOT/cache"
PLAYLIST_DIR="$MUSIC_ROOT/playlists"
TXTS_DIR="$MUSIC_ROOT/txts"
DOWNLOADS_DIR="$MUSIC_ROOT/downloads"
DATA_DIR="$MUSIC_ROOT/data"
LOCK_DIR="$MUSIC_ROOT/locks"
LOCK_FILE="$LOCK_DIR/start.lock"
LOCK_FILE_D="$LOCK_FILE.d"
HISTORY_LOCK="$LOCK_DIR/history.lock"
LIKES_FILE="$DATA_DIR/likes"
HISTORY_FILE="$DATA_DIR/history"
TXT_STATE_FILE="$DATA_DIR/txt_state"
TXT_BG_GEN_FILE="$DATA_DIR/txt_bg_gen"
QUEUE_SNAPSHOT="$DATA_DIR/queue_snapshot.m3u"
MPV_LOG="$DATA_DIR/mpv.log"
LOCAL_INDEX="$DATA_DIR/local_index.tsv"
BOOKMARKS_FILE="$DATA_DIR/bookmarks"
AUTODJ_FILE="$DATA_DIR/autodj_enabled"
PINS_FILE="$DATA_DIR/pins"
STATIONS_FILE="$MUSIC_ROOT/stations.tsv"
AUTOSAVE_QUEUE_FILE="$DATA_DIR/autosave_queue.m3u"
QUEUE_SAVE_AUTO_FILE="$DATA_DIR/queue_save_auto_enabled"
VOLUME_SPEED_STATE="$DATA_DIR/volume_speed_state"
NORM_STATE_FILE="$DATA_DIR/norm_enabled"
TXT_PROGRESS_FILE="$DATA_DIR/txt_progress"
SHARE_DIR="$DATA_DIR/shares"
SCHEDULE_DIR="$DATA_DIR/schedules"
UXI_PID_FILE="$DATA_DIR/uxi_server.pid"
TXT_LINES=()
CONFIG_FILE="$MUSIC_ROOT/config"
PLUGINS_DIR="$MUSIC_ROOT/plugins"

# ── defaults (overridable via config file) ────────────────────
CACHE_TTL=3600
HISTORY_MAX=500
DEFAULT_VOLUME=80
VOLUME_STEP=5
SEARCH_RESULTS=20
AUDIO_DEVICE_SPEAKERS=""
AUDIO_DEVICE_HEADPHONES=""
SCROBBLE_URL=""
YTDLP_MAX_AGE_DAYS=30
LASTFM_API_KEY=""
YOUTUBE_API_KEY=""         # v5-L: optional YouTube Data API v3 key for fast search
INVIDIOUS_HOST=""          # v5-L: optional Invidious instance e.g. "https://invidious.snopyta.org"
LOCAL_MUSIC_DIR="${HOME}/Music"
AUTODJ_ENABLED=0           # v5-R: auto-refill queue from Last.fm when empty
LYRICS_ENABLED=1           # v5-P: enable lrclib.net lyrics fetch
AUTO_RESTART_DAEMON=true   # v6-A: auto-restart daemon when unresponsive
NOTIFY_ENABLED=0           # desktop notification on track change
CROSSFADE_SECS=0           # crossfade duration between tracks (0=off)
BAR_REFRESH_MS=500         # progress bar refresh interval
M_UPDATE_URL=""            # self-update URL (empty=disabled)
M_UPDATE_SHA256=""         # expected SHA256 for self-update
UXI_AUTH=0                 # 1 = require web UI PIN on first visit
UXI_PORT="${UXI_PORT:-7700}"

# ── binary paths (resolved lazily via _ensure_bin) ─────────────
# Declare variables empty; they are populated on first use via _ensure_bin.
# Commands that need a specific binary call _ensure_bin before using it.
YTDLP="${YTDLP:-}"
MPV="${MPV:-}"
FZF="${FZF:-}"
SOCAT="${SOCAT:-}"
JQ="${JQ:-}"
CURL="${CURL:-}"
CHAFA="${CHAFA:-}"
FFPROBE="${FFPROBE:-}"

# ── load user config ──────────────────────────────────────────

# ── Load library modules ────────────────────────────────────────────────────
_MOX_LIB_DIR="$(cd "$(dirname "${(%):-%N}")" && pwd)/lib"
MOX_LIB_ONLY=1
for _mox_lib in core lock ipc search playback queue audio history playlist lyrics schedule ui; do
  # shellcheck source=/dev/null
  source "$_MOX_LIB_DIR/${_mox_lib}.sh" || { echo "Error: failed to load lib/${_mox_lib}.sh" >&2; exit 1; }
done
unset MOX_LIB_ONLY _mox_lib _MOX_LIB_DIR

# Load and validate user configuration after libs are loaded
_load_config
_validate_config


# ── main dispatch ─────────────────────────────────────────────
if [ $# -eq 0 ]; then
  if [ ! -S "$SOCKET" ]; then
    echo ""
    echo "  ${BOLD}mox${X} — terminal music CLI"
    echo "  run: ${G}mox help${X} for all commands"
    echo ""
    echo "  Quick start:"
    echo "    ${G}mox \"lofi hip hop\"${X}    search & play"
    echo "    ${G}mox uxi${X}                 open web UI"
    echo ""
  else
    _check_deps
    do_status
  fi
  exit 0
fi

case "$1" in
  --version|-V|version) do_version;                   exit 0 ;;
  pause|pp)            do_pause;                   exit 0 ;;
  next|mn)             do_next;                    exit 0 ;;
  prev|mb)             do_prev;                    exit 0 ;;
  stop)                do_stop;                    exit 0 ;;
  start)               do_start;                   exit 0 ;;
  shuffle)             do_shuffle;                 exit 0 ;;
  repeat|rp)           do_repeat;                  exit 0 ;;
  repeat-one|ro)       do_repeat_one;              exit 0 ;;
  clear)               do_clear;                   exit 0 ;;
  now)                 do_now;                     exit 0 ;;
  bar|progress)        do_bar;                     exit 0 ;;
  lyrics)              do_lyrics;                  exit 0 ;;
  art)                 do_art;                     exit 0 ;;
  ui)                  do_ui;                      exit 0 ;;
  uxi)                 do_uxi;                     exit 0 ;;
  uxi-stop)             do_uxi_stop;                 exit 0 ;;
  scrub|slider)        do_scrub;                   exit 0 ;;
  queue)               do_queue;                   exit 0 ;;
  qmove)               do_queue_move "${2:-}" "${3:-}";    exit 0 ;;
  qrm)                 do_queue_remove "${2:-}";       exit 0 ;;
  status)              do_status;                  exit 0 ;;
  hp|headphones)       do_hp;                      exit 0 ;;
  sp|speakers)         do_sp;                      exit 0 ;;
  devices)             do_devices;                 exit 0 ;;
  playlists|pls)       do_playlists;               exit 0 ;;
  save)                do_save "${2:-}";           exit 0 ;;
  load)                do_load "${2:-}";           exit 0 ;;
  pldel)               do_playlist_del "${2:-}";   exit 0 ;;
  import)              do_import "${2:-}";         exit 0 ;;
  dl)                  do_dl "${2:-}";             exit 0 ;;
  dl-list)             do_dl_list;                 exit 0 ;;
  txt)                 do_txt "${2:-}" "${3:-}";   exit 0 ;;
  txts)                do_txts;                    exit 0 ;;
  txtnext|tn)          do_txtnext;                 exit 0 ;;
  txtprev|tp)          do_txtprev;                 exit 0 ;;
  txtnow)              do_txtnow;                  exit 0 ;;
  txtpick|tj)          do_txtpick;                 exit 0 ;;
  txtedit|te)          do_txtedit "${2:-}";        exit 0 ;;
  txt-export)          do_txt_export;              exit 0 ;;
  vol|volume)          do_vol "${2:-}";            exit 0 ;;
  seek)                do_seek "${2:-}";           exit 0 ;;
  speed)               do_speed "${2:-}";          exit 0 ;;
  like)                do_like;                    exit 0 ;;
  unlike)              do_unlike;                  exit 0 ;;
  likes)               do_likes;                   exit 0 ;;
  likes-play|lp)       do_likes_play;              exit 0 ;;
  love)                do_love;                    exit 0 ;;
  similar)             do_similar;                 exit 0 ;;
  smart)               do_smart;                   exit 0 ;;
  history|hist)        do_history;                 exit 0 ;;
  history-clear)       do_history_clear;           exit 0 ;;
  replay|rl)           do_replay;                  exit 0 ;;
  eq)                  if [[ "${2:-}" == "custom" ]]; then do_eq_custom "$@"; else do_eq "${2:-}"; fi; exit 0 ;;
  crossfade)            do_crossfade "${2:-}";     exit 0 ;;
  queue-dedup)          do_queue_dedup;           exit 0 ;;
  pin)                 do_pin "${2:-}";            exit 0 ;;
  pins)                do_pins;                   exit 0 ;;
  queue-save-auto)      do_queue_save_auto;       exit 0 ;;
  search)              shift; do_search_only "$@"; exit 0 ;;
  radio)               do_radio "${2:-}";         exit 0 ;;
  chapter)              do_chapter;               exit 0 ;;
  stats)               do_stats;                  exit 0 ;;
  config-edit)         do_config_edit;           exit 0 ;;
  notify-toggle)        do_notify_toggle;          exit 0 ;;
  auto-restart-toggle)  do_auto_restart_toggle;     exit 0 ;;
  history-stats)       do_history_stats;          exit 0 ;;
  completions)         do_completions;            exit 0 ;;
  norm)                do_norm;                    exit 0 ;;
  sleep)               do_sleep "${2:-}";          exit 0 ;;
  export)              do_export "${2:-}";         exit 0 ;;
  update)              do_update;                  exit 0 ;;
  doctor)              do_doctor;                  exit 0 ;;
  queue-restore|qr)    do_queue_restore;           exit 0 ;;
  log)                 do_log;                     exit 0 ;;
  log-clear)           do_log_clear;               exit 0 ;;
  cache-clear)         do_cache_clear;             exit 0 ;;
  cache-prune)         do_cache_prune;             exit 0 ;;
  cache-stats)         do_cache_stats;             exit 0 ;;
  autodj)              do_autodj;                  exit 0 ;;
  bookmark)            do_bookmark "${2:-}";       exit 0 ;;
  bookmarks)           do_bookmarks;               exit 0 ;;
  bookmark-load|bl)    do_bookmark_load;           exit 0 ;;
  index)               do_index;                   exit 0 ;;
  local)               do_local "${2:-}";          exit 0 ;;
  scan)                do_scan "${2:-}" "${3:-}";  exit 0 ;;
  share)               do_share "${2:-}";          exit 0 ;;
  schedule)            do_schedule "${2:-}" "${3:-}"; exit 0 ;;
  reload-config)       do_reload_config;           exit 0 ;;
  cast)                do_cast;                    exit 0 ;;
  help|-h|--help)      do_help;                    exit 0 ;;
esac

# ── Free-form query with optional flags ───────────────────────
typeset -a QUERY_ARGS
QUERY_ARGS=()
FLAG_ADD=0
FLAG_FORCE=0
FLAG_NEXT=0
FLAG_HP=0
FLAG_SP=0

for arg in "$@"; do
  case "$arg" in
    -a|--add)          FLAG_ADD=1 ;;
    -f|--force)        FLAG_FORCE=1 ;;
    -an|--add-next)    FLAG_ADD=1; FLAG_NEXT=1 ;;
    -hp|--headphones)  FLAG_HP=1 ;;
    -sp|--speakers)    FLAG_SP=1 ;;
    -*)                _die "unknown flag: $arg  (run: mox help)" ;;
    *)                 QUERY_ARGS+=("$arg") ;;
  esac
done

[ ${#QUERY_ARGS[@]} -eq 0 ] && _die "no query — usage: mox \"song name\"  or  mox help"

QUERY="${(j: :)QUERY_ARGS}"

if [ $FLAG_ADD -eq 1 ]; then
  if [ $FLAG_NEXT -eq 1 ]; then
    do_add_next "$QUERY"
  elif [ $FLAG_FORCE -eq 1 ]; then
    do_add_force "$QUERY"
  else
    do_add "$QUERY"
  fi
else
  do_play "$QUERY"
fi

[ $FLAG_HP -eq 1 ] && sleep 0.4 && do_hp
[ $FLAG_SP -eq 1 ] && sleep 0.4 && do_sp
