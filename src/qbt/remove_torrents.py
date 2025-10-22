from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()
prefs = {
    "max_ratio_enabled": True,
    "max_ratio": 0
}
qb.set_preferences(**prefs)

def remove_completed_torrents():
    for t in qb.torrents():
        if t['state'] == 'stoppedUP':
            qb.delete(t['hash'])