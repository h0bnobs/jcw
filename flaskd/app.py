import json
import os
import platform
import re
import subprocess
import time
from threading import Event

from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO

from src.qbt.download_history import get_all_completed_downloads
from src.qbt.download_torrent import download_torrent, is_vpn
from src.qbt.find_torrents import get_torrents
from src.qbt.remove_torrents import remove_completed_torrents
from src.qbt.torrent_download_status import (
    get_active_downloads, pause_download, resume_download, remove_download,
    force_reannounce, force_recheck, force_start_torrent, boost_torrent,
)
from src.qbt.client import is_available as qbit_available

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)
CONFIG_FILE = 'config.json'


@app.context_processor
def inject_globals():
    host = app.config.get('BIND_ADDRESS', '0.0.0.0')
    if host == '0.0.0.0':
        host = request.host.split(':')[0]
    return {
        'download_dir': app.config.get('DOWNLOAD_DIR', ''),
        'bind_address': app.config.get('BIND_ADDRESS', '0.0.0.0'),
        'qbit_host': host,
    }


@app.route('/')
def home():
    return render_template('search.html', vpn_bypass=app.config.get("VPN_BYPASS", False))


@app.route('/search', methods=['GET'])
def search():
    vpn_bypass = app.config.get("VPN_BYPASS", False)
    if not vpn_bypass and not is_vpn():
        return "<script>alert('VPN is not active!'); window.history.back();</script>"
    query = request.args.get('query')
    page = int(request.args.get('page', 1))

    if not query:
        return "No query provided", 400

    session['query'] = query
    session['page'] = page

    results = get_torrents(query, page=page)
    return render_template('results.html', results=results, query=query, page=page)


def _alert_back(msg: str) -> str:
    """Show a JS alert with `msg` then send the user back. Keeps API surface tiny."""
    safe = msg.replace("\\", "\\\\").replace("'", "\\'")
    return f"<script>alert('{safe}'); window.history.back();</script>"


@app.route('/download-torrent', methods=['GET'])
def download():
    vpn_bypass = app.config.get("VPN_BYPASS", False)
    if not vpn_bypass and not is_vpn():
        return _alert_back('VPN is not active!')
    if not qbit_available():
        return _alert_back('qBittorrent is not running on port 9000.')
    result = download_torrent(request.args.get('magnet'), app.config['DOWNLOAD_DIR'])
    if not result.get('ok'):
        return _alert_back(result.get('message', 'Failed to add torrent'))
    return redirect('/active-downloads')


@app.route('/download-magnet', methods=['POST'])
def download_magnet():
    vpn_bypass = app.config.get("VPN_BYPASS", False)
    if not vpn_bypass and not is_vpn():
        return _alert_back('VPN is not active!')
    magnet = request.form.get('magnet', '').strip()
    if not magnet.startswith('magnet:?'):
        return _alert_back("That doesn't look like a magnet link.")
    if not qbit_available():
        return _alert_back('qBittorrent is not running on port 9000.')
    result = download_torrent(magnet, app.config['DOWNLOAD_DIR'])
    if not result.get('ok'):
        return _alert_back(result.get('message', 'Failed to add torrent'))
    return redirect('/active-downloads')


@app.route('/pause-torrent', methods=['POST'])
def pause_torrent_route():
    torrent_hash = request.form.get('hash', '')
    if not re.match(r'^[a-fA-F0-9]{40}$', torrent_hash):
        return 'Invalid hash', 400
    pause_download(torrent_hash)
    return '', 204


@app.route('/resume-torrent', methods=['POST'])
def resume_torrent_route():
    torrent_hash = request.form.get('hash', '')
    if not re.match(r'^[a-fA-F0-9]{40}$', torrent_hash):
        return 'Invalid hash', 400
    resume_download(torrent_hash)
    return '', 204


@app.route('/remove-torrent', methods=['POST'])
def remove_torrent_route():
    torrent_hash = request.form.get('hash', '')
    if not re.match(r'^[a-fA-F0-9]{40}$', torrent_hash):
        return 'Invalid hash', 400
    remove_download(torrent_hash)
    return '', 204


