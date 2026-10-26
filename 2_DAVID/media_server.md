# Home Media Server Commands

This guide targets the Ubuntu 22.04 LTS home server from `hosting.md`. It uses the 4 TB WD drive for movies, shows, and Immich uploads, while keeping Immich's PostgreSQL database on the server's internal SSD. Replace `example.com` with your domain. The commands that format the disk erase the selected disk; stop and verify the model, serial, and size before running them.

## 1. Check the Server and Install Base Tools

Before changes, check the operating system, storage, memory, and USB devices:

```bash
lsb_release -a # Show the installed Ubuntu release.
uname -a # Show the kernel and machine architecture.
free -h # Show memory available to the server.
df -h / # Show free space on the internal system disk.
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS # List disks and identify the external drive.
lsusb # List USB devices, including the Buffalo optical drive.
```

> Example release output (the kernel version and hostname will differ):
>
> ```text
> Distributor ID: Ubuntu
> Description:    Ubuntu 22.04.5 LTS
> Release:        22.04
> ```

Install the basic packages and firewall:

```bash
sudo apt update # Refresh Ubuntu's package index.
sudo apt upgrade -y # Install available security and package updates.
sudo apt install -y curl wget ca-certificates gnupg lsb-release parted e2fsprogs smartmontools nginx certbot python3-certbot-nginx ufw # Install the tools used below.
sudo ufw default deny incoming # Block unsolicited incoming connections by default.
sudo ufw default allow outgoing # Allow the server to make outbound connections.
sudo ufw allow OpenSSH # Keep SSH reachable so remote administration continues.
sudo ufw allow 80/tcp # Allow HTTP for Let's Encrypt validation and redirects.
sudo ufw allow 443/tcp # Allow HTTPS for the public media services.
sudo ufw enable # Turn on the firewall after allowing SSH and web traffic.
sudo systemctl enable --now nginx # Start Nginx now and after future reboots.
```

> Example firewall output includes `Status: active` and rules for `OpenSSH`, `80/tcp`, and `443/tcp`.

Check the result:

```bash
nginx -v # Print the installed Nginx version.
sudo systemctl status --no-pager nginx # Confirm the web server is running.
sudo ufw status verbose # Confirm the firewall is active with the expected rules.
```

> Example checks: `nginx version: nginx/1.18.0 (Ubuntu)` and `Active: active (running)`. Package versions vary.

## 2. Format and Mount the 4 TB Drive

