"""Active-download status + torrent control."""
from __future__ import annotations

from .client import qb, QbitUnavailable
from .trackers import get_trackers

# qBittorrent state strings to TREAT AS ACTIVE (i.e. show on the active-downloads
# page). We use a denylist instead of an allowlist because qBittorrent has a lot
# of transient states (`checkingResumeData`, `moving`, `error`, `missingFiles`,
# the v5+ `stoppedDL`/`stoppedUP`) and any state we forget makes torrents
# *vanish* mid-flight from the UI — exactly the bug the user just reported.
#
# Anything in this set is considered "done" and will NOT be shown as active:
COMPLETED_STATES = {
    "uploading",        # actively seeding (download finished)
    "stalledUP",        # done, no upload peers
    "queuedUP",         # done, queued to seed
    "checkingUP",       # checking after completion
    "forcedUP",         # forced to seed
    "pausedUP",         # legacy paused-after-completion
    "stoppedUP",        # qBit v5+ stopped-after-completion
}


def get_active_downloads() -> list:
    """Return torrents currently being downloaded *or* in any in-flight state.

    Anything that isn't fully complete is shown — including error /
    missingFiles / checkingResumeData / moving / stoppedDL — so that
    transient state changes don't make a torrent disappear from the UI.
    """
    try:
        client = qb()
    except QbitUnavailable:
        return []
    try:
        all_torrents = client.torrents()
    except Exception:
        return []
    return [t for t in all_torrents if t.get("state") not in COMPLETED_STATES]


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
    """Force qBit to immediately re-contact all trackers for this torrent."""
    _safe(lambda: qb().reannounce(torrent_hash))


def force_recheck(torrent_hash: str) -> None:
    """Re-verify the torrent's pieces."""
    _safe(lambda: qb().recheck(torrent_hash))


def force_start_torrent(torrent_hash: str) -> None:
    """Bypass queueing limits for this torrent."""
    _safe(lambda: qb().force_start(torrent_hash, value=True))


def boost_torrent(torrent_hash: str) -> None:
    """One-click rescue for stuck torrents.

    1. Re-inject the public-tracker list (if the magnet had no trackers and
       DHT/PeX is not finding peers, this is the fix).
    2. Resume in case the torrent ended up paused/stopped.
    3. Force a fresh tracker announce.

    NOTE: We deliberately do NOT call `force_start` here anymore — on some
    qBit versions toggling force-start while a torrent is mid-`metaDL` causes
    it to transition through a weird `checkingResumeData`/`stoppedDL` cycle
    and effectively reset, which was making torrents *vanish* from the UI.
    """
    def _do():
        client = qb()
        # Trackers must be separated by newline per qBittorrent's WebUI API.
        trackers = "\n".join(get_trackers())
        try:
            client.add_trackers(torrent_hash, trackers)
        except Exception as e:
            print(f"[qbt.boost] add_trackers failed (non-fatal): {e}")
        try:
            client.resume(torrent_hash)
        except Exception as e:
            print(f"[qbt.boost] resume failed (non-fatal): {e}")
        client.reannounce(torrent_hash)
    _safe(_do)
