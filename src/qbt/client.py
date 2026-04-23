"""
Centralized, lazy qBittorrent client.

Why this exists:
- Previously every module created its own `Client('http://localhost:9000/')` at
  import time and called `.login()` immediately. If qBittorrent wasn't running
  the whole Flask app would crash on import with no useful error.
- Preferences were also being re-set on every import.

This module provides:
- A lazy singleton accessor `qb()` that connects on first use and re-tries.
- `apply_recommended_prefs()` which is called once after a successful connect
  and configures DHT / PeX / LSD / encryption — the things that actually fix
  the perpetual "downloading metadata" stall.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from qbittorrent import Client

QBIT_URL = "http://localhost:9000/"

# Settings tuned to maximise peer discovery for magnet links coming from
# public trackers (which is the common case here). The previous code only
# set max_ratio — leaving DHT/PeX/LSD at qBit's defaults, which on some
# installs are *off*, producing the dreaded "downloading metadata" forever.
RECOMMENDED_PREFS = {
    # Stop seeding once ratio hits 0 (i.e. immediately on completion).
    "max_ratio_enabled": True,
    "max_ratio": 0,
    # Peer discovery — critical for magnets without trackers.
    "dht": True,
    "pex": True,
    "lsd": True,
    # Allow both encrypted and plain peers for max compatibility.
    "encryption": 0,
    # Don't sit in queue forever.
    "queueing_enabled": False,
    # Reasonable global limits.
    "max_connec": 500,
    "max_connec_per_torrent": 100,
    "max_uploads": 20,
    "max_uploads_per_torrent": 4,
    # Anonymous mode off — it disables DHT/PeX/LSD which is what we need.
    "anonymous_mode": False,
}

_lock = threading.Lock()
_client: Optional[Client] = None
_prefs_applied = False
_last_attempt = 0.0
_RETRY_INTERVAL = 5.0  # seconds


class QbitUnavailable(RuntimeError):
    """Raised when qBittorrent WebUI cannot be reached."""


def qb() -> Client:
    """Return a connected qBittorrent client, connecting lazily.

    Raises QbitUnavailable if the WebUI is unreachable. Callers should catch
    this and surface a friendly message to the user instead of crashing.
    """
    global _client, _prefs_applied, _last_attempt
    with _lock:
        if _client is not None:
            return _client
        # Throttle reconnect attempts so a down qBit doesn't hammer the loop.
        now = time.time()
        if now - _last_attempt < _RETRY_INTERVAL and _client is None and _last_attempt:
            raise QbitUnavailable("qBittorrent WebUI not reachable (recently failed)")
        _last_attempt = now
        try:
            c = Client(QBIT_URL)
            c.login()
        except Exception as e:  # pragma: no cover - network dependent
            raise QbitUnavailable(f"Cannot reach qBittorrent at {QBIT_URL}: {e}") from e
        _client = c
        if not _prefs_applied:
            try:
                c.set_preferences(**RECOMMENDED_PREFS)
                _prefs_applied = True
            except Exception as e:
                # Non-fatal: continue without recommended prefs.
                print(f"[qbt.client] warn: could not apply recommended prefs: {e}")
        return _client


def is_available() -> bool:
    """Cheap check used by routes to short-circuit with a friendly error."""
    try:
        qb()
        return True
    except QbitUnavailable:
        return False
