"""Magnet download + VPN helpers."""
from __future__ import annotations

import os
from urllib.parse import parse_qs, unquote_plus, urlsplit

import psutil
import requests

from .client import qb, QbitUnavailable
from .trackers import enrich_magnet


def get_ip_address() -> str:
    """Return the current public IP (best-effort)."""
    try:
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return ""


def is_vpn() -> bool:
    """Detect a VPN by looking for tun/tap/wg-style network interfaces."""
    for name in psutil.net_if_addrs().keys():
        n = name.lower()
        if any(tag in n for tag in ("tun", "tap", "vpn", "wg", "ovpn", "mullvad", "proton")):
            return True
    return False


def magnet_display_name(magnet_link: str) -> str:
    """Return the decoded display name (dn) of a magnet, or '' if absent."""
    try:
        dn = parse_qs(urlsplit(magnet_link).query).get("dn", [""])[0]
    except Exception:
        return ""
    return unquote_plus(dn).strip()


def already_downloaded(magnet_link: str, download_path: str) -> str | None:
    """Return the on-disk name if this torrent's content already exists.

    Matches the magnet display name (dn) against entries in the download
    directory. For the public torrents this app handles, dn matches the saved
    folder/file name, so this catches the "re-add something already grabbed"
    case that otherwise checks to 100% and is silently removed by the cleanup.

    Best-effort: a missing/odd dn or unreadable directory just skips the check
    and lets qBittorrent handle it as before.
    """
    name = magnet_display_name(magnet_link)
    if not name or not download_path:
        return None
    try:
        entries = os.listdir(download_path)
    except OSError:
        return None
    for entry in entries:
        # Exact match for a release folder, or `<name>.<ext>` for single files.
        if entry == name or entry.startswith(name + "."):
            return entry
    return None


def download_torrent(magnet_link: str, download_path: str) -> dict:
    """Add a magnet to qBittorrent.

    Returns {ok, message} so the Flask layer can show a sensible response
    instead of silently swallowing errors (which made "downloading metadata"
    look like the only failure mode).
    """
    if not magnet_link or not magnet_link.startswith("magnet:?"):
        return {"ok": False, "message": "Invalid magnet link"}
    existing = already_downloaded(magnet_link, download_path)
    if existing:
        return {"ok": False, "duplicate": True,
                "message": f"Already downloaded: {existing}"}
    enriched = enrich_magnet(magnet_link)
    try:
        client = qb()
    except QbitUnavailable as e:
        return {"ok": False, "message": str(e)}
    try:
        client.download_from_link(enriched, savepath=download_path)
    except Exception as e:
        return {"ok": False, "message": f"qBittorrent rejected the magnet: {e}"}
    return {"ok": True, "message": "Added to qBittorrent", "savepath": download_path}
