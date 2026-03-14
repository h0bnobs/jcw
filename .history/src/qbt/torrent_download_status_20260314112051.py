from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()
prefs = {
    "max_ratio_enabled": True,
    "max_ratio": 0
}
qb.set_preferences(**prefs)


def get_active_downloads() -> list:
    return qb.torrents(filter='downloading')


def pause_download(torrent_hash: str):
    qb.pause(torrent_hash)


def resume_download(torrent_hash: str):
    qb.resume(torrent_hash)


def remove_download(torrent_hash: str):
    qb.delete(torrent_hash)
