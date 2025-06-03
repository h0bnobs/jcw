import requests

class TorrentResult:
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


def search_for_torrent():
    response = requests.get('http://localhost:8009/api/v1/search?site=piratebay&query=mobland')
    results = response.json().get('data')

    torrents = [TorrentResult(**r) for r in results]
    for torrent in torrents:
        print(torrent.name, torrent.seeders, torrent.magnet)


if __name__ == '__main__':
    search_for_torrent()