# Home Media Server Commands

This guide targets the Ubuntu 22.04 LTS home server from `hosting.md`. It uses the 4 TB WD drive for movies, shows, and Immich uploads, while keeping Immich's PostgreSQL database on the server's internal SSD. Replace `example.com` with your domain. The commands that format the disk erase the selected disk; stop and verify the model, serial, and size before running them.

## 1. Check the Server and Install Base Tools

Before changes, check the operating system, storage, memory, and USB devices:

```bash
lsb_release -a
uname -a
free -h
df -h /
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS
lsusb
```

Install the basic packages and firewall:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl wget ca-certificates gnupg lsb-release parted e2fsprogs smartmontools nginx certbot python3-certbot-nginx ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo systemctl enable --now nginx
```

Check the result:

```bash
nginx -v
sudo systemctl status --no-pager nginx
sudo ufw status verbose
```

## 2. Format and Mount the 4 TB Drive

Plug in the WD Elements drive and identify it by its **model, serial, and approximately 3.6 TiB size**. Linux device names such as `/dev/sdb` can change, so use the current `lsblk` output each time. The example uses `/dev/sdX` and `/dev/sdX1` as placeholders; replace them with the exact device and partition you verify.

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS
```

Set the disk and partition only after identifying them. The confirmation below must match the selected disk path exactly. Do not use a partition that contains `/`, `/boot`, or another mounted filesystem.

```bash
DISK=/dev/sdX
PART=/dev/sdX1
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DISK"
read -r -p "Type ERASE $DISK only if this is the empty WD Elements drive: " CONFIRM
test "$CONFIRM" = "ERASE $DISK" || { echo "Stopped; disk was not formatted."; unset DISK PART CONFIRM; false; }
findmnt --source "$DISK" || true
lsblk -nrpo NAME,MOUNTPOINTS "$DISK"
if lsblk -nrpo MOUNTPOINT "$DISK" | grep -q '/'; then echo "A partition on $DISK is mounted; stop and unmount it first."; false; fi
```

If `findmnt` shows a mounted filesystem, unmount that exact drive in the file manager or with `sudo umount /dev/sdX1`, then repeat the identification and confirmation. Create one GPT partition and format it as ext4:

```bash
sudo parted --script "$DISK" mklabel gpt mkpart primary ext4 1MiB 100%
sudo partprobe "$DISK"
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DISK"
```

Confirm the partition name in the output, update `PART` if needed, then format it:

```bash
PART=/dev/sdX1
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$PART"
sudo mkfs.ext4 -L MEDIA "$PART"
sudo blkid "$PART"
```

Mount by filesystem UUID so the mount survives a reboot even if Linux assigns the drive another `/dev/sd*` name:

```bash
UUID=$(sudo blkid -s UUID -o value "$PART")
test -n "$UUID" || { echo "No filesystem UUID found; stop here."; false; }
sudo mkdir -p /srv/media
grep -q "UUID=$UUID " /etc/fstab || echo "UUID=$UUID /srv/media ext4 defaults,nofail,x-systemd.device-timeout=10 0 2" | sudo tee -a /etc/fstab
sudo findmnt --verify --verbose
sudo mount /srv/media
findmnt /srv/media
df -hT /srv/media
```

Create the shared media folders and permissions. The `media` group lets Jellyfin read the files while your login can rip and organize them.

```bash
sudo groupadd --force media
sudo usermod -aG media "$USER"
sudo mkdir -p /srv/media/{movies,shows,rips/movies,rips/shows,immich}
sudo chown -R "$USER":media /srv/media
sudo find /srv/media -type d -exec chmod 2775 {} +
sudo find /srv/media -type f -exec chmod 0664 {} +
ls -ld /srv/media /srv/media/{movies,shows,rips,immich}
df -h /srv/media
```

Log out and back in after adding your account to `media`. Verify the drive comes back after a reboot:

```bash
sudo reboot
```

After reconnecting:

```bash
findmnt /srv/media
df -hT /srv/media
touch /srv/media/.write-check && rm /srv/media/.write-check && echo "Drive is mounted and writable"
```

