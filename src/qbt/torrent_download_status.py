from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()

def get_active_downloads() -> list:
    return qb.torrents(filter='downloading')
