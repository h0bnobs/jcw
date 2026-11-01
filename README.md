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