@app.route('/boost-torrent', methods=['POST'])
def boost_torrent_route():
    """One-click rescue for a stuck torrent: re-inject trackers + force-start + reannounce."""
    torrent_hash = request.form.get('hash', '')
    if not re.match(r'^[a-fA-F0-9]{40}$', torrent_hash):
        return 'Invalid hash', 400
    boost_torrent(torrent_hash)
    return '', 204


@app.route('/reannounce-torrent', methods=['POST'])
def reannounce_torrent_route():
    torrent_hash = request.form.get('hash', '')
    if not re.match(r'^[a-fA-F0-9]{40}$', torrent_hash):
        return 'Invalid hash', 400
    force_reannounce(torrent_hash)
    return '', 204


@app.route('/recheck-torrent', methods=['POST'])
def recheck_torrent_route():
    torrent_hash = request.form.get('hash', '')
    if not re.match(r'^[a-fA-F0-9]{40}$', torrent_hash):
        return 'Invalid hash', 400
    force_recheck(torrent_hash)
    return '', 204


def _serialize_torrent(d: dict) -> dict:
    """Turn a raw qBit torrent dict into the slim structure the UI expects.

    Adds `num_seeds` / `num_leechs` so the UI can hint when a torrent is
    starved for peers — the underlying cause of most metadata stalls.
    """
    return {
        'hash': d['hash'],
        'name': d.get('name', ''),
        'content_path': d.get('content_path', ''),
        'dlspeed': int(d.get('dlspeed', 0)) / 1000000,
        'eta': int(d.get('eta', 0)),
        'progress': round(float(d.get('progress', 0)) * 100, 0),
        'state': d.get('state', ''),
        'num_seeds': int(d.get('num_seeds', 0)),
        'num_leechs': int(d.get('num_leechs', 0)),
        'size': int(d.get('size', 0)),
    }


@app.route('/active-downloads', methods=['GET', 'POST'])
def active_downloads():
    active = [_serialize_torrent(d) for d in get_active_downloads()]
    return render_template('active-downloads.html', active_downloads=active)

@app.route('/api/nics', methods=['GET'])
def list_nics():
    import psutil
    nics = []
    for name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family.name == 'AF_INET':  # IPv4 only
                nics.append({'name': name, 'address': addr.address})
    return json.dumps(nics), 200, {'Content-Type': 'application/json'}


@app.route('/advanced-settings', methods=['GET', 'POST'])
def advanced_settings():
    if request.method == 'POST':
        vpn_bypass = request.form.get('vpn_bypass') == 'on'
        bind_address = request.form.get('bind_address', '0.0.0.0').strip()
        app.config['VPN_BYPASS'] = vpn_bypass
        app.config['BIND_ADDRESS'] = bind_address

        # Read existing config
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config['vpn_bypass'] = vpn_bypass
        config['bind_address'] = bind_address
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return redirect('/advanced-settings')

    vpn_bypass = app.config.get('VPN_BYPASS', False)
    bind_address = app.config.get('BIND_ADDRESS', '0.0.0.0')
    return render_template('advanced-settings.html', vpn_bypass=vpn_bypass, bind_address=bind_address)

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
    full_path = os.path.join(app.config['DOWNLOAD_DIR'], filename)
    open_file_or_folder(full_path)
    return redirect('/download-history')


@app.route('/open-folder/<path:foldername>')
def open_folder(foldername):
    open_file_or_folder(app.config['DOWNLOAD_DIR'])
    return redirect(request.referrer)


@app.route('/download-history', methods=['GET', 'POST'])
def download_history():
    return render_template('download-history.html',
                           downloads=get_all_completed_downloads(app.config['DOWNLOAD_DIR']))


@app.route('/delete-file', methods=['POST'])
def delete_file():
    filename = request.form.get('filename')
    full_path = os.path.join(app.config['DOWNLOAD_DIR'], filename)
    if os.path.exists(full_path):
        os.remove(full_path)
    return redirect('/download-history')


thread = None
thread_stop_event = Event()


