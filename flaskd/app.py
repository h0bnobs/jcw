from flask import Flask, render_template, request

from flask_socketio import SocketIO
from src.download_torrents.download_torrent import download_torrent
from src.download_torrents.query_torrent_api import search_for_torrent

app = Flask(__name__, static_folder="static", template_folder="templates")
socketio = SocketIO(app)

@app.route('/')
def home():
    return render_template('search.html')


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        return "No query provided", 400

    results = search_for_torrent(query)
    return render_template('results.html', results=results, query=query)

@app.route('/download-torrent', methods=['GET'])
def download():
    download_torrent(request.args.get('magnet'), '.', request.args.get('name'))

import threading

@socketio.on('start_download')
def handle_start_download(data):
    magnet = data.get('magnet')
    name = data.get('name')
    sid = request.sid

    def run_download():
        try:
            download_torrent(magnet, '.', name, sid=sid, socketio=socketio)
            socketio.emit('torrent_complete', {'message': 'Download complete'}, to=sid)
        except Exception as e:
            socketio.emit('torrent_error', {'message': str(e)}, to=sid)

    threading.Thread(target=run_download).start()
