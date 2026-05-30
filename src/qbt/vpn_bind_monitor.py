"""
VPN-bind monitor: keep qBittorrent pinned to the current VPN tunnel IP.

Why this exists
---------------
qBittorrent is bound to the VPN's IP address (not the interface name — binding
by name uses SO_BINDTODEVICE which breaks all UDP/DHT on a WireGuard
interface; see client.vpn_bind_address). Binding to the IP keeps peer traffic
on the tunnel AND acts as a per-app kill switch: if that IP disappears,
libtorrent cannot send anything, so it stalls instead of leaking to the
physical NIC. Verified live: a stale/bogus bind drops DHT to 0 and produces no
torrent traffic on the physical interface.

The catch is that Mullvad hands out a NEW tunnel IP on every reconnect and on
its (roughly weekly) key rotation. When that happens qBittorrent stays pinned
to the old, now non-existent address and every download silently stalls. This
daemon watches the tunnel IP and re-pins qBittorrent whenever it changes.

Re-pinning is done purely via the WebUI API. Verified live: changing
`current_interface_address` makes libtorrent reopen its listen socket and DHT
recovers within ~30s with no process restart, so downloads are not interrupted.

Run as:  python -m src.qbt.vpn_bind_monitor
Intended to run as the `jcw-vpn-bind.service` systemd unit.
"""
from __future__ import annotations

import time

from . import client
from .client import QbitUnavailable, vpn_bind_address

# How often to check the tunnel IP. Cheap (a psutil call plus one API read),
# and an IP change only needs to be caught within a few seconds.
POLL_INTERVAL = 10.0
# After a failed API call, wait a bit before retrying so a down/restarting
# qBittorrent is not hammered.
ERROR_BACKOFF = 15.0


def _current_bind(c) -> str:
    """Return qBittorrent's currently configured interface-address bind."""
    return c.preferences().get("current_interface_address", "") or ""


def apply_bind(c, ip: str) -> None:
    """Pin qBittorrent to `ip` via the API (never the interface name)."""
    c.set_preferences(current_network_interface="", current_interface_address=ip)


def check_once(last_logged_state: dict) -> None:
    """One monitor iteration. Never raises — logs and returns on any error.

    `last_logged_state` carries small bits of cross-iteration state so we log
    transitions once rather than spamming every poll.
    """
    vpn_ip = vpn_bind_address()

    if not vpn_ip:
        # Tunnel is down (reconnecting / VPN off). Do NOT touch the bind: the
        # stale pin keeps qBittorrent failing closed, so nothing leaks. Log the
        # transition once.
        if last_logged_state.get("vpn_up") is not False:
            print("[vpn-bind] VPN tunnel down — leaving qBit bound (fails closed, no leak)")
            last_logged_state["vpn_up"] = False
        return

    if last_logged_state.get("vpn_up") is not True:
        print(f"[vpn-bind] VPN tunnel up, IP {vpn_ip}")
        last_logged_state["vpn_up"] = True

    try:
        c = client.qb()
        current = _current_bind(c)
        if current != vpn_ip:
            apply_bind(c, vpn_ip)
            print(f"[vpn-bind] re-pinned qBittorrent: {current or '<unset>'} -> {vpn_ip}")
            last_logged_state["bind"] = vpn_ip
        elif last_logged_state.get("bind") != vpn_ip:
            # First time we observe a matching bind — note it once, quietly.
            print(f"[vpn-bind] qBittorrent already pinned to {vpn_ip}")
            last_logged_state["bind"] = vpn_ip
        last_logged_state["_errored"] = False
    except QbitUnavailable as e:
        print(f"[vpn-bind] qBittorrent unavailable: {e}")
        client.reset_connection()
        last_logged_state["_errored"] = True
    except Exception as e:
        # qBit may have restarted under us, leaving a stale session. Reset so
        # the next iteration reconnects cleanly.
        print(f"[vpn-bind] error talking to qBittorrent: {e}")
        client.reset_connection()
        last_logged_state["_errored"] = True


def run() -> None:
    print(f"[vpn-bind] monitor started (poll every {POLL_INTERVAL:.0f}s)")
    state: dict = {}
    while True:
        before = time.time()
        check_once(state)
        # Back off after an error iteration so we do not spin on a down qBit.
        delay = ERROR_BACKOFF if state.get("_errored") else POLL_INTERVAL
        elapsed = time.time() - before
        time.sleep(max(1.0, delay - elapsed))


if __name__ == "__main__":
    run()
