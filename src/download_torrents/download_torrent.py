import asyncio
import os

from src.local_torrent import TorrentDownloader
from src.download_torrents.check_vpn import is_vpn
from src.db.db import get_connection, update_progress

async def monitor_progress(downloader, sid, socketio, torrent_id=None, db_fn=None):
    db = get_connection() if torrent_id is not None else None
    while True:
        progress = int(downloader.get_progress())
        if socketio:
            socketio.emit('torrent_progress', {'progress': progress}, to=sid)
        if db:
            db_fn(db, torrent_id, progress)
        if progress >= 100:
            break
        await asyncio.sleep(2)
    if db:
        db.close()


def download_torrent(magnet_link: str, download_path: str, torrent_name: str,
                     *, sid=None, socketio=None,
                     torrent_id: int | None = None,
                     db_mark_completed=None) -> str:
    if not is_vpn():
        raise RuntimeError("Please turn a VPN on.")

    downloader = TorrentDownloader(magnet_link, download_path)

    async def run_both():
        await asyncio.gather(
            downloader.start_download(),
            monitor_progress(downloader, sid, socketio,
                             torrent_id=torrent_id,
                             db_fn=update_progress)
        )

    asyncio.run(run_both())
    # mark 100% in DB once run_both() returns
    if torrent_id is not None and db_mark_completed is not None:
        db = get_connection()
        db_mark_completed(db, torrent_id)
        db.close()
    return os.path.join(download_path, torrent_name)