## 3. Install MakeMKV and HandBrake

Check that Ubuntu can see the Buffalo optical drive:

```bash
lsusb
lsblk -o NAME,TYPE,SIZE,MODEL,TRAN
```

If `/dev/sr0` is owned by the `cdrom` group and your user is not in that group, add your account and log out/in before ripping:

```bash
ls -l /dev/sr0
id -nG
sudo usermod -aG cdrom "$USER"
```

Install MakeMKV's Linux build dependencies. MakeMKV distributes the Linux source archives through its official download/forum pages, so download the current `makemkv-oss` and `makemkv-bin` `.tar.gz` files from [MakeMKV Downloads](https://www.makemkv.com/download/) into `~/Downloads` first.

```bash
sudo apt update
sudo apt install -y build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev
mkdir -p "$HOME/src"
find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-*.tar.gz' -printf '%f\n' | sort -V
```

Build and install the matching OSS and binary archives (the version numbers in their filenames should match):

```bash
OSS_ARCHIVE=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-oss-*.tar.gz' -printf '%f\n' | sort -V | tail -n 1)
BIN_ARCHIVE=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-bin-*.tar.gz' -printf '%f\n' | sort -V | tail -n 1)
test -n "$OSS_ARCHIVE" && test -n "$BIN_ARCHIVE" || { echo "Download both current MakeMKV archives first."; false; }
printf 'OSS: %s\nBIN: %s\n' "$OSS_ARCHIVE" "$BIN_ARCHIVE"
tar -xzf "$HOME/Downloads/$OSS_ARCHIVE" -C "$HOME/src"
tar -xzf "$HOME/Downloads/$BIN_ARCHIVE" -C "$HOME/src"
cd "$HOME/src/${OSS_ARCHIVE%.tar.gz}"
./configure
make -j"$(nproc)"
sudo make install
cd "$HOME/src/${BIN_ARCHIVE%.tar.gz}"
make
sudo make install
```

Check the CLI and optical drive:

```bash
makemkvcon --version
makemkvcon info disc:0
```

For Blu-ray use, get the current beta key from the official [MakeMKV beta-key forum thread](https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053). Do not paste a key copied from an old guide; beta keys expire. Add the key to your Linux user's MakeMKV settings without putting it in shell history:

```bash
mkdir -p "$HOME/.MakeMKV"
read -r -s -p "Paste the current MakeMKV beta key: " MAKEMKV_KEY
printf '\napp_Key = "%s"\n' "$MAKEMKV_KEY" >> "$HOME/.MakeMKV/settings.conf"
unset MAKEMKV_KEY
chmod 600 "$HOME/.MakeMKV/settings.conf"
makemkvcon info disc:0
```

Install HandBrake's official Flatpak release and use its CLI through Flatpak:

```bash
sudo apt install -y flatpak
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
sudo flatpak install -y flathub fr.handbrake.ghb
flatpak run --command=HandBrakeCLI fr.handbrake.ghb --version
flatpak run --command=HandBrakeCLI fr.handbrake.ghb --preset-list | grep -F 'Fast 1080p30'
```

## 4. Rip and Compress Discs Overnight

Insert one disc and inspect its titles before ripping. The `all` selector copies every title; review the output afterward because discs often contain trailers and extras. Keep movie and TV rips in separate folders so Jellyfin libraries stay organized.

```bash
makemkvcon info disc:0
DISC_DIR='/srv/media/rips/movies/Movie Name (year)'
mkdir -p "$DISC_DIR"
makemkvcon mkv disc:0 all "$DISC_DIR"
find "$DISC_DIR" -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
du -sh "$DISC_DIR"
```

For TV, use a path such as `/srv/media/rips/shows/Show Name/Season 01` and name each selected title according to the episode (for example `Show Name - S01E01.mkv`). For movies, rename the main title to `Movie Name (year).mkv`. Jellyfin uses these names to match episodes and movie metadata:

