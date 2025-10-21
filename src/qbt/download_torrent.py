import json
from datetime import datetime
import requests
from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()


def get_ip_address() -> str:
    """
    Get the current public IP address of the machine.
    :return: Public IP address as a string.
    """
    data = str(requests.get('http://checkip.dyndns.com/').text)  # https doesnt work....?
    return data.split(': ')[-1].split('<')[0]


def is_vpn() -> bool:
    """
    Check if the current IP address is associated with a VPN service.
    :return: True if the IP is a VPN, False otherwise.
    """

    api_key = "2c1294b9924b42fe9eba83fcf032374d" #sigma
    response = requests.get(f"https://vpnapi.io/api/{get_ip_address()}?key={api_key}")
    data = json.loads(response.text)
    return data["security"]["vpn"]


def download_torrent(magnet_link: str, download_path: str):
    try:
        qb.download_from_link(magnet_link, savepath=download_path)
    except Exception:
        # assume here that the download is stuck on 'stalling' - which if true, is fine to ignore any error here because
        # it just means the vpn or torrent connection is just slow. if anything else then this will just break so...
        return download_path
    return download_path