def background_download_status():
    """Push the active-downloads list to all connected clients once per second.

    Auto-boosts any torrent stuck in `metaDL` for ~45s, but ONLY ONCE per
    torrent. Repeatedly poking a half-resumed torrent was causing state
    thrash (`metaDL` -> `checkingResumeData` -> `stoppedDL` -> ...) which
    made downloads vanish from the UI.

    Includes verbose diagnostic logging of state transitions so we can
    actually SEE which actor is removing a torrent (qBit auto-rule vs.
    our cleanup vs. UI filter).
    """
    from src.qbt.client import qb as _qb_client, QbitUnavailable as _QU

    metadl_first_seen: dict[str, float] = {}
    boosted: set[str] = set()
    last_states: dict[str, str] = {}
    AUTO_BOOST_AFTER = 45
    while not thread_stop_event.is_set():
        # Inspect ALL torrents (not just active) so we can log state changes
        # even when something gets booted out of the active set.
        try:
            all_t = _qb_client().torrents()
        except _QU:
            all_t = []
        except Exception as e:
            print(f"[bg-status] qb.torrents() failed: {e}")
            all_t = []

        present_now = {t.get('hash'): t for t in all_t}

        # Log state changes + disappearances.
        for h, prev in list(last_states.items()):
            if h not in present_now:
                print(f"[diag] torrent {h[:8]}... DISAPPEARED from qBit entirely (was state={prev}) — something deleted it")
                last_states.pop(h, None)
                metadl_first_seen.pop(h, None)
                boosted.discard(h)
        for h, t in present_now.items():
            cur = t.get('state', '?')
            if last_states.get(h) != cur:
                if h in last_states:
                    print(f"[diag] torrent {h[:8]}... state {last_states[h]} -> {cur} (progress={t.get('progress', 0):.3f}, peers={t.get('num_seeds', 0)}/{t.get('num_leechs', 0)})")
                else:
                    print(f"[diag] torrent {h[:8]}... NEW state={cur} name={t.get('name', '?')[:60]}")
                last_states[h] = cur

        # Filter to active for the UI.
        from src.qbt.torrent_download_status import COMPLETED_STATES as _COMPLETED
        raw = [t for t in all_t if t.get('state') not in _COMPLETED]
        now = time.time()
        live_hashes = {d.get('hash') for d in raw}
        for h in list(metadl_first_seen):
            if h not in live_hashes:
                metadl_first_seen.pop(h, None)
                boosted.discard(h)
        for d in raw:
            h = d.get('hash')
            if d.get('state') == 'metaDL' and h not in boosted:
                first = metadl_first_seen.setdefault(h, now)
                if now - first > AUTO_BOOST_AFTER:
                    print(f"[auto-boost] torrent {h[:8]}... stuck in metaDL — boosting (one-shot)")
                    boost_torrent(h)
                    boosted.add(h)
        active_downloads = [_serialize_torrent(d) for d in raw]
        socketio.emit('update_downloads', active_downloads)
        socketio.sleep(1)


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
    # Read existing config
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except Exception:
            config = {}
    config['download_dir'] = path
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    app.config['DOWNLOAD_DIR'] = path
    return redirect('/')

def remote_empty_directories_in_download_dir(download_dir) -> None:
    for root, dirs, files in os.walk(download_dir, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)

@app.route('/qbit', methods=['GET'])
def redirect_to_qbittorrent():
    host = app.config.get('BIND_ADDRESS', '0.0.0.0')
    if host == '0.0.0.0':
        host = request.host.split(':')[0]
    url = f'http://{host}:9000'
    return f'<html><head><meta http-equiv="refresh" content="0;url={url}"></head><body></body></html>'

@app.route('/jellyfin', methods=['GET'])
def fix_directory():
    """
    Hardcoded chown for my personal jellyfin media directory
    :return: None
    """
    subprocess.run(['chown', '-R', 'jellyfin:jellyfin', '/media'])
    return subprocess.run(['ls', '-al', '/media'], capture_output=True, text=True).stdout.replace('\n', '<br>') + '<br><a href="/">Go Back</a>'


# Periodic cleanup: previously this ran on EVERY HTTP request — meaning the
# download dir was walked dozens of times per page load and qBit was hit
# every time the favicon loaded. We now run it at most once per CLEANUP_INTERVAL.
CLEANUP_INTERVAL = 30  # seconds
_last_cleanup = 0.0


@app.before_request
def _maybe_cleanup():
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    try:
        remove_completed_torrents()
        remote_empty_directories_in_download_dir(app.config['DOWNLOAD_DIR'])
    except Exception as e:
        print(f"[cleanup] failed: {e}")
