import asyncio
from torrentp import TorrentDownloader

torrent_file = TorrentDownloader("magnet:...", '.')
asyncio.run(torrent_file.start_download())
