import time
from qbittorrent import Client
from flask import Flask, render_template, request, redirect, session
from threading import Event

from flask_socketio import SocketIO
from src.qbt.download_torrent import download_torrent, is_vpn
from src.qbt.find_torrents import get_torrents
from src.qbt.torrent_download_status import get_active_downloads

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)


@app.route('/')
def home():
    return render_template('search.html')


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        return "No query provided", 400

    session['query'] = query

    results = get_torrents(query)
    return render_template('results.html', results=results, query=query)


@app.route('/download-torrent', methods=['GET'])
def download():
    if not is_vpn():
        return "<script>alert('VPN is not active!'); window.history.back();</script>"
    download_torrent(request.args.get('magnet'), '.', request.args.get('name'))
    query = session.get('query', '')
    return redirect(f'/search?query={query}')


@app.route('/downloads', methods=['GET', 'POST'])
def downloads():
    active_downloads = [
        {
            'content_path': d['content_path'],
            'dlspeed': int(d['dlspeed']) / 1000000,
            'eta': int(d['eta']),
            'progress': round(float(d['progress']) * 100, 0),
        }
        for d in get_active_downloads()
    ]
    return render_template('downloads.html', active_downloads=active_downloads)


thread = None
thread_stop_event = Event()


def background_download_status():
    """Send active downloads to all clients every 1 second."""
    while not thread_stop_event.is_set():
        active_downloads = [
            {
                'content_path': d['content_path'],
                'dlspeed': int(d['dlspeed']) / 1000000,
                'eta': int(d['eta']),
                'progress': round(float(d['progress']) * 100, 0),
            }
            for d in get_active_downloads()
        ]
        socketio.emit('update_downloads', active_downloads)
        socketio.sleep(1)  # sleep 1s between updates


@socketio.on('connect')
def handle_connect():
    global thread
    if thread is None:
        thread = socketio.start_background_task(background_download_status)