```bash
mv "$DISC_DIR/title00.mkv" "$DISC_DIR/Movie Name (year).mkv"
mkdir -p '/srv/media/rips/shows/Show Name/Season 01'
makemkvcon mkv disc:0 all '/srv/media/rips/shows/Show Name/Season 01'
mv '/srv/media/rips/shows/Show Name/Season 01/title00.mkv' '/srv/media/rips/shows/Show Name/Season 01/Show Name - S01E01.mkv'
find /srv/media/rips -type f -name '*.mkv' -printf '%p %s bytes\n' | sort
```

For each movie or episode title you want to keep, run the following command with its real input filename and corresponding output path. The `Fast 1080p30` preset produces an MP4/H.264 file with AAC stereo audio and caps output at 1080p/30 fps. RF 20 is a sensible quality/size starting point; raise it toward 22 for smaller files or lower it toward 18 for larger files. This is broad compatibility oriented, including iPhone and AirPlay clients. The rip remains untouched in `rips` if you want to re-encode later.

```bash
INPUT='/srv/media/rips/movies/Movie Name (year)/Movie Name (year).mkv'
OUTPUT='/srv/media/movies/Movie Title (year)/Movie Title (year).mp4'
test -r "$INPUT" || { echo "Input file not found: $INPUT"; false; }
test ! -e "$OUTPUT" || { echo "Output already exists: $OUTPUT"; false; }
mkdir -p "$(dirname "$OUTPUT")"
ls -lh "$INPUT"
flatpak run --command=HandBrakeCLI fr.handbrake.ghb -i "$INPUT" -o "$OUTPUT" --preset="Fast 1080p30" --format=av_mp4 --encoder=x264 --quality=20 --aencoder=av_aac --ab=160 --mixdown=stereo
ls -lh "$INPUT" "$OUTPUT"
```

After renaming selected movie and episode files to Jellyfin's usual title format, this script preserves their subfolders in the Movies and Shows libraries. It skips existing outputs, records command output in `/srv/media/encode.log`, and continues after an individual failure. Run once with `DRY_RUN=1` to see the planned files; change to `DRY_RUN=0` to encode.

```bash
DRY_RUN=1
set -o pipefail
while IFS= read -r -d '' INPUT; do
    RELATIVE=${INPUT#/srv/media/rips/}
    case "$INPUT" in
        /srv/media/rips/movies/*) OUTPUT="/srv/media/movies/${RELATIVE#movies/}"; OUTPUT="${OUTPUT%.mkv}.mp4" ;;
        /srv/media/rips/shows/*) OUTPUT="/srv/media/shows/${RELATIVE#shows/}"; OUTPUT="${OUTPUT%.mkv}.mp4" ;;
        *) continue ;;
    esac
    mkdir -p "$(dirname "$OUTPUT")"
    if [ -e "$OUTPUT" ]; then
        printf 'SKIP (already exists): %s\n' "$OUTPUT"
        continue
    fi
    printf 'WOULD ENCODE: %s -> %s\n' "$INPUT" "$OUTPUT"
    if [ "$DRY_RUN" = 0 ]; then
        flatpak run --command=HandBrakeCLI fr.handbrake.ghb -i "$INPUT" -o "$OUTPUT" --preset="Fast 1080p30" --format=av_mp4 --encoder=x264 --quality=20 --aencoder=av_aac --ab=160 --mixdown=stereo || printf 'FAILED: %s\n' "$INPUT"
        [ -f "$OUTPUT" ] && ls -lh "$INPUT" "$OUTPUT"
    fi
done < <(find /srv/media/rips/movies /srv/media/rips/shows -type f -name '*.mkv' -print0 2>/dev/null) 2>&1 | tee -a /srv/media/encode.log
```

After the dry run, start the real queue in `tmux` so it continues if SSH disconnects:

```bash
sudo apt install -y tmux
tmux new -s encode
```

Inside `tmux`, paste the queue script again after changing `DRY_RUN=1` to `DRY_RUN=0`. Detach with `Ctrl+B`, then `D`; reconnect with `tmux attach -t encode`. Check the queue and remaining space:

