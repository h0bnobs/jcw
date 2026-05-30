# Deploy notes

## jcw-vpn-bind.service — VPN-bind monitor

Keeps qBittorrent pinned to the current Mullvad tunnel IP. Mullvad assigns a
new tunnel IP on reconnect and on key rotation (~weekly); without this, the
bind goes stale and downloads silently stall on "downloading metadata".

The monitor re-pins via the qBittorrent WebUI API only — no qBittorrent restart
and no interruption to active downloads. If the tunnel is down it leaves the
stale bind in place, which makes qBittorrent fail closed (no IP leak).

### Install (on the host, as root)

```sh
cp /root/jcw/deploy/jcw-vpn-bind.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now jcw-vpn-bind.service
```

### Check it

```sh
systemctl status jcw-vpn-bind.service
journalctl -u jcw-vpn-bind.service -f
```

Assumes the app lives at `/root/jcw` with its venv at `/root/jcw/venv`. Adjust
`WorkingDirectory` and `ExecStart` in the unit if your paths differ.
