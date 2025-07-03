import requests

from src.download_torrents.check_torrent_api import check_torrent_api_running


class TorrentResult:
    """
    Represents a torrent search result.
    Attributes:
        name (str): Filename of the torrent.
        category (str): Category of the torrent.
        date (str): Date when the torrent was uploaded.
        hash (str): Unique hash of the torrent.
        leechers (int): Number of leechers for the torrent.
        magnet (str): Magnet link for the torrent.
        seeders (int): Number of seeders for the torrent.
        size (str): Size of the torrent file.
        uploader (str): Uploader of the torrent.
        url (str): URL to the torrent page.
    """

    def __init__(self, name, category, date, hash, leechers, magnet, seeders, size, uploader, url):
        self.name = name
        self.category = category
        self.date = date
        self.hash = hash
        self.leechers = int(leechers)
        self.magnet = magnet
        self.seeders = int(seeders)
        self.size = size
        self.uploader = uploader
        self.url = url

    def __repr__(self):
        return f"<TorrentResult {self.name} ({self.seeders} seeders / {self.leechers} leechers)>"


def search_for_torrent(query: str):
    if check_torrent_api_running():
        response = requests.get(f'http://localhost:8009/api/v1/search?site=piratebay&query={query}')
        results: list[dict] = response.json().get(
            'data')  # response.json is a dict. ['data'] is a list of dicts containing the actual torrent data.

        return [TorrentResult(**r) for r in results]
    # print(
    #     f'{torrents[0].name}\n{torrents[0].category}\n{torrents[0].date}\n{torrents[0].hash}\n{torrents[0].leechers}\n{torrents[0].magnet}\n'
    #     f'{torrents[0].seeders}\n{torrents[0].size}\n{torrents[0].uploader}\n{torrents[0].url}')
    # for torrent in torrents:
    #     print(torrent.name, torrent.seeders, torrent.magnet)
