import json
import os
import argparse

from flaskd.app import app, socketio

CONFIG_FILE = 'config.json'

if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description="JCW Application")
    # parser.add_argument('--vpn-bypass', action='store_true', help="Bypass VPN check")
    # args = parser.parse_args()
    default_config = {
        "download_dir": os.path.join(os.path.expanduser("~"), "Desktop"),
        "vpn_bypass": "false",
        "bind_address": "0.0.0.0"
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        app.config['DOWNLOAD_DIR'] = default_config["download_dir"]
        app.config['VPN_BYPASS'] = default_config["vpn_bypass"]
        app.config['BIND_ADDRESS'] = default_config["bind_address"]
    else:
        with open(CONFIG_FILE) as f:
            try:
                session_data = json.load(f)
            except json.JSONDecodeError:
                session_data = {}
        download_dir = session_data.get("download_dir", "")
        vpn_bypass = session_data.get("vpn_bypass", "")
        if download_dir == '':
            download_dir = default_config["download_dir"]
            session_data['download_dir'] = download_dir
            with open(CONFIG_FILE, "w") as f:
                json.dump(session_data, f, indent=4)
        app.config['DOWNLOAD_DIR'] = download_dir
        app.config['VPN_BYPASS'] = vpn_bypass
        app.config['BIND_ADDRESS'] = session_data.get('bind_address', '0.0.0.0')

    bind_address = app.config.get('BIND_ADDRESS', '0.0.0.0')
    socketio.run(app, host=bind_address, port=80, debug=True, allow_unsafe_werkzeug=True)
