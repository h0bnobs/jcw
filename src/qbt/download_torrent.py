"""Magnet download + VPN helpers."""
from __future__ import annotations

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


def download_torrent(magnet_link: str, download_path: str) -> dict:
    """Add a magnet to qBittorrent.

    Returns {ok, message} so the Flask layer can show a sensible response
    instead of silently swallowing errors (which made "downloading metadata"
    look like the only failure mode).
    """
    if not magnet_link or not magnet_link.startswith("magnet:?"):
        return {"ok": False, "message": "Invalid magnet link"}
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
