import asyncio
from torrentp import TorrentDownloader

from src.check_vpn import is_vpn


def download_torrent(magnet_link: str, download_path: str):
    """
    Download a torrent file from a magnet link.

    :param magnet_link: Magnet link of the torrent to download.
    :param download_path: Directory where the torrent file will be saved.
    """
    if is_vpn():
        downloader = TorrentDownloader(magnet_link, download_path)
        asyncio.run(downloader.start_download())