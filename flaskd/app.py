from flask import Flask, render_template, request

from src.download_torrent import download_torrent
from src.query_torrent_api import search_for_torrent

app = Flask(__name__, static_folder="static", template_folder="templates")


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
    download_torrent(request.args.get('magnet'), '.')