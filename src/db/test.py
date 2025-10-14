from src.db.db import add_torrent, get_connection

add_torrent(get_connection(), 'name', 'magnet', None)