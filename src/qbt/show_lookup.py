"""Resolve a parsed TV series name to a canonical show identity.

The TV organizer only files episodes into show folders that already exist in
the library — a deliberately conservative choice that leaves a brand-new show
sitting in qBittorrent for a manual move. This module closes that gap by
identifying the show from its metadata so a correctly named folder can be
created automatically.

Keyless by default: it reuses the same Cinemeta source the catalogue browser
uses, which returns a canonical title, a year and an IMDb id. Jellyfin resolves
an ``[imdbid-ttN]`` folder tag as reliably as ``[tmdbid-N]``, so a new show is
filed correctly with no API key at all. When a TMDB API key is configured, the
IMDb id is upgraded to a TMDB id so new folders match the existing
``Title (Year) [tmdbid-N]`` convention already used across the library.

Everything here is best-effort: any lookup failure or an un-confident match
returns ``None`` so the organizer falls back to its existing "leave for review"
behaviour rather than creating a wrong folder.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

import requests

from src.catalogue import catalogue

_TMDB_FIND_URL = "https://api.themoviedb.org/3/find/{imdb_id}"
_DEFAULT_TIMEOUT = (3, 8)


def _normalize(title: str) -> str:
    """Punctuation/accent-insensitive key, matching tv_organizer._normalize_title."""
    decomposed = unicodedata.normalize("NFKD", title or "")
    ascii_title = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", ascii_title.lower())


def _release_year(value) -> str:
    """Pull the first 4-digit year out of a Cinemeta year/releaseInfo string.

    Series carry ranges like ``2005-`` or ``2005-2012``; only the start year
    belongs in a Jellyfin folder name.
    """
    match = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return match.group(0) if match else ""


@dataclass(frozen=True)
class ShowIdentity:
    title: str
    year: str
    tmdb_id: str | None = None
    imdb_id: str | None = None

    def provider_tag(self) -> str:
        """A Jellyfin folder provider tag — tmdbid preferred, imdbid otherwise."""
        if self.tmdb_id:
            return f"tmdbid-{self.tmdb_id}"
        if self.imdb_id:
            return f"imdbid-{self.imdb_id}"
        return ""

    def folder_name(self) -> str:
        base = f"{self.title} ({self.year})" if self.year else self.title
        tag = self.provider_tag()
        name = f"{base} [{tag}]" if tag else base
        # The shows library is a single ext4 volume, where only the path
        # separator and NUL are genuinely unsafe in a path component. Keep the
        # rest (apostrophes, colons, ampersands) so the folder matches the real
        # title and Jellyfin's own matching stays happy.
        return name.replace("/", "-").replace("\x00", "").strip()


def _tmdb_id_for_imdb(imdb_id: str | None, api_key: str | None,
                      timeout=_DEFAULT_TIMEOUT) -> str | None:
    """Map an IMDb id to a TMDB TV id via TMDB's keyed /find endpoint."""
    if not imdb_id or not api_key:
        return None
    try:
        response = requests.get(
            _TMDB_FIND_URL.format(imdb_id=imdb_id),
            params={"api_key": api_key, "external_source": "imdb_id"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None
    results = data.get("tv_results") if isinstance(data, dict) else None
    if not results:
        return None
    tmdb_id = results[0].get("id")
    return str(tmdb_id) if tmdb_id else None


def resolve_show(title: str, year: str | None = None,
                 tmdb_api_key: str | None = None) -> ShowIdentity | None:
    """Return a confident show identity for ``title``/``year``, or ``None``.

    Confidence is deliberately strict: the candidate's title must match exactly
    once punctuation and accents are stripped. When the release carries a year,
    a candidate must share that (start) year; when it does not, the match must
    be unambiguous. Anything less returns ``None`` so no folder is created.
    """
    query = (title or "").strip()
    target = _normalize(query)
    if not target:
        return None
    try:
        candidates = catalogue("series", query)
    except Exception:
        return None

    exact = [c for c in candidates if _normalize(c.get("name", "")) == target]
    if not exact:
        return None

    if year:
        year = str(year)
        year_matches = [c for c in exact if _release_year(c.get("year")) == year]
        if not year_matches:
            return None
        chosen = year_matches[0]
    else:
        if len(exact) > 1:
            return None
        chosen = exact[0]

    imdb_id = chosen.get("id") or None
    canonical = (chosen.get("name") or query).strip()
    resolved_year = _release_year(chosen.get("year")) or (str(year) if year else "")
    tmdb_id = _tmdb_id_for_imdb(imdb_id, tmdb_api_key)
    if not (tmdb_id or imdb_id):
        return None
    return ShowIdentity(canonical, resolved_year, tmdb_id, imdb_id)
