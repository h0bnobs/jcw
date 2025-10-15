from flaskd.app import app, socketio
import os
import json

CONFIG_FILE = 'config.json'

if __name__ == '__main__':
    default_config = {
        "download_dir": os.path.join(os.path.expanduser("~"), "Desktop")
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        app.config['DOWNLOAD_DIR'] = default_config["download_dir"]
    else:
        with open(CONFIG_FILE) as f:
            session_data = json.load(f)
        download_dir = session_data.get("download_dir", "")
        print(download_dir)
        if download_dir == '':
            download_dir = default_config["download_dir"]
        with open(CONFIG_FILE, "w") as f:
            json.dump({"download_dir": download_dir}, f, indent=4)
        app.config['DOWNLOAD_DIR'] = download_dir
    socketio.run(app, host='0.0.0.0', port=80, debug=True, allow_unsafe_werkzeug=True)
