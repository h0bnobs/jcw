import asyncio
import os
from torrentp import TorrentDownloader
from src.check_vpn import is_vpn

async def monitor_progress(downloader, sid, socketio):
    while True:
        progress = downloader.get_progress()
        if socketio:
            socketio.emit('torrent_progress', {'progress': int(progress)}, to=sid)
        if progress >= 100:
            break
        await asyncio.sleep(2)


def download_torrent(magnet_link: str, download_path: str, torrent_name: str, sid=None, socketio=None) -> str:
    if not is_vpn():
        raise RuntimeError("VPN is not enabled.")

    downloader = TorrentDownloader(magnet_link, download_path)

    async def run_both():
        await asyncio.gather(
            downloader.start_download(),
            monitor_progress(downloader, sid, socketio)
        )

    asyncio.run(run_both())
    return os.path.join(download_path, torrent_name)
