"""Cleanup of finished torrents."""
from __future__ import annotations

from .client import qb, QbitUnavailable


def remove_completed_torrents() -> None:
    try:
        client = qb()
    except QbitUnavailable:
        return
    try:
        torrents = client.torrents()
    except Exception:
        return
    # Cover both legacy and modern qBittorrent completion states.
    completed_states = {"stoppedUP", "pausedUP", "stalledUP", "forcedUP", "uploading"}
    for t in torrents:
        if t.get("state") in completed_states:
            try:
                client.delete(t["hash"])
            except Exception:
                pass
