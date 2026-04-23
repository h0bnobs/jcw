"""
Public-tracker enrichment for magnet links.

Many magnet links scraped from public indexers contain only the info-hash
(`xt=urn:btih:...`) and no `tr=` tracker entries. With no trackers, qBittorrent
has to rely entirely on DHT/PeX/LSD to find peers — which is what causes the
infamous "downloading metadata" hang, sometimes for hours.

We fix this by appending a curated list of well-known public trackers to every
magnet before handing it to qBit. The list is fetched once from the popular
`ngosang/trackerslist` GitHub mirror and cached on disk; if the network is
down we fall back to a small built-in list so downloads still work offline.
"""
from __future__ import annotations

import os
import time
from typing import List
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests

# Refresh the cached tracker list at most once per day.
_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".trackers_cache.txt")
_CACHE_TTL = 24 * 60 * 60
_REMOTE_URL = (
    "https://cdn.jsdelivr.net/gh/ngosang/trackerslist@master/trackers_best.txt"
)

# Conservative built-in fallback — these are long-running, well-known trackers.
_FALLBACK_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://explodie.org:6969/announce",
    "udp://tracker.theoks.net:6969/announce",
    "udp://opentracker.io:6969/announce",
    "https://tracker.tamersunion.org:443/announce",
]


def _load_cached() -> List[str] | None:
    if not os.path.exists(_CACHE_PATH):
        return None
    if time.time() - os.path.getmtime(_CACHE_PATH) > _CACHE_TTL:
        return None
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError:
        return None


def _save_cache(trackers: List[str]) -> None:
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(trackers))
    except OSError:
        pass


def get_trackers() -> List[str]:
    """Return a list of public tracker URLs, cached for a day."""
    cached = _load_cached()
    if cached:
        return cached
    try:
        resp = requests.get(_REMOTE_URL, timeout=5)
        resp.raise_for_status()
        trackers = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
        if trackers:
            _save_cache(trackers)
            return trackers
    except Exception as e:
        print(f"[qbt.trackers] failed to fetch remote tracker list: {e}")
    return _FALLBACK_TRACKERS


def enrich_magnet(magnet: str) -> str:
    """Append public trackers to a magnet link, preserving any existing ones."""
    if not magnet or not magnet.startswith("magnet:?"):
        return magnet
    parsed = urlparse(magnet)
    # parse_qsl preserves duplicates of the same key, which is exactly what
    # magnet links use (multiple `tr=` entries).
    pairs = parse_qsl(parsed.query, keep_blank_values=False)
    existing = {v for k, v in pairs if k == "tr"}
    for tr in get_trackers():
        if tr not in existing:
            pairs.append(("tr", tr))
            existing.add(tr)
    new_query = urlencode(pairs)
    return urlunparse(parsed._replace(query=new_query))
