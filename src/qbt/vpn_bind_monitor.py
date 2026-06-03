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

There are two ways the bind goes stale, and we must catch BOTH:

1. Key rotation (~weekly): Mullvad hands out a brand-new tunnel IP. qBit stays
   pinned to the old, now non-existent address. Caught by watching the IP.

2. Reconnect / relay switch: Mullvad tears down and recreates the tunnel but
   reuses the SAME IP. The IP is unchanged, so an IP-only watcher sees nothing
   to do — but the kernel assigns the recreated interface a NEW index, and
   libtorrent's listen socket is still scoped to the OLD index (e.g.
   `10.165.20.192%if44` when the live interface is now `if46`). Every outgoing
   UDP send then fails with ENODEV "No such device": tracker announces die and
   downloads hang on "downloading metadata", while DHT's persisted routing
   table masks it for a while. Caught by watching the interface index.

Re-pinning is done purely via the WebUI API. Verified live: setting
`current_interface_address` to "" and then back to the IP forces libtorrent to
rebuild its listen socket on the CURRENT interface index — trackers recover and
torrents move from metaDL to downloading within seconds, no process restart, so
active downloads are not interrupted. Simply re-writing the same IP is NOT
enough: qBit treats the unchanged value as a no-op and keeps the dead socket.

The brief empty-bind step is safe: it only runs while the tunnel is up, and the
host's default route is the tunnel, so traffic still egresses via the VPN during
the sub-second window before the IP is re-applied.

Run as:  python -m src.qbt.vpn_bind_monitor
Intended to run as the `jcw-vpn-bind.service` systemd unit.
"""
from __future__ import annotations

import socket
import time

from . import client
from .client import QbitUnavailable, vpn_interface

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
    """Pin qBittorrent to `ip`, forcing libtorrent to rebuild its socket.

    The empty-then-IP sequence is deliberate: writing the same IP that is
    already configured is a no-op for qBittorrent, so the listen socket stays
    scoped to a dead interface index after a reconnect. Clearing it first makes
    qBit tear the socket down, then re-applying the IP reopens it on the current
    index. Never bind by interface name (SO_BINDTODEVICE breaks UDP/DHT).
    """
    c.set_preferences(current_network_interface="", current_interface_address="")
    # Small gap so qBit actually applies the clear and tears the socket down
    # before we re-pin; without it the two writes can coalesce into a no-op.
    time.sleep(1.0)
    c.set_preferences(current_network_interface="", current_interface_address=ip)


def _ifindex(name: str) -> int | None:
    """Return the kernel interface index for `name`, or None."""
    try:
        return socket.if_nametoindex(name)
    except OSError:
        return None


def check_once(last_logged_state: dict) -> None:
    """One monitor iteration. Never raises — logs and returns on any error.

    `last_logged_state` carries small bits of cross-iteration state so we log
    transitions once rather than spamming every poll.
    """
    iface = vpn_interface()

    if not iface:
        # Tunnel is down (reconnecting / VPN off). Do NOT touch the bind: the
        # stale pin keeps qBittorrent failing closed, so nothing leaks. Log the
        # transition once.
        if last_logged_state.get("vpn_up") is not False:
            print("[vpn-bind] VPN tunnel down — leaving qBit bound (fails closed, no leak)")
            last_logged_state["vpn_up"] = False
        return

    vpn_name, vpn_ip = iface
    ifindex = _ifindex(vpn_name)

    if last_logged_state.get("vpn_up") is not True:
        print(f"[vpn-bind] VPN tunnel up, IP {vpn_ip} on {vpn_name} (if{ifindex})")
        last_logged_state["vpn_up"] = True

    try:
        c = client.qb()
        current = _current_bind(c)
        # Re-pin when the IP changed (key rotation) OR the interface index
        # changed (reconnect with the same IP — the socket is scoped to a dead
        # index and all outgoing UDP fails with ENODEV). On the first poll the
        # tracked index is unset, so we re-pin once to guarantee the socket is
        # fresh on the current index regardless of how qBit was last bound.
        ip_changed = current != vpn_ip
        idx_changed = last_logged_state.get("ifindex") != ifindex
        if ip_changed or idx_changed:
            apply_bind(c, vpn_ip)
            reason = "IP changed" if ip_changed else f"interface index changed -> if{ifindex}"
            print(f"[vpn-bind] re-pinned qBittorrent ({reason}): "
                  f"{current or '<unset>'} -> {vpn_ip} on {vpn_name} (if{ifindex})")
            last_logged_state["bind"] = vpn_ip
            last_logged_state["ifindex"] = ifindex
        elif last_logged_state.get("bind") != vpn_ip:
            # First time we observe a matching bind — note it once, quietly.
            print(f"[vpn-bind] qBittorrent already pinned to {vpn_ip} (if{ifindex})")
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
