import psutil
import requests
from qbittorrent import Client

qb = Client('http://localhost:9000/')
qb.login()
prefs = {
    "max_ratio_enabled": True,
    "max_ratio": 0
}
qb.set_preferences(**prefs)


def get_ip_address() -> str:
    """
    Get the current public IP address of the machine.
    :return: Public IP address as a string.
    """
    ip = requests.get('https://api.ipify.org').content.decode('utf8')
    print(ip)
    print(format(ip))
    return format(ip)


def is_vpn() -> bool:
    """
    Check if the current IP address is associated with a VPN service.
    :return: True if the IP is a VPN, False otherwise.
    """
    # api_key = "2c1294b9924b42fe9eba83fcf032374d"  # sigma
    # response = requests.get(f"https://vpnapi.io/api/{get_ip_address()}?key={api_key}")
    # data = json.loads(response.text)
    # return data["security"]["vpn"]
    nics = psutil.net_if_addrs()
    for nic in nics.items():
        if "tun" in nic[0] or "tap" in nic[0] or "vpn" in nic[0] or "wg" in nic[0] or "ovpn" in nic[0]:
            return True
    return False


def download_torrent(magnet_link: str, download_path: str):
    qb.download_from_link(magnet_link, savepath=download_path)
    return download_path
