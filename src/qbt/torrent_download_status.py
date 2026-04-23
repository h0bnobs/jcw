"""Active-download status + torrent control."""
from __future__ import annotations

from .client import qb, QbitUnavailable
from .trackers import get_trackers


def get_active_downloads() -> list:
    """Return torrents currently in any non-completed state.

    The previous implementation only returned `filter='downloading'`, which
    excludes torrents stuck in `metaDL` (downloading metadata) on some
    qBittorrent versions — meaning the user couldn't see, pause, or boost
    the very torrents giving them trouble. We now include those.
    """
    try:
        client = qb()
    except QbitUnavailable:
        return []
    active_states = {
        "downloading", "metaDL", "stalledDL", "queuedDL",
        "checkingDL", "forcedDL", "allocating", "pausedDL",
    }
    try:
        all_torrents = client.torrents()
    except Exception:
        return []
    return [t for t in all_torrents if t.get("state") in active_states]


def _safe(call):
    try:
        call()
    except QbitUnavailable:
        pass
    except Exception as e:
        print(f"[qbt] action failed: {e}")


def pause_download(torrent_hash: str) -> None:
    _safe(lambda: qb().pause(torrent_hash))


def resume_download(torrent_hash: str) -> None:
    _safe(lambda: qb().resume(torrent_hash))


def remove_download(torrent_hash: str) -> None:
    _safe(lambda: qb().delete(torrent_hash))


def force_reannounce(torrent_hash: str) -> None:
    """Force qBit to immediately re-contact all trackers for this torrent.

    The single most effective fix for a torrent stuck on "downloading
    metadata" — a fresh tracker handshake instead of waiting for the next
    scheduled announce (which can be 30+ minutes away).
    """
    _safe(lambda: qb().reannounce(torrent_hash))


def force_recheck(torrent_hash: str) -> None:
    """Re-verify the torrent's pieces."""
    _safe(lambda: qb().recheck(torrent_hash))


def force_start_torrent(torrent_hash: str) -> None:
    """Bypass queueing limits for this torrent."""
    _safe(lambda: qb().force_start(torrent_hash, value=True))


def boost_torrent(torrent_hash: str) -> None:
    """One-click rescue for stuck torrents.

    Combines three actions: re-inject the public tracker list (in case the
    original magnet had none and DHT is failing), force-start (bypass any
    queue), then immediately reannounce.
    """
    def _do():
        client = qb()
        # qBittorrent expects trackers separated by newline (\n).
        trackers = "\n".join(get_trackers())
        try:
            client.add_trackers(torrent_hash, trackers)
        except Exception as e:
            print(f"[qbt] add_trackers failed (non-fatal): {e}")
        try:
            client.force_start(torrent_hash, value=True)
        except Exception as e:
            print(f"[qbt] force_start failed (non-fatal): {e}")
        client.reannounce(torrent_hash)
    _safe(_do)
