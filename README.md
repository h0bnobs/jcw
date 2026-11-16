# jcw

Simple torrenting portal.

### Prerequisites

- [qBittorrent](https://www.qbittorrent.org/)
- [qBittorrent WebUI enabled](https://github.com/lgallard/qBittorrent-Controller/wiki/How-to-enable-the-qBittorrent-Web-UI)
  on port 9000
- Paid VPN subscription from any major provider

#### WebUI setup

- In qBittorrent, go to Tools -> WebUI and tick `Web User Interface (Remote control)`.
- Set the port to `9000`.
- Set a Username and password.
- Enable `Bypass authentication for clients on localhost`.
- Head to http://localhost:9000/ to verify

## TV episodes

JCW can file completed TV episodes into an existing shows library without
changing the configured download directory. Set `shows_dir` in `config.json`
or the `JCW_SHOWS_DIR` environment variable (defaults to `/media/shows`).
Existing show folders must use the `Show Name (Year) [tmdbid-ID]` convention;
episodes are placed in `Season 01/`, `Season 02/`, and so on.

No TMDB API key is needed. JCW matches release names against those existing
folders and leaves unknown or ambiguous episodes in qBittorrent for review.
Movies and downloads that do not look like episodes keep their existing
handling. The completion worker starts when JCW first receives a web request
and then continues polling while JCW is running.
# Local development with Nix

The homepage browses films and TV shows from Cinemeta without an API key.
Select a title, then **Find downloads** to search the existing torrent sources.
**Torrent search** in the sidebar still provides direct search and magnet entry.
Metadata is cached in memory for 15 minutes (up to 128 responses). Catalogue
requests go to Cinemeta; posters load directly from the image URLs it supplies.
An internet connection is required. If the service is unavailable, direct
torrent search remains accessible. Browsing metadata does not start downloads.

Run `nix run` from a writable directory, then open http://127.0.0.1:8080.
The flake supplies the Python dependencies on macOS and Linux; no pip installation
or root privileges are needed. Configuration is stored in `config.json` in the
working directory. qBittorrent and VPN services remain external dependencies;
the UI can start without them, but downloads require a configured backend.

For live source edits, run `nix develop` followed by `python jcw.py`.
Override the listener with `JCW_HOST` and `JCW_PORT` if needed.
Run the unit tests with `python -m pytest src/tests/test_*.py` in the shell.