```bash
find /srv/media/rips -type f -name '*.mkv' -printf '%p\n' | sort
find /srv/media/movies -type f -name '*.mp4' -printf '%p %s bytes\n' | sort
find /srv/media/shows -type f -name '*.mp4' -printf '%p %s bytes\n' | sort
tail -n 50 /srv/media/encode.log
df -h /srv/media
```

## 5. Install Jellyfin

Install Jellyfin from the official Ubuntu repository setup script and verify its published checksum before running it:

```bash
cd /tmp
curl -fsSLO https://repo.jellyfin.org/install-debuntu.sh
curl -fsSLO https://repo.jellyfin.org/install-debuntu.sh.sha256sum
sha256sum -c install-debuntu.sh.sha256sum
sudo bash install-debuntu.sh
sudo apt install -y jellyfin
```

Add Jellyfin to the media group and restart it. Check that the service can read the movie folder:

```bash
sudo usermod -aG media jellyfin
sudo mkdir -p /etc/systemd/system/jellyfin.service.d
sudo tee /etc/systemd/system/jellyfin.service.d/media-drive.conf >/dev/null <<'EOF'
[Unit]
RequiresMountsFor=/srv/media
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now jellyfin
sudo systemctl restart jellyfin
sudo -u jellyfin test -r /srv/media/movies && echo "Jellyfin can read movies"
sudo systemctl status --no-pager jellyfin
curl -I http://127.0.0.1:8096
```

