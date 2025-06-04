import requests
import json

# all nicked from https://github.com/Mo61n/VPN-Detector-Python

def get_ip_address() -> str:
    """
    Get the current public IP address of the machine.
    :return: Public IP address as a string.
    """
    data = str(requests.get('http://checkip.dyndns.com/').text) #https doesnt work....?
    return data.split(': ')[-1].split('<')[0]


def is_vpn() -> bool:
    """
    Check if the current IP address is associated with a VPN service.
    :return: True if the IP is a VPN, False otherwise.
    """

    api_key = "2c1294b9924b42fe9eba83fcf032374d"
    response = requests.get(f"https://vpnapi.io/api/{get_ip_address()}?key={api_key}")
    data = json.loads(response.text)
    return data["security"]["vpn"]

