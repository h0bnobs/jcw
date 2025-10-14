from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()


def download_torrent(magnet_link: str, download_path: str, torrent_name: str):
    qb.download_from_link(magnet_link, savepath="/home/max/PycharmProjects/jcw/tempdownloads/")
    return "/home/max/PycharmProjects/jcw/tempdownloads/"

