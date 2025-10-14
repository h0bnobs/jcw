import time
from qbittorrent import Client
from flask import Flask, render_template, request, redirect, session

from flask_socketio import SocketIO
from src.qbt.download_torrent import download_torrent
from src.qbt.find_torrents import get_torrents

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
    download_torrent(request.args.get('magnet'), '.', request.args.get('name'))
    query = session.get('query', '')
    return redirect(f'/search?query={query}')

@app.route('/downloads', methods=['GET', 'POST'])
def downloads():
    