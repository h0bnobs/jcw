import requests

def check_torrent_api_running(port: int=8009) -> bool:
    """
    Check if the torrent API is running on the specified port.
    :param port: Port number to check, default is 8009.
    :return: True if the API is running, False otherwise.
    """
    return 'Torrents Api' in (response := requests.get(f"http://localhost:{port}/")).text and response.status_code == 200