For first-time setup, run this SSH tunnel on your home computer (replace `SERVER_LAN_IP` and `agentbot` with your server's LAN address and Linux username), then open the two `localhost` URLs in that computer's browser:

```bash
ssh -L 8096:127.0.0.1:8096 -L 2283:127.0.0.1:2283 agentbot@SERVER_LAN_IP
```

Open `http://localhost:8096` for Jellyfin. Create your admin account, then create a Movies library at `/srv/media/movies` and a Shows library at `/srv/media/shows`. Create separate Jellyfin accounts for other household members; set each user's library and playback permissions in the dashboard. When finished, enable authentication for remote users and disable guest access.

## 6. Install Immich

Install Docker Engine and the Compose plugin from Docker's official Ubuntu repository:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/media-drive.conf >/dev/null <<'EOF'
[Unit]
RequiresMountsFor=/srv/media /var/lib/immich
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

Keep the database on the internal SSD and the photos/videos on the mounted 4 TB drive. Download the official Immich Compose and environment files, set their paths, and replace the sample database password with a unique letters-and-numbers password:

```bash
sudo mkdir -p /opt/immich /var/lib/immich/postgres /srv/media/immich
sudo chown -R "$USER":"$USER" /opt/immich
cd /opt/immich
curl -fL -o docker-compose.yml https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml
curl -fL -o .env https://github.com/immich-app/immich/releases/latest/download/example.env
sed -i 's|^UPLOAD_LOCATION=.*|UPLOAD_LOCATION=/srv/media/immich|' .env
sed -i 's|^DB_DATA_LOCATION=.*|DB_DATA_LOCATION=/var/lib/immich/postgres|' .env
sed -i 's|^DB_PASSWORD=.*|DB_PASSWORD=REPLACE_WITH_A_LONG_LETTERS_AND_NUMBERS_PASSWORD|' .env
grep -E '^(UPLOAD_LOCATION|DB_DATA_LOCATION|DB_PASSWORD|IMMICH_VERSION)=' .env
```

Edit the Compose file so its published web port is bound to localhost only. This keeps port `2283` private while Nginx and Tailscale provide the two access paths:

```bash
grep -n -A3 -B2 '2283:' docker-compose.yml
nano docker-compose.yml
```

In the `immich-server` `ports` list, change the mapping from `2283:2283` to `127.0.0.1:2283:2283`, then start Immich:

```bash
sudo docker compose config
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=50 immich-server
curl -I http://127.0.0.1:2283
df -hT /srv/media /var/lib/immich
```

Open `http://localhost:2283` in the browser while the SSH tunnel from the Jellyfin section is running. Create the administrator account before inviting anyone else. Add each friend/family member as their own Immich user, and leave public registration disabled. Install the Immich mobile app and use the HTTPS URL from the access option they will use below.

## 7. Private Remote Access with Tailscale

Install Tailscale on the server and sign it in to your tailnet:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale status
tailscale ip -4
```

Install the Tailscale app on your own phone, laptop, and TV device where supported, sign them into the same tailnet, and turn on MagicDNS in the Tailscale admin console. The application ports stay private; the Serve URLs below are the private paths to use.

To avoid exposing Jellyfin's direct port and still give its client a private HTTPS URL, use Tailscale Serve for Jellyfin. Immich is already bound to localhost, so Serve can proxy it too:

```bash
sudo tailscale serve --bg --https=8443 8096
sudo tailscale serve --bg --https=8444 2283
sudo ufw allow in on tailscale0 to any port 8443 proto tcp
sudo ufw allow in on tailscale0 to any port 8444 proto tcp
sudo tailscale serve status
```

Use the server's MagicDNS name with the private HTTPS ports, for example `https://media-server.your-tailnet.ts.net:8443` and `https://media-server.your-tailnet.ts.net:8444`. Tailscale Serve shares those services only with devices/users in your tailnet. Do not invite friends who do not want a VPN to this option; use the public HTTPS option below for them.

## 8. Public HTTPS Access for Friends and Family

This option lets people use regular Jellyfin and Immich apps without installing Tailscale. It uses the existing hosting pattern: DNS points to the router's public IP, the router forwards only TCP `80` and `443` to the server, and Nginx routes HTTPS to the private application ports.

Check the public IPv4 address seen on the internet and compare it with the WAN address shown in the Xfinity app:

```bash
curl -4 https://icanhazip.com
```

Create DNS `A` records such as `media.example.com` and `photos.example.com` pointing to your router's public IPv4 address. In the Xfinity app, forward TCP `80` and `443` to the home server. Do not forward `8096`, `2283`, `5432`, SSH, or Tailscale ports. If your public IP changes, set up a DNS updater with your DNS provider. If the address reported above differs from the Xfinity WAN address, your ISP may use CGNAT; a dynamic DNS updater will not solve that, and public access will need a public IP from the ISP or another publicly reachable relay. The Tailscale option works without router port forwarding.

Set the hostnames and create an Nginx site. Jellyfin requires websocket forwarding and streaming without response buffering; Immich needs websocket forwarding and a large request body limit for photo/video uploads.

```bash
MEDIA_DOMAIN=media.example.com
PHOTOS_DOMAIN=photos.example.com
sudo tee /etc/nginx/sites-available/media-server >/dev/null <<EOF
server {
    listen 80;
    server_name $MEDIA_DOMAIN;
    access_log off;
    location / {
        proxy_pass http://127.0.0.1:8096;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }
    location /socket {
        proxy_pass http://127.0.0.1:8096;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
server {
    listen 80;
    server_name $PHOTOS_DOMAIN;
    client_max_body_size 50G;
    client_body_timeout 600s;
    proxy_read_timeout 600s;
    location / {
        proxy_pass http://127.0.0.1:2283;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
sudo ln -sfn /etc/nginx/sites-available/media-server /etc/nginx/sites-enabled/media-server
sudo nginx -t
sudo systemctl reload nginx
```

After DNS has propagated and the server is reachable from the internet, request HTTPS certificates:

```bash
MEDIA_DOMAIN=media.example.com
PHOTOS_DOMAIN=photos.example.com
sudo certbot --nginx -d "$MEDIA_DOMAIN" -d "$PHOTOS_DOMAIN"
sudo certbot renew --dry-run
sudo nginx -t && sudo systemctl reload nginx
```

Check the services from a phone with Wi-Fi turned off (cellular data):

```bash
MEDIA_DOMAIN=media.example.com
PHOTOS_DOMAIN=photos.example.com
curl -I "https://$MEDIA_DOMAIN"
curl -I "https://$PHOTOS_DOMAIN"
sudo ufw status numbered
sudo ss -lntp
```

Set Jellyfin's **Known Proxies** to `127.0.0.1` in its Dashboard → Networking settings so it honors Nginx's forwarded client headers. Use the Jellyfin and Immich apps with `https://media.example.com` and `https://photos.example.com`. Create individual accounts and strong passwords; do not share the administrator login. Jellyfin's public web client is at the media hostname, and Immich's mobile app server URL is the photos hostname.

## 9. Jellyfin and Plex: Pros and Cons

| | Jellyfin | Plex |
|---|---|---|
| Cost and control | Free, open-source, self-hosted; no vendor account is needed for server playback. | Polished setup and user sharing tied to Plex accounts. Plex currently requires Plex Pass or Remote Watch Pass for remote playback of personal media. |
| Apps | Good browser, mobile, and TV clients; app availability and polish vary by device. | Broad, polished clients on many TVs and streaming devices; simpler for less technical family. |
| Remote access | You control the network path. Use Tailscale privately or your own HTTPS reverse proxy publicly. | Plex coordinates remote access, but it depends on Plex account services and its current subscription rules. |
| Maintenance | You manage updates, HTTPS, accounts, backups, and troubleshooting. | Easier account discovery/sharing, but depends more on Plex's service and pricing decisions. |
| Transcoding | Supports hardware acceleration when the server hardware/driver supports it; compatible H.264 files can Direct Play with little server load. | Also supports transcoding; some advanced functionality and remote playback depend on subscription. |

For this setup, Jellyfin avoids a recurring remote-playback subscription and works with either Tailscale or your own public HTTPS endpoint. Plex may be easier for relatives who already use its apps and account sharing. [Plex remote playback rules](https://support.plex.tv/articles/200289506-remote-access/) and [Plex's 2025 remote-playback change](https://www.plex.tv/blog/important-2025-plex-updates/) describe its current remote access model. Jellyfin's supported playback modes and hardware acceleration are in its [transcoding documentation](https://jellyfin.org/docs/general/post-install/transcoding/).

## 10. Checks and Maintenance

Check the mount, disk space, Jellyfin, Immich containers, Nginx, and HTTPS renewal:

```bash
findmnt /srv/media
df -hT /srv/media /var/lib/immich
sudo systemctl status --no-pager jellyfin nginx certbot.timer
sudo docker compose -f /opt/immich/docker-compose.yml ps
sudo docker compose -f /opt/immich/docker-compose.yml logs --tail=50
sudo nginx -t
sudo certbot renew --dry-run
```

Check drive health and recent kernel disk errors:

```bash
sudo smartctl -a -d sat /dev/sdX
sudo journalctl -k --since today | grep -Ei 'usb|uas|reset|I/O error|ext4'
```

Make a second backup of irreplaceable photos and the Immich database on another disk or backup service. The 4 TB drive is storage, not a backup. Immich's built-in database dump does not back up the original media files; back up both `/srv/media/immich` and `/var/lib/immich`.

Useful service logs:

```bash
sudo journalctl -u jellyfin -f
sudo journalctl -u nginx -f
sudo docker compose -f /opt/immich/docker-compose.yml logs -f
```

## Official References

- [Ubuntu disk formatting](https://help.ubuntu.com/stable/ubuntu-help/disk-format.html.en)
- [Western Digital filesystem guidance](https://support-en.wd.com/app/answers/detailweb/a_id/20821)
- [MakeMKV downloads](https://www.makemkv.com/download/) and [current beta key thread](https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053)
- [HandBrake official presets](https://handbrake.fr/docs/en/latest/technical/official-presets.html)
- [Jellyfin Ubuntu/Linux installation](https://jellyfin.org/docs/general/installation/linux/) and [Nginx reverse proxy](https://jellyfin.org/docs/general/networking/nginx/)
- [Immich quick start](https://docs.immich.app/overview/quick-start/) and [storage requirements](https://docs.immich.app/install/requirements/)
- [Tailscale Linux install](https://tailscale.com/docs/install/linux) and [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
