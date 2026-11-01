"""Organize completed TV episode torrents into an existing shows library.

This intentionally uses the library itself as the show catalog. It does not
call TMDB or create show folders: releases that cannot be matched confidently
are left in qBittorrent for review.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import errno
import os
import re
import shutil
import tempfile
import unicodedata

from .download_history import is_video_file


NOT_TV = "not_tv"
ORGANIZED = "organized"
REVIEW = "review"

_TV_PATTERNS = (
    re.compile(
        r"(?i)(?P<title>.*?)(?:^|[ ._-]+)S(?P<season>\d{1,2})[ ._-]*E"
        r"(?P<episodes>\d{1,3}(?:(?:E|-E?)[0-9]{1,3})*)"
    ),
    re.compile(
        r"(?i)(?P<title>.*?)(?:^|[ ._-]+)(?P<season>\d{1,2})x"
        r"(?P<episodes>\d{1,3}(?:x\d{1,3})*)"
    ),
)
_SHOW_FOLDER = re.compile(
    r"^(?P<title>.+?)\s+\((?P<year>\d{4})\)\s+\[tmdbid-(?P<tmdb_id>\d+)\]$",
    re.IGNORECASE,
)
_YEAR_SUFFIX = re.compile(r"(?:\s|[._(-])((?:19|20)\d{2})\)?$")
_SEASON_ONLY_SUFFIX = re.compile(
    r"(?i)^(?P<title>.+?)[ ._-]+(?:season[ ._-]*\d{1,2}|s\d{1,2})"
    r"(?:$|[ ._-].*)"
)


@dataclass(frozen=True)
class EpisodeRelease:
    series_title: str
    season: int
    episodes: tuple[int, ...]
    year: str | None = None


@dataclass(frozen=True)
class ShowFolder:
    title: str
    year: str
    tmdb_id: str
    path: str


@dataclass(frozen=True)
class OrganizationResult:
    status: str
    reason: str = ""


def _clean_title(title: str) -> tuple[str, str | None]:
    title = re.sub(r"^\[[^\]]+\][ ._-]*", "", title.strip())
    year = None
    match = _YEAR_SUFFIX.search(title)
    if match:
        year = match.group(1)
        title = title[:match.start()].rstrip(" ._-([")
    title = re.sub(r"[._]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" -_")
    return title, year


def parse_episode_release(name: str) -> EpisodeRelease | None:
    """Parse common ``Show.S01E02`` and ``Show.1x02`` release names."""
    if not name:
        return None
    stem = os.path.basename(str(name))
    for pattern in _TV_PATTERNS:
        match = pattern.search(stem)
        if not match:
            continue
        season = int(match.group("season"))
        expression = match.group("episodes")
        numbers = [int(number) for number in re.findall(r"\d{1,3}", expression)]
        if not numbers:
            continue
        # A hyphen denotes an episode range (S01E01-E03 or S01E01-03).
        if "-" in expression and numbers[-1] >= numbers[0] and numbers[-1] - numbers[0] <= 20:
            numbers = list(range(numbers[0], numbers[-1] + 1))
        title, year = _clean_title(match.group("title"))
        return EpisodeRelease(title, season, tuple(dict.fromkeys(numbers)), year)
    return None


def _series_context(name: str) -> tuple[str, str | None]:
    release = parse_episode_release(name)
    if release and release.series_title:
        return release.series_title, release.year
    stem = os.path.splitext(os.path.basename(str(name)))[0]
    match = _SEASON_ONLY_SUFFIX.search(stem)
    if match:
        return _clean_title(match.group("title"))
    return "", None


def _normalize_title(title: str) -> str:
    decomposed = unicodedata.normalize("NFKD", title)
    ascii_title = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", ascii_title.lower())


def _library_shows(shows_dir: str) -> list[ShowFolder]:
    shows: list[ShowFolder] = []
    try:
        entries = os.scandir(shows_dir)
    except OSError:
        return shows
    with entries:
        for entry in entries:
            match = _SHOW_FOLDER.fullmatch(entry.name)
            if not match:
                continue
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            shows.append(ShowFolder(
                title=match.group("title"),
                year=match.group("year"),
                tmdb_id=match.group("tmdb_id"),
                path=entry.path,
            ))
    return shows


def match_library_show(
    title: str, shows_dir: str, year: str | None = None,
) -> tuple[ShowFolder | None, str]:
    """Return a unique high-confidence match from existing library folders."""
    query = _normalize_title(title)
    if not query:
        return None, "release does not include a series title"
    shows = _library_shows(shows_dir)
    if not shows:
        return None, "shows library is missing or has no recognized show folders"

    exact = [show for show in shows if _normalize_title(show.title) == query]
    candidates = exact or [
        show for show in shows
        if SequenceMatcher(None, query, _normalize_title(show.title), autojunk=False).ratio() >= 0.92
    ]
    if year:
        year_matches = [show for show in candidates if show.year == year]
        if not year_matches:
            if candidates:
                return None, f"release year {year} does not match the existing show folder"
            return None, f"no existing show matches {title!r}"
        candidates = year_matches

    if not candidates:
        return None, f"no existing show matches {title!r}"
    if len(candidates) == 1:
        return candidates[0], ""
    if exact:
        return None, f"multiple existing shows match {title!r}; a year is needed"

    ranked = sorted(
        [
            (
                SequenceMatcher(None, query, _normalize_title(show.title), autojunk=False).ratio(),
                show,
            )
            for show in candidates
        ],
        key=lambda item: item[0],
        reverse=True,
    )
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.08:
        return None, f"series title {title!r} is ambiguous"
    return ranked[0][1], ""


def _episode_folder(show_path: str, season: int) -> str:
    return os.path.join(show_path, f"Season {season:02d}")


def _video_episodes_in_library(show: ShowFolder, season: int) -> set[int]:
    season_dir = _episode_folder(show.path, season)
    try:
        names = os.listdir(season_dir)
    except OSError:
        return set()
    episodes: set[int] = set()
    for name in names:
        if not is_video_file(name):
            continue
        release = parse_episode_release(name)
        if release and release.season == season:
            episodes.update(release.episodes)
    return episodes


def release_is_in_library(release_name: str, shows_dir: str) -> bool:
    """Best-effort duplicate check for an episode already filed in the library."""
    release = parse_episode_release(release_name)
    if not release or not release.series_title:
        return False
    show, _reason = match_library_show(release.series_title, shows_dir, release.year)
    if not show:
        return False
    present = _video_episodes_in_library(show, release.season)
    return set(release.episodes).issubset(present)


def _is_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((os.path.realpath(path), os.path.realpath(root))) == os.path.realpath(root)
    except (OSError, ValueError):
        return False


def _torrent_content_path(torrent: dict, download_dir: str) -> str | None:
    name = str(torrent.get("name", ""))
    save_path = str(torrent.get("save_path", download_dir) or download_dir)
    candidates = [torrent.get("content_path")]
    if name:
        candidates.extend((os.path.join(save_path, name), os.path.join(download_dir, name)))
    root = os.path.realpath(download_dir)
    for candidate in candidates:
        if not candidate:
            continue
        candidate = os.path.realpath(str(candidate))
        if candidate == root or not _is_within(candidate, root) or not os.path.exists(candidate):
            continue
        if os.path.isfile(candidate) or os.path.isdir(candidate):
            return candidate
    return None


def _torrent_video_files(content_path: str | None, download_dir: str) -> list[str]:
    if not content_path:
        return []
    if os.path.isfile(content_path):
        return [content_path] if is_video_file(content_path) and _is_within(content_path, download_dir) else []
    videos: list[str] = []
    for root, dirs, files in os.walk(content_path, followlinks=False):
        dirs[:] = [d for d in dirs if d.lower() != "sample"]
        if "sample" in os.path.basename(root).lower():
            continue
        for filename in files:
            path = os.path.join(root, filename)
            if is_video_file(filename) and _is_within(path, download_dir):
                videos.append(path)
    return sorted(videos)


def _release_for_video(
    path: str, torrent_release: EpisodeRelease | None, torrent_name: str, video_count: int,
) -> EpisodeRelease | None:
    release = parse_episode_release(path)
    if release is None and video_count == 1:
        release = torrent_release
    if release is None:
        return None
    if release.series_title:
        return release
    title, year = _series_context(torrent_name)
    if not title:
        parent = os.path.dirname(path)
        title, year = _series_context(parent)
        if not title:
            title, year = _series_context(os.path.dirname(parent))
    if not title:
        return release
    return EpisodeRelease(title, release.season, release.episodes, release.year or year)


def _move_without_overwrite(source: str, destination: str) -> None:
    """Move a file atomically where possible, never replacing a destination."""
    if os.path.abspath(source) == os.path.abspath(destination):
        return
    if os.path.lexists(destination):
        if os.path.samefile(source, destination):
            os.unlink(source)
            return
        raise FileExistsError(destination)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    try:
        # Hard-linking then unlinking is atomic at the destination and fails if
        # a file already exists there. The media directories normally share a
        # filesystem, making this a quick no-copy move.
        os.link(source, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        descriptor, temporary = tempfile.mkstemp(prefix=".jcw-", suffix=".tmp", dir=os.path.dirname(destination))
        try:
            with os.fdopen(descriptor, "wb") as target, open(source, "rb") as origin:
                shutil.copyfileobj(origin, target)
                target.flush()
                os.fsync(target.fileno())
            shutil.copystat(source, temporary)
            # link() is exclusive: it cannot replace an existing library file.
            os.link(temporary, destination)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    os.unlink(source)


def _already_organized(release: EpisodeRelease, show: ShowFolder) -> bool:
    present = _video_episodes_in_library(show, release.season)
    return set(release.episodes).issubset(present)


def organize_completed_torrent(
    torrent: dict, download_dir: str, shows_dir: str,
) -> OrganizationResult:
    """File recognized episode videos and report whether the torrent can be removed."""
    torrent_name = str(torrent.get("name", ""))
    torrent_release = parse_episode_release(torrent_name)
    content_path = _torrent_content_path(torrent, download_dir)
    video_files = _torrent_video_files(content_path, download_dir)

    if not video_files:
        inferred_name = torrent_name or (os.path.basename(content_path) if content_path else "")
        release = parse_episode_release(inferred_name)
        if release is None:
            return OrganizationResult(NOT_TV)
        title = release.series_title
        if not title:
            title, year = _series_context(torrent_name)
            release = EpisodeRelease(title, release.season, release.episodes, release.year or year)
        show, reason = match_library_show(title, shows_dir, release.year)
        if not show:
            return OrganizationResult(REVIEW, reason)
        if _already_organized(release, show):
            return OrganizationResult(ORGANIZED, "episode files were already moved")
        return OrganizationResult(REVIEW, "episode source files were not found")

    parsed: list[tuple[str, EpisodeRelease]] = []
    unparsed: list[str] = []
    for path in video_files:
        release = _release_for_video(path, torrent_release, torrent_name, len(video_files))
        if release is None:
            unparsed.append(path)
        else:
            parsed.append((path, release))
    if not parsed:
        if torrent_release:
            return OrganizationResult(REVIEW, "torrent name looks episodic but its video files do not identify episodes")
        return OrganizationResult(NOT_TV)
    if unparsed:
        return OrganizationResult(REVIEW, "one or more video files do not identify an episode")

    moves: list[tuple[str, str]] = []
    for source, release in parsed:
        if not release.series_title:
            return OrganizationResult(REVIEW, "episode release has no identifiable series title")
        show, reason = match_library_show(release.series_title, shows_dir, release.year)
        if not show:
            return OrganizationResult(REVIEW, reason)
        filename = os.path.basename(source)
        destination = os.path.join(_episode_folder(show.path, release.season), filename)
        if not _is_within(destination, shows_dir):
            return OrganizationResult(REVIEW, "destination path is outside the shows library")
        existing_episodes = _video_episodes_in_library(show, release.season)
        if set(release.episodes) & existing_episodes:
            try:
                same_file = os.path.lexists(destination) and os.path.samefile(source, destination)
            except OSError:
                same_file = False
            if not same_file:
                episode_label = ",".join(f"E{episode:02d}" for episode in release.episodes)
                return OrganizationResult(
                    REVIEW,
                    f"episode(s) S{release.season:02d}{episode_label} already exist under another file",
                )
        moves.append((source, destination))

    destinations: set[str] = set()
    for source, destination in moves:
        key = os.path.normcase(os.path.abspath(destination))
        if key in destinations:
            return OrganizationResult(REVIEW, "multiple torrent files have the same destination name")
        destinations.add(key)
        if os.path.lexists(destination):
            try:
                if not os.path.samefile(source, destination):
                    return OrganizationResult(REVIEW, f"destination already exists: {destination}")
            except OSError:
                return OrganizationResult(REVIEW, f"destination already exists: {destination}")

    try:
        for source, destination in moves:
            _move_without_overwrite(source, destination)
    except OSError as error:
        return OrganizationResult(REVIEW, f"could not safely move episode file: {error}")

    return OrganizationResult(ORGANIZED, f"filed {len(moves)} episode video(s)")
