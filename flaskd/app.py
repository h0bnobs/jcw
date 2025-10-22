import json
import os
import platform
import subprocess
from threading import Event

from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO

from src.qbt.download_history import get_all_completed_downloads
from src.qbt.download_torrent import download_torrent, is_vpn
from src.qbt.find_torrents import get_torrents
from src.qbt.remove_torrents import remove_completed_torrents
from src.qbt.torrent_download_status import get_active_downloads

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)
CONFIG_FILE = 'config.json'


@app.route('/')
def home():
    download_dir = session.get('download_dir', app.config['DOWNLOAD_DIR'])
    return render_template('search.html', download_dir=download_dir)


@app.route('/search', methods=['GET'])
def search():
    if not is_vpn():
        return "<script>alert('VPN is not active!'); window.history.back();</script>"
    query = request.args.get('query')
    page = int(request.args.get('page', 1))

    if not query:
        return "No query provided", 400

    session['query'] = query
    session['page'] = page

    results = get_torrents(query, page=page)
    download_dir = session['download_dir']
    return render_template('results.html', results=results, download_dir=download_dir, query=query, page=page)


@app.route('/download-torrent', methods=['GET'])
def download():
    if not is_vpn():
        return "<script>alert('VPN is not active!'); window.history.back();</script>"
    download_dir = session.get('download_dir', app.config['DOWNLOAD_DIR'])
    download_torrent(request.args.get('magnet'), download_dir)
    query = session.get('query', '')
    return redirect(f'/search?query={query}')


@app.route('/active-downloads', methods=['GET', 'POST'])
def active_downloads():
    active = [
        {
            'content_path': d['content_path'],
            'dlspeed': int(d['dlspeed']) / 1000000,
            'eta': int(d['eta']),
            'progress': round(float(d['progress']) * 100, 0),
        }
        for d in get_active_downloads()
    ]
    download_dir = session['download_dir']
    return render_template('active-downloads.html', active_downloads=active, download_dir=download_dir)


def open_file_or_folder(path):
    """
    Gpt Special this\n
    Open a media file using the default application based on the operating system.
    :param path: Path to the media file to be opened.
    :return: None
    """
    if platform.system().lower() == 'linux' or platform.system().lower() == 'darwin':
        subprocess.Popen(['open', path])
    elif platform.system().lower() == 'windows':
        os.startfile(path)


@app.route('/open/<path:filename>')
def open_file(filename):
    full_path = os.path.join(session['download_dir'], filename)
    open_file_or_folder(full_path)
    return redirect('/download-history')


@app.route('/open-folder/<path:foldername>')
def open_folder(foldername):
    open_file_or_folder(session['download_dir'])
    return redirect(request.referrer)


@app.route('/download-history', methods=['GET', 'POST'])
def download_history():
    return render_template('download-history.html', download_dir=session['download_dir'],
                           downloads=get_all_completed_downloads())


@app.route('/delete-file', methods=['POST'])
def delete_file():
    filename = request.form.get('filename')
    full_path = os.path.join(session['download_dir'], filename)
    if os.path.exists(full_path):
        os.remove(full_path)
    return redirect('/download-history')


thread = None
thread_stop_event = Event()


def background_download_status():
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


@app.route('/set-download-dir', methods=['POST'])
def set_download_dir():
    path = request.form.get('download_dir')
    if not os.path.isdir(path):
        return "Invalid directory", 400
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'download_dir': path}, f)
    session['download_dir'] = path
    return redirect('/')


@app.before_request
def remove_torrent():
    remove_completed_torrents()
