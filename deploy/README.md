# Deploy notes

## jcw.service — the web portal itself

Runs `jcw.py` (the Flask app on port 80). The `require-mount.conf` drop-in
holds it back until `/media/jellyfin` — the download disk, mounted via
`/etc/fstab` by UUID — is actually mounted, so it never starts writing to an
empty mountpoint after a reboot before the disk is ready.

### Install (on the host, as root)

```sh
cp /root/jcw/deploy/jcw.service /etc/systemd/system/
mkdir -p /etc/systemd/system/jcw.service.d
cp /root/jcw/deploy/jcw.service.d/require-mount.conf /etc/systemd/system/jcw.service.d/
systemctl daemon-reload
systemctl enable --now jcw.service
```

Needs `/media/jellyfin` (or wherever `config.json`'s `download_dir` points)
mounted and a `media-jellyfin.mount` unit for that path — see the host's
`/etc/fstab` and the `mele-host-infra` repo for the disk-mount notes.

## qbittorrent.service — the torrent client itself

Runs `qbittorrent-nox` headless as root, WebUI on port 9000 (see the main
README for WebUI setup). jcw's Flask app and the VPN-bind monitor both talk
to it over that WebUI API — nothing else here starts without it.

### Install (on the host, as root)

```sh
cp /root/jcw/deploy/qbittorrent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now qbittorrent.service
```

### Prerequisite: Mullvad

qBittorrent's outbound bind is pinned to the Mullvad tunnel interface — see
`is_vpn()` / `tunnel_is_stale()` in `src/qbt/download_torrent.py`. Install and
log in to the Mullvad daemon before starting qBittorrent, otherwise searches
will report "VPN is not active" (or `VPN_BYPASS=true` in `config.json` to
disable the check entirely — not recommended). Host-level Mullvad
install/login notes live outside this repo, in the `mele-host-infra` repo.

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
