"""Cleanup of finished torrents."""
from __future__ import annotations

from .client import qb, QbitUnavailable
from .tv_organizer import NOT_TV, ORGANIZED, REVIEW, organize_completed_torrent

# Only delete a torrent when it is in BOTH:
#   - a state that means "done downloading", AND
#   - actually 100% complete (progress >= 1.0)
#
# The progress check is the safety belt that stops the cleanup loop from
# accidentally deleting a torrent that briefly transitions through, say,
# `pausedUP` while qBittorrent is reshuffling state during metadata pickup
# — which was making torrents disappear mid-download.
_COMPLETED_STATES = {
    "stoppedUP", "pausedUP", "stalledUP", "forcedUP", "queuedUP", "uploading",
}


def remove_completed_torrents(download_dir: str = "", shows_dir: str = "") -> None:
    try:
        client = qb()
    except QbitUnavailable:
        return
    try:
        torrents = client.torrents()
    except Exception:
        return
    for t in torrents:
        state = t.get("state")
        progress = float(t.get("progress", 0))
        if state in _COMPLETED_STATES and progress >= 1.0:
            if download_dir and shows_dir:
                try:
                    result = organize_completed_torrent(t, download_dir, shows_dir)
                except Exception as e:
                    # Fail closed: a recognized episode must not be removed
                    # from qBittorrent if filing failed unexpectedly.
                    print(f"[organizer] could not process {t.get('name', '?')!r}: {e}")
                    continue
                if result.status == REVIEW:
                    print(f"[organizer] keeping completed torrent for review: {t.get('name', '?')!r}: {result.reason}")
                    continue
                if result.status == ORGANIZED:
                    print(f"[organizer] {t.get('name', '?')!r}: {result.reason}")
                elif result.status != NOT_TV:
                    print(f"[organizer] unexpected result for {t.get('name', '?')!r}: {result.status}")
                    continue
            try:
                print(f"[cleanup] deleting completed torrent {t.get('hash', '?')[:8]}... (state={state}, progress={progress})")
                client.delete(t["hash"])
            except Exception as e:
                print(f"[cleanup] delete failed: {e}")