Plug in the WD Elements drive and identify it by its **model, serial, and approximately 3.6 TiB size**. Linux device names such as `/dev/sdb` can change, so use the current `lsblk` output each time. The example uses `/dev/sdX` and `/dev/sdX1` as placeholders; replace them with the exact device and partition you verify.

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS # Compare model, serial, and size before choosing a device.
```

> Example only; use the name that your own output shows:
>
> ```text
> NAME   SIZE MODEL            SERIAL  TRAN FSTYPE MOUNTPOINTS
> sda    3.6T WD Elements 25A3 WX...   usb
> └─sda1 3.6T                         ntfs   /media/david/Elements
> ```

Set the disk and partition only after identifying them. The confirmation below must match the selected disk path exactly. Do not use a partition that contains `/`, `/boot`, or another mounted filesystem.

```bash
DISK=/dev/sdX # Replace this placeholder with the verified external disk name.
PART=/dev/sdX1 # Replace this with the partition name shown by lsblk.
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DISK" # Recheck the selected device details.
read -r -p "Type ERASE $DISK only if this is the empty WD Elements drive: " CONFIRM # Require deliberate confirmation before partitioning.
test "$CONFIRM" = "ERASE $DISK" || { echo "Stopped; disk was not formatted."; unset DISK PART CONFIRM; false; } # Stop this block if the confirmation does not match.
findmnt --source "$DISK" || true # Show whether the selected disk is currently mounted.
lsblk -nrpo NAME,MOUNTPOINTS "$DISK" # Check child partitions for mount points.
if lsblk -nrpo MOUNTPOINT "$DISK" | grep -q '/'; then echo "A partition on $DISK is mounted; stop and unmount it first."; false; fi
```

If `findmnt` shows a mounted filesystem, unmount that exact drive in the file manager or with `sudo umount /dev/sdX1`, then repeat the identification and confirmation. Create one GPT partition and format it as ext4:

```bash
sudo parted --script "$DISK" mklabel gpt mkpart primary ext4 1MiB 100% # Erase the selected disk's partition table and create one partition.
sudo partprobe "$DISK" # Ask Linux to reread the partition table.
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DISK" # Verify the new partition name before formatting.
```

> Example after partitioning: `sda` is the 3.6 TiB disk and `sda1` is its new partition. Confirm this matches your selected drive before continuing.

Confirm the partition name in the output, update `PART` if needed, then format it:

```bash
PART=/dev/sdX1 # Replace this placeholder with the new partition shown by lsblk.
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$PART" # Final check that this is the external partition.
sudo mkfs.ext4 -L MEDIA "$PART" # Create the Linux ext4 filesystem labeled MEDIA.
sudo blkid "$PART" # Read its UUID for persistent mounting.
```

> Example `blkid` output includes `TYPE="ext4"` and a `UUID="..."` value.

Mount by filesystem UUID so the mount survives a reboot even if Linux assigns the drive another `/dev/sd*` name:

```bash
UUID=$(sudo blkid -s UUID -o value "$PART") # Save the filesystem's unique ID in this shell.
test -n "$UUID" || { echo "No filesystem UUID found; stop here."; false; } # Check that the UUID lookup succeeded.
sudo mkdir -p /srv/media # Create the permanent mount directory.
grep -q "UUID=$UUID " /etc/fstab || echo "UUID=$UUID /srv/media ext4 defaults,nofail,x-systemd.device-timeout=10 0 2" | sudo tee -a /etc/fstab # Add one fstab entry if it is not already present.
sudo findmnt --verify --verbose # Check that the fstab entry parses correctly.
sudo mount /srv/media # Mount the drive at /srv/media.
findmnt /srv/media # Show the mounted filesystem and source device.
df -hT /srv/media # Show filesystem type and available capacity.
```

> Example success: `findmnt` reports `FSTYPE ext4`; `df` reports about `3.6T` total for the 4 TB drive.

Create the shared media folders and permissions. The `media` group lets Jellyfin read the files while your login can rip and organize them.

```bash
sudo groupadd --force media # Create the shared media group if needed.
sudo usermod -aG media "$USER" # Let your login manage media files.
sudo mkdir -p /srv/media/{movies,shows,rips/movies,rips/shows,immich} # Create the movie, show, rip, and Immich folders.
sudo chown -R "$USER":media /srv/media # Assign files to your login and shared group.
sudo find /srv/media -type d -exec chmod 2775 {} + # Give folders group write access and inherit the media group.
sudo find /srv/media -type f -exec chmod 0664 {} + # Give existing files group read/write access.
ls -ld /srv/media /srv/media/{movies,shows,rips,immich} # Show ownership and permissions.
df -h /srv/media # Confirm the expected free space remains.
```

> Example folder permissions start with `drwxrwsr-x` and show your login with group `media`.

Log out and back in after adding your account to `media`. Verify the drive comes back after a reboot:

```bash
sudo reboot # Restart so the external drive mounts and the new group membership applies.
```

After reconnecting:

```bash
findmnt /srv/media # Confirm the UUID-based mount returned after reboot.
df -hT /srv/media # Check filesystem type and free space after reboot.
touch /srv/media/.write-check && rm /srv/media/.write-check && echo "Drive is mounted and writable" # Create and remove a temporary file to verify write access.
```

> Example confirmation: `Drive is mounted and writable`.

## 3. Install MakeMKV and HandBrake

Check that Ubuntu can see the Buffalo optical drive:

```bash
lsusb # Confirm the Buffalo drive appears on the USB bus.
lsblk -o NAME,TYPE,SIZE,MODEL,TRAN # Show Linux's block-device name for the optical drive.
```

If `/dev/sr0` is owned by the `cdrom` group and your user is not in that group, add your account and log out/in before ripping:

```bash
ls -l /dev/sr0 # Show the optical device's owner and group.
id -nG # Show groups your current login belongs to.
sudo usermod -aG cdrom "$USER" # Allow your login to read optical discs after you sign in again.
```

Install MakeMKV's Linux build dependencies. MakeMKV distributes the Linux source archives through its official download/forum pages, so download the current `makemkv-oss` and `makemkv-bin` `.tar.gz` files from [MakeMKV Downloads](https://www.makemkv.com/download/) into `~/Downloads` first.

```bash
sudo apt update # Refresh package metadata before installing MakeMKV build tools.
sudo apt install -y build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev # Install compilers and MakeMKV dependencies.
mkdir -p "$HOME/src" # Create a source-build folder in your home directory.
find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-*.tar.gz' -printf '%f\n' | sort -V # List the MakeMKV source archives you downloaded.
```

Build and install the matching OSS and binary archives (the version numbers in their filenames should match):

```bash
OSS_ARCHIVE=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-oss-*.tar.gz' -printf '%f\n' | sort -V | tail -n 1) # Find the newest MakeMKV open-source archive.
BIN_ARCHIVE=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-bin-*.tar.gz' -printf '%f\n' | sort -V | tail -n 1) # Find the matching binary archive.
test -n "$OSS_ARCHIVE" && test -n "$BIN_ARCHIVE" || { echo "Download both current MakeMKV archives first."; false; } # Stop if either archive is missing.
printf 'OSS: %s\nBIN: %s\n' "$OSS_ARCHIVE" "$BIN_ARCHIVE" # Print the selected versions so you can compare them.
tar -xzf "$HOME/Downloads/$OSS_ARCHIVE" -C "$HOME/src" # Extract the open-source archive.
tar -xzf "$HOME/Downloads/$BIN_ARCHIVE" -C "$HOME/src" # Extract the binary archive.
cd "$HOME/src/${OSS_ARCHIVE%.tar.gz}" # Enter the open-source source directory.
./configure # Check dependencies and prepare the MakeMKV build.
make -j"$(nproc)" # Compile using the server's available CPU cores.
sudo make install # Install the open-source MakeMKV components.
cd "$HOME/src/${BIN_ARCHIVE%.tar.gz}" # Enter the binary source directory.
make # Prepare the binary component for installation.
sudo make install # Install the MakeMKV binary component.
```

> Example archive listing includes a matching pair such as `makemkv-oss-1.18.4.tar.gz` and `makemkv-bin-1.18.4.tar.gz`; versions change.

Check the CLI and optical drive:

```bash
makemkvcon --version # Print the installed MakeMKV version.
makemkvcon info disc:0 # Inspect the disc in the first optical drive.
```

> Example disc feedback includes the MakeMKV version and a list of title numbers, durations, and sizes. No disc or a drive-access problem produces an error instead.

For Blu-ray use, get the current beta key from the official [MakeMKV beta-key forum thread](https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053). Do not paste a key copied from an old guide; beta keys expire. Add the key to your Linux user's MakeMKV settings without putting it in shell history:

```bash
mkdir -p "$HOME/.MakeMKV" # Create MakeMKV's per-user settings directory.
read -r -s -p "Paste the current MakeMKV beta key: " MAKEMKV_KEY # Read the key without displaying it in the terminal.
printf '\napp_Key = "%s"\n' "$MAKEMKV_KEY" >> "$HOME/.MakeMKV/settings.conf" # Save the key using MakeMKV's Linux setting name.
unset MAKEMKV_KEY # Remove the key from the current shell environment.
chmod 600 "$HOME/.MakeMKV/settings.conf" # Restrict the key file to your user account.
makemkvcon info disc:0 # Check that MakeMKV can read the disc with the key installed.
```

Install HandBrake's official Flatpak release and use its CLI through Flatpak:

```bash
sudo apt install -y flatpak # Install the Flatpak application manager.
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo # Add Flathub as an application source.
sudo flatpak install -y flathub fr.handbrake.ghb # Install HandBrake from its official Flathub release.
flatpak run --command=HandBrakeCLI fr.handbrake.ghb --version # Print the installed HandBrake CLI version.
flatpak run --command=HandBrakeCLI fr.handbrake.ghb --preset-list | grep -F 'Fast 1080p30' # Confirm the requested preset is available.
```

> Example output includes a HandBrakeCLI version line and `Fast 1080p30` in the preset list.

## 4. Rip and Compress Discs Overnight

Insert one disc and inspect its titles before ripping. The `all` selector copies every title; review the output afterward because discs often contain trailers and extras. Keep movie and TV rips in separate folders so Jellyfin libraries stay organized.

```bash
makemkvcon info disc:0 # List titles on the disc before selecting what to keep.
DISC_DIR='/srv/media/rips/movies/Movie Name (year)' # Set the destination folder for this movie's raw rip.
mkdir -p "$DISC_DIR" # Create the destination folder if needed.
makemkvcon mkv disc:0 all "$DISC_DIR" # Rip every disc title into the destination folder.
find "$DISC_DIR" -maxdepth 1 -type f -printf '%f %s bytes\n' | sort # List ripped files and their byte sizes.
du -sh "$DISC_DIR" # Show the total space used by the rip.
```

> Example feedback: MakeMKV lists title IDs and durations; the final checks show filenames and a total such as `34G`.

For TV, use a path such as `/srv/media/rips/shows/Show Name/Season 01` and name each selected title according to the episode (for example `Show Name - S01E01.mkv`). For movies, rename the main title to `Movie Name (year).mkv`. Jellyfin uses these names to match episodes and movie metadata:

```bash
mv "$DISC_DIR/title00.mkv" "$DISC_DIR/Movie Name (year).mkv" # Rename the selected movie title for Jellyfin.
mkdir -p '/srv/media/rips/shows/Show Name/Season 01' # Create a season folder for a TV rip.
makemkvcon mkv disc:0 all '/srv/media/rips/shows/Show Name/Season 01' # Rip TV disc titles into that season folder.
mv '/srv/media/rips/shows/Show Name/Season 01/title00.mkv' '/srv/media/rips/shows/Show Name/Season 01/Show Name - S01E01.mkv' # Name the chosen title as an episode.
find /srv/media/rips -type f -name '*.mkv' -printf '%p %s bytes\n' | sort # Review all rip filenames and sizes.
```

For each movie or episode title you want to keep, run the following command with its real input filename and corresponding output path. The `Fast 1080p30` preset produces an MP4/H.264 file with AAC stereo audio and caps output at 1080p/30 fps. RF 20 is a sensible quality/size starting point; raise it toward 22 for smaller files or lower it toward 18 for larger files. This is broad compatibility oriented, including iPhone and AirPlay clients. The rip remains untouched in `rips` if you want to re-encode later.

```bash
INPUT='/srv/media/rips/movies/Movie Name (year)/Movie Name (year).mkv' # Set the raw rip path.
OUTPUT='/srv/media/movies/Movie Title (year)/Movie Title (year).mp4' # Set the compressed library path.
test -r "$INPUT" || { echo "Input file not found: $INPUT"; false; } # Stop if the source file cannot be read.
test ! -e "$OUTPUT" || { echo "Output already exists: $OUTPUT"; false; } # Prevent overwriting an existing encode.
mkdir -p "$(dirname "$OUTPUT")" # Create the output movie folder.
ls -lh "$INPUT" # Record the original file size before encoding.
flatpak run --command=HandBrakeCLI fr.handbrake.ghb -i "$INPUT" -o "$OUTPUT" --preset="Fast 1080p30" --format=av_mp4 --encoder=x264 --quality=20 --aencoder=av_aac --ab=160 --mixdown=stereo # Encode a compatible 1080p H.264/AAC MP4.
ls -lh "$INPUT" "$OUTPUT" # Compare the raw and compressed file sizes.
```

> Example feedback: `ls -lh` might show a `22G` MKV before encoding and a `3.8G` MP4 afterward; actual sizes depend on the disc and content.

After renaming selected movie and episode files to Jellyfin's usual title format, this script preserves their subfolders in the Movies and Shows libraries. It skips existing outputs, records command output in `/srv/media/encode.log`, and continues after an individual failure. Run once with `DRY_RUN=1` to see the planned files; change to `DRY_RUN=0` to encode.

```bash
DRY_RUN=1 # Keep this at 1 to list work without encoding; use 0 to run the queue.
set -o pipefail # Preserve pipeline failures so the log command does not hide them.
while IFS= read -r -d '' INPUT; do # Process each null-delimited source filename safely, including spaces.
    RELATIVE=${INPUT#/srv/media/rips/} # Make a path relative to the rip root.
    case "$INPUT" in # Choose the matching output library based on the source folder.
        /srv/media/rips/movies/*) OUTPUT="/srv/media/movies/${RELATIVE#movies/}"; OUTPUT="${OUTPUT%.mkv}.mp4" ;; # Preserve the path under the Movies library and use MP4.
        /srv/media/rips/shows/*) OUTPUT="/srv/media/shows/${RELATIVE#shows/}"; OUTPUT="${OUTPUT%.mkv}.mp4" ;; # Preserve the path under the Shows library and use MP4.
        *) continue ;; # Ignore files outside the movie and show folders.
    esac # Finish choosing the output path.
    mkdir -p "$(dirname "$OUTPUT")" # Ensure the matching library folder exists.
    if [ -e "$OUTPUT" ]; then # Check whether this file was already encoded.
        printf 'SKIP (already exists): %s\n' "$OUTPUT" # Report files left unchanged.
        continue # Do not replace an existing encode.
    fi # Continue with files that do not already have an output.
    printf 'WOULD ENCODE: %s -> %s\n' "$INPUT" "$OUTPUT" # Show each planned input and output path.
    if [ "$DRY_RUN" = 0 ]; then # Only start the encoder when dry-run mode is disabled.
        flatpak run --command=HandBrakeCLI fr.handbrake.ghb -i "$INPUT" -o "$OUTPUT" --preset="Fast 1080p30" --format=av_mp4 --encoder=x264 --quality=20 --aencoder=av_aac --ab=160 --mixdown=stereo || printf 'FAILED: %s\n' "$INPUT" # Encode this file or report its failure and continue.
        [ -f "$OUTPUT" ] && ls -lh "$INPUT" "$OUTPUT" # Show before-and-after sizes when an output exists.
    fi # Finish handling this source file.
done < <(find /srv/media/rips/movies /srv/media/rips/shows -type f -name '*.mkv' -print0 2>/dev/null) 2>&1 | tee -a /srv/media/encode.log # Feed movie/show MKVs to the queue and append output to its log.
```

> Example dry-run output: `WOULD ENCODE: /srv/media/rips/movies/...mkv -> /srv/media/movies/...mp4`. Existing outputs show `SKIP (already exists)`.

After the dry run, start the real queue in `tmux` so it continues if SSH disconnects:

```bash
sudo apt install -y tmux # Install a terminal session manager for long jobs.
tmux new -s encode # Start a named session that keeps running after SSH disconnects.
```

Inside `tmux`, paste the queue script again after changing `DRY_RUN=1` to `DRY_RUN=0`. Detach with `Ctrl+B`, then `D`; reconnect with `tmux attach -t encode`. Check the queue and remaining space:

```bash
find /srv/media/rips -type f -name '*.mkv' -printf '%p\n' | sort # List source rips still available for encoding.
find /srv/media/movies -type f -name '*.mp4' -printf '%p %s bytes\n' | sort # List encoded movies and sizes.
find /srv/media/shows -type f -name '*.mp4' -printf '%p %s bytes\n' | sort # List encoded episodes and sizes.
tail -n 50 /srv/media/encode.log # Review recent encoder output and errors.
df -h /srv/media # Check remaining space on the external drive.
```

> Example queue feedback: the log ends with HandBrake's `Muxing: this may take awhile...` or completed output; `df` shows used and available disk space.

## 5. Install Jellyfin

Install Jellyfin from the official Ubuntu repository setup script and verify its published checksum before running it:

```bash
cd /tmp # Use a temporary folder for the repository setup files.
curl -fsSLO https://repo.jellyfin.org/install-debuntu.sh # Download the official Jellyfin setup script.
curl -fsSLO https://repo.jellyfin.org/install-debuntu.sh.sha256sum # Download its published checksum.
sha256sum -c install-debuntu.sh.sha256sum # Verify the downloaded script before running it.
sudo bash install-debuntu.sh # Configure Jellyfin's official Ubuntu package source.
sudo apt install -y jellyfin # Install Jellyfin from that package source.
```

> Example checksum feedback: `install-debuntu.sh: OK`; package installation ends with a successful setup message.

Add Jellyfin to the media group and restart it. Check that the service can read the movie folder:

```bash
sudo usermod -aG media jellyfin # Give the Jellyfin service account read access through the media group.
sudo mkdir -p /etc/systemd/system/jellyfin.service.d # Create a systemd override folder.
sudo tee /etc/systemd/system/jellyfin.service.d/media-drive.conf >/dev/null <<'EOF' # Require the external media mount before Jellyfin starts.
[Unit]
RequiresMountsFor=/srv/media
EOF
sudo systemctl daemon-reload # Load the new systemd override.
sudo systemctl enable --now jellyfin # Enable Jellyfin at boot and start it now.
sudo systemctl restart jellyfin # Restart so it uses the new group and mount requirement.
sudo -u jellyfin test -r /srv/media/movies && echo "Jellyfin can read movies" # Verify the service account can read the library.
sudo systemctl status --no-pager jellyfin # Show service health and recent status.
curl -I http://127.0.0.1:8096 # Check that Jellyfin responds on its local web port.
```

> Example success: `Jellyfin can read movies`, `Active: active (running)`, and an HTTP `200` or `302` response.

For first-time setup, run this SSH tunnel on your home computer (replace `SERVER_LAN_IP` and `agentbot` with your server's LAN address and Linux username), then open the two `localhost` URLs in that computer's browser:

```bash
ssh -L 8096:127.0.0.1:8096 -L 2283:127.0.0.1:2283 agentbot@SERVER_LAN_IP # Forward the local Jellyfin and Immich browser ports over SSH.
```

Open `http://localhost:8096` for Jellyfin. Create your admin account, then create a Movies library at `/srv/media/movies` and a Shows library at `/srv/media/shows`. Create separate Jellyfin accounts for other household members; set each user's library and playback permissions in the dashboard. When finished, enable authentication for remote users and disable guest access.

## 6. Install Immich

Install Docker Engine and the Compose plugin from Docker's official Ubuntu repository:

```bash
sudo install -m 0755 -d /etc/apt/keyrings # Create the trusted repository key folder.
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc # Download Docker's signing key.
sudo chmod a+r /etc/apt/keyrings/docker.asc # Allow apt to read the signing key.
. /etc/os-release # Load the Ubuntu release codename for the repository entry.
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null # Add Docker's official Ubuntu package source.
sudo apt update # Refresh package metadata with Docker's repository.
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin # Install Docker Engine and Compose.
sudo mkdir -p /etc/systemd/system/docker.service.d # Create a systemd override folder for Docker.
sudo tee /etc/systemd/system/docker.service.d/media-drive.conf >/dev/null <<'EOF' # Make Docker wait for the SSD and media mount paths.
[Unit]
RequiresMountsFor=/srv/media /var/lib/immich
EOF
sudo systemctl daemon-reload # Load the Docker mount override.
sudo systemctl restart docker # Restart Docker with the new mount requirement.
sudo systemctl enable --now docker # Enable Docker at boot and start it now.
sudo docker version # Show the installed Docker client and server versions.
sudo docker compose version # Confirm the Compose plugin is available.
```

> Example checks show `Docker version ...` and `Docker Compose version v...` without a daemon connection error.

Keep the database on the internal SSD and the photos/videos on the mounted 4 TB drive. Download the official Immich Compose and environment files, set their paths, and replace the sample database password with a unique letters-and-numbers password:

```bash
sudo mkdir -p /opt/immich /var/lib/immich/postgres /srv/media/immich # Create compose, SSD database, and external upload folders.
sudo chown -R "$USER":"$USER" /opt/immich # Let your login maintain the Compose files.
cd /opt/immich # Enter the Immich configuration folder.
curl -fL -o docker-compose.yml https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml # Download Immich's official Compose file.
curl -fL -o .env https://github.com/immich-app/immich/releases/latest/download/example.env # Download its matching environment template.
sed -i 's|^UPLOAD_LOCATION=.*|UPLOAD_LOCATION=/srv/media/immich|' .env # Store uploaded photos and videos on the external drive.
sed -i 's|^DB_DATA_LOCATION=.*|DB_DATA_LOCATION=/var/lib/immich/postgres|' .env # Keep the database files on the internal SSD.
sed -i 's|^DB_PASSWORD=.*|DB_PASSWORD=REPLACE_WITH_A_LONG_LETTERS_AND_NUMBERS_PASSWORD|' .env # Set the database password placeholder to replace before startup.
grep -E '^(UPLOAD_LOCATION|DB_DATA_LOCATION|DB_PASSWORD|IMMICH_VERSION)=' .env # Review configured paths, version, and password before launch.
```

Edit the Compose file so its published web port is bound to localhost only. This keeps port `2283` private while Nginx and Tailscale provide the two access paths:

```bash
grep -n -A3 -B2 '2283:' docker-compose.yml # Locate Immich's published web-port mapping.
nano docker-compose.yml # Edit the mapping to bind only to localhost.
```

In the `immich-server` `ports` list, change the mapping from `2283:2283` to `127.0.0.1:2283:2283`, then start Immich:

```bash
sudo docker compose config # Validate the Compose configuration and resolved paths.
sudo docker compose up -d # Download required images and start Immich in the background.
sudo docker compose ps # Show container states and published ports.
sudo docker compose logs --tail=50 immich-server # Review recent Immich server startup output.
curl -I http://127.0.0.1:2283 # Confirm the local Immich web service responds.
df -hT /srv/media /var/lib/immich # Verify external uploads and internal database storage mounts.
```

> Example success: `docker compose ps` shows the Immich containers as `Up`, and `curl` returns an HTTP response such as `200` or `302`.

Open `http://localhost:2283` in the browser while the SSH tunnel from the Jellyfin section is running. Create the administrator account before inviting anyone else. Add each friend/family member as their own Immich user, and leave public registration disabled. Install the Immich mobile app and use the HTTPS URL from the access option they will use below.

## 7. Private Remote Access with Tailscale

Install Tailscale on the server and sign it in to your tailnet:

```bash
curl -fsSL https://tailscale.com/install.sh | sh # Install the official Tailscale package for this Linux system.
sudo tailscale up # Authenticate this server to your tailnet.
tailscale status # Show connected devices and their current connectivity.
tailscale ip -4 # Print this server's private tailnet IPv4 address.
```

> Example output: `tailscale status` lists this server and signed-in devices; `tailscale ip -4` prints an address in Tailscale's private range.

Install the Tailscale app on your own phone, laptop, and TV device where supported, sign them into the same tailnet, and turn on MagicDNS in the Tailscale admin console. The application ports stay private; the Serve URLs below are the private paths to use.

To avoid exposing Jellyfin's direct port and still give its client a private HTTPS URL, use Tailscale Serve for Jellyfin. Immich is already bound to localhost, so Serve can proxy it too:

```bash
sudo tailscale serve --bg --https=8443 8096 # Publish Jellyfin over private tailnet HTTPS on port 8443.
sudo tailscale serve --bg --https=8444 2283 # Publish Immich over private tailnet HTTPS on port 8444.
sudo ufw allow in on tailscale0 to any port 8443 proto tcp # Allow the Jellyfin Serve port only on Tailscale's interface.
sudo ufw allow in on tailscale0 to any port 8444 proto tcp # Allow the Immich Serve port only on Tailscale's interface.
sudo tailscale serve status # Display the active private HTTPS proxy rules.
```

> Example status shows `https://...ts.net:8443` forwarding to `http://127.0.0.1:8096` and port `8444` forwarding to Immich.

Use the server's MagicDNS name with the private HTTPS ports, for example `https://media-server.your-tailnet.ts.net:8443` and `https://media-server.your-tailnet.ts.net:8444`. Tailscale Serve shares those services only with devices/users in your tailnet. Do not invite friends who do not want a VPN to this option; use the public HTTPS option below for them.

## 8. Public HTTPS Access for Friends and Family

This option lets people use regular Jellyfin and Immich apps without installing Tailscale. It uses the existing hosting pattern: DNS points to the router's public IP, the router forwards only TCP `80` and `443` to the server, and Nginx routes HTTPS to the private application ports.

Check the public IPv4 address seen on the internet and compare it with the WAN address shown in the Xfinity app:

```bash
curl -4 https://icanhazip.com # Print the public IPv4 address currently seen by internet services.
```

> Example output is a single public IPv4 address such as `203.0.113.10`; the address shown here is illustrative.

Create DNS `A` records such as `media.example.com` and `photos.example.com` pointing to your router's public IPv4 address. In the Xfinity app, forward TCP `80` and `443` to the home server. Do not forward `8096`, `2283`, `5432`, SSH, or Tailscale ports. If your public IP changes, set up a DNS updater with your DNS provider. If the address reported above differs from the Xfinity WAN address, your ISP may use CGNAT; a dynamic DNS updater will not solve that, and public access will need a public IP from the ISP or another publicly reachable relay. The Tailscale option works without router port forwarding.

Set the hostnames and create an Nginx site. Jellyfin requires websocket forwarding and streaming without response buffering; Immich needs websocket forwarding and a large request body limit for photo/video uploads.

```bash
MEDIA_DOMAIN=media.example.com # Set the Jellyfin hostname; replace it with your domain.
PHOTOS_DOMAIN=photos.example.com # Set the Immich hostname; replace it with your domain.
sudo tee /etc/nginx/sites-available/media-server >/dev/null <<EOF # Write Nginx reverse-proxy rules for both hostnames.
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
sudo ln -sfn /etc/nginx/sites-available/media-server /etc/nginx/sites-enabled/media-server # Enable this Nginx site configuration.
sudo nginx -t # Check Nginx configuration syntax before reloading.
sudo systemctl reload nginx # Apply the validated site configuration.
```

> Example validation output: `syntax is ok` followed by `test is successful`.

After DNS has propagated and the server is reachable from the internet, request HTTPS certificates:

```bash
MEDIA_DOMAIN=media.example.com # Set the Jellyfin domain for certificate issuance.
PHOTOS_DOMAIN=photos.example.com # Set the Immich domain for certificate issuance.
sudo certbot --nginx -d "$MEDIA_DOMAIN" -d "$PHOTOS_DOMAIN" # Obtain certificates and configure HTTPS in Nginx.
sudo certbot renew --dry-run # Verify automatic certificate renewal can succeed.
sudo nginx -t && sudo systemctl reload nginx # Validate and apply Certbot's Nginx changes.
```

> Example success: Certbot reports `Congratulations!` and the dry run reports that all simulated renewals succeeded.

Check the services from a phone with Wi-Fi turned off (cellular data):

```bash
MEDIA_DOMAIN=media.example.com # Set the public Jellyfin hostname for the checks.
PHOTOS_DOMAIN=photos.example.com # Set the public Immich hostname for the checks.
curl -I "https://$MEDIA_DOMAIN" # Check the public Jellyfin HTTPS response headers.
curl -I "https://$PHOTOS_DOMAIN" # Check the public Immich HTTPS response headers.
sudo ufw status numbered # Review enabled firewall rules and their numbers.
sudo ss -lntp # Show listening TCP ports to verify only intended services are exposed.
```

> Example response: each `curl` check returns an HTTP status line such as `HTTP/2 200` or `HTTP/1.1 302 Found`.

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
findmnt /srv/media # Confirm the media drive remains mounted.
df -hT /srv/media /var/lib/immich # Review space and filesystem types for media and database storage.
sudo systemctl status --no-pager jellyfin nginx certbot.timer # Check the services and automatic renewal timer.
sudo docker compose -f /opt/immich/docker-compose.yml ps # Check whether Immich containers are running.
sudo docker compose -f /opt/immich/docker-compose.yml logs --tail=50 # Review recent Immich logs for errors.
sudo nginx -t # Validate the active Nginx configuration.
sudo certbot renew --dry-run # Test HTTPS certificate renewal without changing certificates.
```

> Example healthy checks show the drive mounted, services `active (running)`, containers `Up`, and Nginx `test is successful`.

Check drive health and recent kernel disk errors:

```bash
sudo smartctl -a -d sat /dev/sdX # Read SMART drive-health details; replace sdX with the verified disk.
sudo journalctl -k --since today | grep -Ei 'usb|uas|reset|I/O error|ext4' # Search today's kernel log for USB and filesystem errors.
```

> Example: SMART reports `SMART overall-health self-assessment test result: PASSED`; no matching kernel lines means the search found no listed errors today.

Make a second backup of irreplaceable photos and the Immich database on another disk or backup service. The 4 TB drive is storage, not a backup. Immich's built-in database dump does not back up the original media files; back up both `/srv/media/immich` and `/var/lib/immich`.

Useful service logs:

```bash
sudo journalctl -u jellyfin -f # Follow Jellyfin's live service log.
sudo journalctl -u nginx -f # Follow Nginx's live service log.
sudo docker compose -f /opt/immich/docker-compose.yml logs -f # Follow live logs from Immich containers.
```

## Official References

- [Ubuntu disk formatting](https://help.ubuntu.com/stable/ubuntu-help/disk-format.html.en)
- [Western Digital filesystem guidance](https://support-en.wd.com/app/answers/detailweb/a_id/20821)
- [MakeMKV downloads](https://www.makemkv.com/download/) and [current beta key thread](https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053)
- [HandBrake official presets](https://handbrake.fr/docs/en/latest/technical/official-presets.html)
- [Jellyfin Ubuntu/Linux installation](https://jellyfin.org/docs/general/installation/linux/) and [Nginx reverse proxy](https://jellyfin.org/docs/general/networking/nginx/)
- [Immich quick start](https://docs.immich.app/overview/quick-start/) and [storage requirements](https://docs.immich.app/install/requirements/)
- [Tailscale Linux install](https://tailscale.com/docs/install/linux) and [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
