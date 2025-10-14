from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()

def get_all_torrent_download_status():
