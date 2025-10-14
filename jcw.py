from src.db.db import initialise_database
from src.download_torrents.check_torrent_api import check_torrent_api_running, start_torrent_api

from flaskd.app import app, socketio

if __name__ == '__main__':

    # check if its running, if not try and find it on the system and start it.
    # if not found on the system, download it from git and start it.
    if not check_torrent_api_running():
        start_torrent_api()
    # initialise_database()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
