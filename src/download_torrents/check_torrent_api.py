import os
import subprocess
import time

import requests
from git import Repo

def start_torrent_api() -> None:
    """
    Start the Torrent API server.
    :return: None
    """
    torrent_api_path = locate_torrent_api()
    subprocess.Popen(["python", 'main.py'], cwd=torrent_api_path)
    time.sleep(0.4)


def check_torrent_api_running(port: int = 8009) -> bool:
    """
    Check if the torrent API is running on the specified port.
    :param port: Port number to check, default is 8009.
    :return: True if the API is running, False otherwise.
    """
    try:
        response = requests.get(f"http://localhost:{port}/")
        return 'Torrents Api' in response.text and response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def locate_torrent_api() -> str | None:
    """
    Locate the Torrent API executable.
    This function checks common directories for the Torrent API executable.
    :return: Path to the Torrent API executable if found, otherwise None.
    """
    possible_paths = [
        os.path.expanduser("~/Torrent-Api-py"),
        "/opt/Torrent-Api-py",
        os.getcwd()
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def download_torrent_api(installation_directory: str = os.getcwd()) -> None:
    """
    Download the Torrent API from GitHub if it is not already present.
    :param installation_directory: FULL directory where the Torrent API will be installed.
    :return: None
    """
    installation_directory += '/Torrent-Api-py'
    Repo.clone_from('https://github.com/Ryuk-me/Torrent-Api-py', installation_directory)
