# Media Server Detailed Reference

Start with the [short guide](media_server.md). Open the sections below when installing something for the first time, changing advanced settings, or investigating a problem. Run only the section you need; this is not a script to paste from top to bottom.

This guide targets the Ubuntu 22.04 LTS home server from `hosting.md`, where SAS and David are already hosted. It uses the 4 TB WD drive for movies, shows, and Immich uploads, while keeping Immich's PostgreSQL database on the server's internal SSD. Replace `example.com` with your domain. The commands that format the disk erase the selected disk; stop and verify the model, serial, and size before running them.

The server already has the shared hosting setup: Nginx, Certbot, UFW, SSH, and public router forwarding for ports 80 and 443. Do not repeat the base setup or reset the firewall, remove existing Nginx sites, or change the SAS and David proxy rules. Section 1 installs the extra tools; later sections add Jellyfin, Immich, Tailscale, and a separate Nginx site while reusing the existing HTTPS and network setup. Its public-access section assumes you want media hostnames on the same server.

Read section 4 for the everyday ripping/encoding workflow, settings, and optional night schedule; sections 1–3 and 5–8 are setup. Section 10 explains healthy results and what to investigate. The examples assume ordinary DVD/Blu-ray SDR sources. UHD/4K HDR discs, unusual disc protection, and optical-drive firmware need separate checks; this command is not an HDR-preservation recipe.

<a id="base-tools"></a>

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

Install the additional download, USB, disk, and queue tools (apt keeps already-installed packages). The hosting guide already installed the web-server and firewall packages:

```bash
sudo apt update # Refresh Ubuntu's package index before installing disk tools.
sudo apt install -y curl wget ca-certificates gnupg lsb-release usbutils parted e2fsprogs smartmontools util-linux # Add download, USB, disk, and queue-lock tools if missing.
```

The existing firewall and Nginx installation are checked below; leave their existing rules and virtual hosts in place.

Check the result:

```bash
nginx -v # Print the installed Nginx version.
sudo systemctl status --no-pager nginx # Confirm the web server is running.
sudo ufw status verbose # Confirm the firewall is active with the expected rules.
```

> Example checks: `nginx version: nginx/1.18.0 (Ubuntu)`, `Active: active (running)`, and UFW `Status: active` with the existing SSH and web rules. Package versions vary.

<a id="drive"></a>

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

Only do this initial format for the empty external drive, once. On later visits, go straight to the mount checks. Run the entire block together: the parentheses create a shell where `set -e` and explicit `exit` guards stop later destructive commands without closing your SSH session. Replace both device placeholders before starting; never choose the disk holding the server's OS or app databases.

```bash
( # Keep all erase checks and destructive commands in one guarded shell.
set -eu # Stop this block on a failed command or unset variable.
DISK=/dev/sdX # Replace with the external disk identified above.
PART=/dev/sdX1 # Replace with its expected first partition.
test -b "$DISK" # Reject the placeholder or a nonexistent block device.
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DISK" # Review this exact disk and every child partition.
read -r -p "Type ERASE $DISK to permanently erase this external disk: " CONFIRM # Require exact confirmation.
test "$CONFIRM" = "ERASE $DISK" # A mismatch stops this entire block.
if lsblk -nrpo MOUNTPOINTS "$DISK" | grep -q '[^[:space:]]'; then echo 'STOP: disk has a mounted filesystem'; exit 1; fi # Refuse disks with mounted partitions.
sudo parted --script "$DISK" mklabel gpt mkpart primary ext4 1MiB 100% # Erase the partition table and create one partition.
sudo partprobe "$DISK" # Ask Linux to reread the partition table.
sudo udevadm settle # Wait for the new device node to appear.
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS "$DISK" # Check the partition just created.
test -b "$PART" # Require the partition device to exist.
test "$(lsblk -ndo PKNAME "$PART")" = "$(basename "$DISK")" # Ensure the partition belongs to the confirmed disk.
read -r -p "Type FORMAT $PART after checking the new partition: " CONFIRM # Confirm the exact partition to format.
test "$CONFIRM" = "FORMAT $PART" # Stop if confirmation differs.
if lsblk -nrpo MOUNTPOINTS "$DISK" | grep -q '[^[:space:]]'; then echo 'STOP: partition mounted during setup'; exit 1; fi # Recheck in case desktop automount ran.
sudo mkfs.ext4 -L MEDIA "$PART" # Create the ext4 filesystem only after all checks pass.
sudo blkid "$PART" # Print the new filesystem UUID and type.
)
```

> Expect a roughly 3.6 TiB partition, and final `blkid` output containing `TYPE="ext4"` and a `UUID`. If a guard fails, stop and identify why; do not paste individual format commands to bypass it. Unmount only the verified external partition if it was automounted, then repeat identification. This check depends on you choosing the correct disk.

Mount by filesystem UUID so the mount survives a reboot even if Linux assigns the drive another `/dev/sd*` name:

```bash
( # Keep the mount setup and its checks together.
set -eu # Stop this block if the UUID or mount checks fail.
PART=/dev/sdX1 # Replace again with the verified ext4 partition; the earlier block used its own shell.
UUID=$(sudo blkid -s UUID -o value "$PART") # Read the formatted partition's UUID.
test -n "$UUID" # Stop this block if the UUID lookup failed.
sudo mkdir -p /srv/media # Create the permanent mount directory.
grep -q "UUID=$UUID " /etc/fstab || echo "UUID=$UUID /srv/media ext4 defaults,nofail,x-systemd.device-timeout=10 0 2" | sudo tee -a /etc/fstab # Add one fstab entry if it is not already present.
sudo findmnt --verify --verbose # Check that the fstab entry parses correctly.
sudo mount /srv/media # Mount the drive at /srv/media.
findmnt /srv/media # Show the mounted filesystem and source device.
df -hT /srv/media # Show filesystem type and available capacity.
)
```

> Example success: `findmnt` reports `FSTYPE ext4`; `df` reports about `3.6T` total for the 4 TB drive.

Create the shared media folders and permissions only during first setup, after confirming the drive is mounted. Do not rerun recursive ownership changes once Immich has created its files. The `media` group lets Jellyfin read the files while your login can rip and organize them.

```bash
( # Stop before changing permissions if the external drive is missing.
set -e # Stop this setup block on an error.
mountpoint -q /srv/media # Require the real external mount.
sudo groupadd --force media # Create the shared media group if needed.
sudo usermod -aG media "$USER" # Let your login manage media files.
sudo mkdir -p /srv/media/{movies,shows,rips/movies,rips/shows,immich} # Create the movie, show, rip, and Immich folders.
sudo chown -R "$USER":media /srv/media # Assign files to your login and shared group.
sudo find /srv/media -type d -exec chmod 2775 {} + # Give folders group write access and inherit the media group.
sudo find /srv/media -type f -exec chmod 0664 {} + # Give existing files group read/write access.
ls -ld /srv/media /srv/media/{movies,shows,rips,immich} # Show ownership and permissions.
df -h /srv/media # Confirm the expected free space remains.
)
```

> Example folder permissions start with `drwxrwsr-x` and show your login with group `media`.

Log out and back in after adding your account to `media`. At a maintenance time, verify the mount after reboot; rebooting temporarily interrupts SAS, David, and all other services on this machine:

```bash
sudo reboot # Restart so the external drive mounts and the new group membership applies.
```

After reconnecting:

```bash
findmnt /srv/media # Confirm the UUID-based mount returned after reboot.
df -hT /srv/media # Check filesystem type and free space after reboot.
mountpoint -q /srv/media && touch /srv/media/.write-check && rm /srv/media/.write-check && echo "Drive is mounted and writable" # Create and remove a temporary file to verify write access.
```

> Example confirmation: `Drive is mounted and writable`.

<a id="software"></a>

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
( # Build both components in one shell that stops on failure.
set -eu # Fail before installation if archives or build commands fail.
OSS_ARCHIVE=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-oss-*.tar.gz' -printf '%f\n' | sort -V | tail -n 1) # Find the newest MakeMKV open-source archive.
BIN_ARCHIVE=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'makemkv-bin-*.tar.gz' -printf '%f\n' | sort -V | tail -n 1) # Find the matching binary archive.
test -n "$OSS_ARCHIVE" # Require the open-source archive.
test -n "$BIN_ARCHIVE" # Require the binary archive.
test "${OSS_ARCHIVE#makemkv-oss-}" = "${BIN_ARCHIVE#makemkv-bin-}" # Require matching versions before compiling.
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
)
```

> Example archive listing includes a matching pair such as `makemkv-oss-1.18.4.tar.gz` and `makemkv-bin-1.18.4.tar.gz`; versions change.

Check the CLI and optical drive:

```bash
makemkvcon info disc:0 # Inspect the disc in the first optical drive.
```

> Example disc feedback includes the MakeMKV version and a list of title numbers, durations, and sizes. No disc or a drive-access problem produces an error instead.

For Blu-ray use, get the current beta key from the official [MakeMKV beta-key forum thread](https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053). Do not paste a key copied from an old guide; beta keys expire. Add the key to your Linux user's MakeMKV settings without putting it in shell history:

```bash
mkdir -p "$HOME/.MakeMKV" # Create MakeMKV's per-user settings directory.
touch "$HOME/.MakeMKV/settings.conf" # Create the settings file if this is the first key.
chmod 600 "$HOME/.MakeMKV/settings.conf" # Restrict access before writing the key.
sed -i '/^app_Key[[:space:]]*=/d' "$HOME/.MakeMKV/settings.conf" # Remove an expired key instead of appending conflicting values.
read -r -s -p "Paste the current MakeMKV beta key: " MAKEMKV_KEY # Read the key without displaying it in the terminal.
printf '\napp_Key = "%s"\n' "$MAKEMKV_KEY" >> "$HOME/.MakeMKV/settings.conf" # Save the key using MakeMKV's Linux setting name.
unset MAKEMKV_KEY # Remove the key from the current shell environment.
chmod 600 "$HOME/.MakeMKV/settings.conf" # Restrict the key file to your user account.
makemkvcon info disc:0 # Check that MakeMKV can read the disc with the key installed.
```

For unattended jobs, use Ubuntu's native CLI package so systemd can run `/usr/bin/HandBrakeCLI` without a graphical login or Flatpak session. This is the Ubuntu-maintained build, which may be older than HandBrake's upstream release. The examples use x264 options supported by Ubuntu 22.04's package; verify the installed help before adding other encoders. [Ubuntu package](https://packages.ubuntu.com/jammy/handbrake-cli).

```bash
sudo apt update # Refresh Ubuntu's package index.
sudo apt install -y handbrake-cli ffmpeg time # Install the encoder, ffprobe for inspection, and elapsed-time measurement.
HandBrakeCLI --version # Confirm the native encoder is installed.
HandBrakeCLI --preset-list 2>&1 | grep -F 'Fast 1080p30' # Confirm the named preset exists.
HandBrakeCLI --help | less # Inspect the options supported by this installed version; q exits less.
```

> Expect a version line and a `Fast 1080p30` preset. If apt cannot find the CLI, enable Ubuntu's Universe repository using `sudo add-apt-repository universe`, then repeat the install. Existing Flatpak installations can stay; the queue below specifically uses the native CLI.

## 4. Rip, Choose Quality, and Encode Overnight

The flow is **disc → MakeMKV rip → your title/language check → HandBrake encode → Jellyfin library → playback**. MakeMKV copies the selected disc streams without reducing their video quality. HandBrake creates a smaller, lossy viewing copy. Jellyfin serves that copy and may convert it again during playback if the client or network needs it. Immich handles photos separately; this movie queue never processes its uploads.

For the everyday disc-copying and approval commands, follow [Add a movie](media_server.md#2-add-a-movie). The sections below explain advanced settings and the one-time queue installation.

<a id="tuning"></a>

### 4.2 Settings you can change

Start with the table's defaults, then change one setting at a time. RF is a quality target, **not a percentage or a file-size ratio**. The following ranges apply to the x264 software encoder used here; do not carry RF numbers over to a different codec or hardware encoder.

| Setting | Default here | Range or alternatives | Effect and tradeoff |
|---|---|---|---|
| Video quality, `--quality` / queue `RF` | `20` | x264's 8-bit RF scale is 0–51; useful first comparisons are 18, 20, 22, 24 | Lower RF keeps more detail and usually makes larger files. Higher RF loses more detail and usually saves space. RF 0 is lossless encoding, often huge, and cannot restore detail missing from a disc. |
| Encoder effort, `--encoder-preset` / `ENCODER_PRESET` | `fast` | `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium`, `slow`, `slower`, `veryslow`, `placebo` | Slower settings spend more CPU time improving compression efficiency. Compare `fast`, `medium`, and `slow`; file size and visual quality can both shift at the same RF. `placebo` is rarely worth its time. This differs from the overall `Fast 1080p30` preset. |
| Resolution and frame cap, `--preset` | `Fast 1080p30` | `Fast 720p30` for smaller copies; a verified 1080p60 preset for high-frame-rate sources | 720p discards detail. The 1080p30 preset caps at 1080p/30 fps and does not make a DVD look like Blu-ray. Ordinary 24 fps films stay around 24 fps; high-frame-rate sources can lose motion frames under this cap. |
| Codec/container | x264 H.264 in MP4 | H.265/AV1 or MKV are separate compatibility choices | H.264/AAC/MP4 is a useful compatibility baseline. Newer codecs can save space but require client and server checks. The queue below deliberately exposes only its documented H.264 settings. |
| Audio bitrate, `--ab` / `AUDIO_KBPS` | `160` kb/s AAC stereo | Compare 128, 160, 192, or 256 | Higher bitrate uses more space for audio. At 160 kb/s, one two-hour stereo track uses about 144 MB. This command downmixes surround sound to stereo and does not preserve lossless audio or Atmos. |
| Audio selection, `--audio` | Track `1` | HandBrake's numbered source tracks | Select the dialogue language, not a commentary track. The queue takes an optional per-file `.audio` sidecar containing one track number. Surround/multiple-audio copies need a separately reviewed command. |
| Subtitles | None in the explicit queue command | Select a track, keep an external SRT, or burn a chosen track into the image | The sample's `--subtitle none` omits even foreign-dialogue subtitles. Check scenes that need them. Burn-in is permanent; disc image subtitles and some clients can force Jellyfin video transcoding. Do not approve a title needing subtitles for this basic queue until you choose its handling. |
| CPU budget | One encode at a time; service `CPUQuota=200%` | `100%` ≈ one logical CPU, `200%` ≈ two; lower to preserve site capacity | Limits total CPU time for the service and its children. It is not 200% of the whole machine. Lower quotas slow completion. `Nice=10` gives competing normal-priority work preference; it does not replace the quota. |
| Memory budget | No hard limit set in this example | Optional service `MemoryMax`, chosen after measuring available RAM | A cap protects other services but can kill the encoder if too low; lower CPU use does not guarantee low RAM use. Check `free -h` during a sample before choosing a cap. |
| Time budget | Start 23:00, run at most 8 hours | Change timer `OnCalendar` and service `RuntimeMaxSec` | A time limit can interrupt a long movie. Finished movies stay; the interrupted movie starts over next run. There is no encode checkpoint/resume in this script. |
| Disk reserve | Source size plus 20 GiB available before each file | Queue `MIN_FREE_GIB` | A conservative starting check, not a guarantee: another service or an unusually large encode can still fill the disk. Sources are kept, so space must cover both rip and output. |

HandBrake recommends RF **20–24 for 1080p** and **18–22 for DVD-resolution sources**. RF 20 is a useful quality-oriented starting point for family viewing, but whether differences are visible depends on the source, screen, distance, and viewer. Grain, dark scenes, and motion deserve particular attention. [HandBrake quality guidance](https://handbrake.fr/docs/en/latest/workflow/adjust-quality.html). Encoder speed settings also affect size and quality, so compare rather than assuming a fixed savings percentage. [HandBrake performance guidance](https://handbrake.fr/docs/en/latest/technical/performance.html).

<a id="samples"></a>

### 4.3 Compare a short scene before committing a whole night

Use a two-minute scene ten minutes into the source; choose another starting position for a difficult scene. These commands are examples to run on your server. Results and timings here are illustrative, not measurements of your hardware.

```bash
INPUT='/srv/media/rips/movies/Movie Name (year)/Movie Name (year).mkv' # Replace with a finished rip.
SAMPLE_DIR=$(mktemp -d /srv/media/quality-samples.XXXXXX) # Keep comparison clips outside Jellyfin and avoid overwriting older samples.
for RF in 18 20 22 24; do # Compare the same scene with only the RF value changed.
    /usr/bin/time -p HandBrakeCLI -i "$INPUT" -o "$SAMPLE_DIR/rf-$RF.mp4" --preset='Fast 1080p30' --encoder=x264 --encoder-preset=fast --quality="$RF" --audio=1 --aencoder=av_aac --ab=160 --mixdown=stereo --subtitle none --start-at seconds:600 --stop-at seconds:120 # Encode the sample and report elapsed seconds.
done
ls -lh "$SAMPLE_DIR" # Compare file sizes, then watch all clips on the TV you will use.
```

> Expect HandBrake progress and `Encode done!` on success, followed by `real` elapsed seconds from `time`. RF 18 will often be larger than RF 24. No fixed compression ratio is promised. If 120 seconds takes 60 seconds to encode, a two-hour movie might take about an hour with those settings and that machine load; different scenes and thermal throttling change that estimate.

Compare `fast` versus `medium` next using your chosen RF. Keep the original rip until you have checked the full viewing copy, including language, subtitles, sound, seeking, and end credits. Keeping it permanently preserves the option to re-encode but uses much more of the 4 TB drive. Do not run a large sample comparison during a busy SAS event; the service's CPU limits below do not apply to these direct shell commands.

<a id="queue"></a>

### 4.4 Install a queue that publishes only finished files

The queue accepts only MKVs with a neighboring `.ready` marker. Add that marker **after** ripping, renaming, track review, and your sample check. Never edit or replace a source while it is queued. If you used the old queue, inspect its existing MP4s first: it could leave incomplete files with final names. Existing final outputs are skipped even after quality settings change; to redo one, first stop the service and move its old output to an archive outside the library.

Install this script once. It encodes into `/srv/media/.encoding`, outside Jellyfin's libraries, then checks for video and approximately matching duration before moving the MP4 into Movies or Shows. That is a basic integrity check, not a replacement for watching the result. A failed or interrupted job cannot publish its partial output as a completed movie.

```bash
sudo tee /usr/local/bin/media-encode >/dev/null <<'SCRIPT' # Save the reusable queue script.
#!/usr/bin/env bash
set -euo pipefail # Stop on unexpected command failures, unset variables, and failed pipelines.
umask 002 # Let the shared media group read and manage the results.
RF=${RF:-20} # Default video quality; environment overrides it for a whole run.
ENCODER_PRESET=${ENCODER_PRESET:-fast} # Default x264 effort setting.
AUDIO_KBPS=${AUDIO_KBPS:-160} # AAC stereo bitrate.
MIN_FREE_GIB=${MIN_FREE_GIB:-20} # Reserve additional disk space beyond the source size.
[[ "$RF" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk -v rf="$RF" 'BEGIN {exit !(rf >= 0 && rf <= 51)}' || { echo 'ERROR: RF must be between 0 and 51'; exit 1; } # Validate the quality setting.
[[ "$MIN_FREE_GIB" =~ ^[0-9]+$ ]] || { echo 'ERROR: MIN_FREE_GIB must be an integer'; exit 1; } # Validate the disk reserve.
mountpoint -q /srv/media || { echo 'ERROR: media drive is not mounted'; exit 1; } # Never write a missing drive's data onto the SSD mount directory.
exec 9>/srv/media/.encode.lock # Open a shared lock file for all runs of this script.
flock -n 9 || { echo 'ERROR: another queue is already running'; exit 1; } # Prevent duplicate concurrent encodes.
test -d /srv/media/rips/movies # Require the movie queue directory.
test -d /srv/media/rips/shows # Require the show queue directory.
mkdir -p /srv/media/.encoding # Keep temporary output outside the Jellyfin libraries.
TEMP_OUTPUT='' # Track only this run's temporary file for cleanup.
trap 'if [[ -n "$TEMP_OUTPUT" ]]; then rm -f -- "$TEMP_OUTPUT"; fi' EXIT # Remove unfinished output when the script exits normally or after a handled signal.
trap 'exit 130' INT # Clean up if interrupted in a terminal.
trap 'exit 143' TERM # Clean up when systemd stops the service.
FAILED=0 # Return a failure status if any approved file cannot be encoded.
COUNT=0 # Count successful files for the final log message.
while IFS= read -r -d '' INPUT; do # Safely handle paths containing spaces.
    [[ -f "$INPUT.ready" ]] || continue # Ignore unapproved files, including rips still being written.
    RELATIVE=${INPUT#/srv/media/rips/} # Preserve movie and season subfolders.
    OUTPUT="/srv/media/${RELATIVE%.mkv}.mp4" # Map rips/movies or rips/shows to the corresponding library.
    if [[ -e "$OUTPUT" ]]; then echo "SKIP: $OUTPUT"; continue; fi # Leave previously completed outputs alone.
    echo "PLAN: $INPUT -> $OUTPUT (RF=$RF, encoder=$ENCODER_PRESET)" # Show exactly what will be processed.
    [[ "${1:-}" == '--dry-run' ]] && continue # List queued work without encoding or publishing files.
    AVAILABLE=$(df -B1 --output=avail /srv/media | tail -1) # Read available bytes on the media drive.
    SOURCE_SIZE=$(stat -c %s -- "$INPUT") # Read the source file's size for a conservative space check.
    if (( AVAILABLE < SOURCE_SIZE + MIN_FREE_GIB * 1073741824 )); then echo 'ERROR: insufficient free space'; exit 1; fi # Stop before consuming the reserve.
    AUDIO_TRACK=1 # Use the first audio track unless this source has an override.
    if [[ -f "$INPUT.audio" ]]; then AUDIO_TRACK=$(cat -- "$INPUT.audio"); fi # Read the selected HandBrake audio-track number.
    if [[ ! "$AUDIO_TRACK" =~ ^[1-9][0-9]*$ ]]; then echo "FAILED: invalid audio track for $INPUT"; FAILED=1; continue; fi # Reject malformed overrides.
    SOURCE_SECONDS=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$INPUT") # Read source duration; an unreadable source stops the queue.
    TEMP_OUTPUT=$(mktemp --suffix=.mp4 /srv/media/.encoding/movie.XXXXXX) # Allocate a private file on the same drive as the final output.
    if HandBrakeCLI -i "$INPUT" -o "$TEMP_OUTPUT" --preset='Fast 1080p30' --format=av_mp4 --encoder=x264 --encoder-preset="$ENCODER_PRESET" --quality="$RF" --audio="$AUDIO_TRACK" --aencoder=av_aac --ab="$AUDIO_KBPS" --mixdown=stereo --subtitle none </dev/null; then # Encode one approved source without consuming the queue's filename input.
        OUTPUT_SECONDS=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TEMP_OUTPUT" || true) # Read completed output duration.
        VIDEO=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$TEMP_OUTPUT" || true) # Confirm a video stream exists.
        AUDIO=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$TEMP_OUTPUT" || true) # Check that the requested audio produced a stream.
        if [[ "$VIDEO" == h264 && "$AUDIO" == aac ]] && awk -v s="$SOURCE_SECONDS" -v o="$OUTPUT_SECONDS" 'BEGIN {d=s-o; if(d<0)d=-d; t=s*0.01; if(t<5)t=5; exit !(s>0 && o>0 && d<=t)}'; then # Allow 1% or five seconds of duration difference.
            mkdir -p "$(dirname "$OUTPUT")" # Create the final library folder only after encoding.
            chmod 664 "$TEMP_OUTPUT" # Make the finished file readable by Jellyfin's media group.
            mv -- "$TEMP_OUTPUT" "$OUTPUT" # Publish the completed file with a same-filesystem rename.
            TEMP_OUTPUT='' # Mark the temporary file as already moved.
            COUNT=$((COUNT + 1)) # Count successful encodes.
            echo "DONE: $OUTPUT" # Log the filename that is now ready to watch.
            continue # Process the next approved source.
        fi
    fi
    echo "FAILED: $INPUT (encode or integrity check)" # Preserve the source and flag this job for review.
    rm -f -- "$TEMP_OUTPUT" # Remove only the incomplete output created by this run.
    TEMP_OUTPUT='' # Reset cleanup state before the next file.
    FAILED=1 # Make the service report a failed run even if later files succeed.
done < <(find /srv/media/rips/movies /srv/media/rips/shows -type f -name '*.mkv' -print0 | sort -z) # Process both libraries in filename order.
echo "QUEUE FINISHED: completed=$COUNT failed=$FAILED" # Summarize successful files and whether any failed.
exit "$FAILED" # Let systemd distinguish success from a failed run.
SCRIPT
sudo chmod 755 /usr/local/bin/media-encode # Make the script executable by your media user.
```

Queue one file after checking its language and any required subtitles:

```bash
INPUT='/srv/media/rips/movies/Movie Name (year)/Movie Name (year).mkv' # Set the exact approved source.
printf '1\n' > "$INPUT.audio" # Set the desired HandBrake audio track; change 1 if needed.
touch "$INPUT.ready" # Approve this completed source for the next queue run.
/usr/local/bin/media-encode --dry-run # Show approved files and outputs without encoding.
```

> Expect `PLAN: ... (RF=20, encoder=fast)`. No `PLAN` lines means there are no approved files waiting; `SKIP` means a final output already exists. Remove a source's `.ready` file to take it out of future runs. Completed `.ready` markers can stay because the output check skips them.

<a id="nightly"></a>

### 4.5 Optional automatic overnight schedule

This setup is an **example you can opt into on the home server**. The repository update itself does not install or enable it. The example uses 23:00 in the server's timezone, a maximum of eight hours per run, one encoder, and two logical CPUs' worth of CPU time. Change those values before enabling it if your sleep window or server capacity differs. A two-core server may need `CPUQuota=100%` or less to leave room for SAS, David, Immich, and Jellyfin. The I/O priority is advisory and depends on the drive's Linux scheduler. See systemd's [resource controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html) and [runtime limits](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).

```bash
timedatectl # Check the server's current timezone before deciding what 23:00 means.
nproc # Count logical CPUs to choose an appropriate CPU quota.
ENCODE_USER=$(id -un) # Use the login that owns the media files; run this setup as that user, not from a root shell.
sudo tee /etc/systemd/system/media-encode.service >/dev/null <<EOF # Create a service that runs without an SSH session.
[Unit]
Description=Encode approved movie and show rips
RequiresMountsFor=/srv/media
ConditionPathIsMountPoint=/srv/media

[Service]
Type=exec
User=$ENCODE_USER
SupplementaryGroups=media
Environment=RF=20 ENCODER_PRESET=fast AUDIO_KBPS=160 MIN_FREE_GIB=20
ExecStart=/usr/local/bin/media-encode
Nice=10
CPUQuota=200%
IOSchedulingClass=best-effort
IOSchedulingPriority=7
RuntimeMaxSec=8h
KillMode=control-group
TimeoutStopSec=30s
EOF
sudo tee /etc/systemd/system/media-encode.timer >/dev/null <<'EOF' # Schedule one nightly start, without daytime catch-up after a missed night.
[Unit]
Description=Start media encoding each night

[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=false
Unit=media-encode.service

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload # Load the new service and timer definitions.
sudo systemctl start --no-block media-encode.service # Run once now after the dry run, so you can inspect a real result before enabling automation.
sudo journalctl -u media-encode.service -f # Watch progress live; Ctrl+C stops following the log, not the job.
```

> During work, service status should show `active (running)` and the journal should show `PLAN`, encoder progress, then `DONE`. After a clean run, `inactive (dead)` is normal because this is a finite queue. It is not a permanent web server. An eight-hour timeout is measured from the actual start, including a manual start; it is not an independent 07:00 wall-clock stop.

After checking one full movie, enable the optional timer:

```bash
sudo systemctl enable --now media-encode.timer # Enable nightly runs now and across server reboots.
systemctl list-timers --all media-encode.timer # Show the next and previous scheduled start times.
systemctl show media-encode.service -p Result -p ExecMainStatus # Show the result of the most recent run.
sudo journalctl -u media-encode.service --since yesterday --no-pager | tail -80 # Review last night's progress and failures.
```

> Expect a next trigger near 23:00, and after a successful run `Result=success` / `ExecMainStatus=0`. If the limit stops a movie, expect `Result=timeout`; that movie is retried from the beginning next night. A movie taking longer than the time budget every night will never finish until you increase the budget or use faster settings. Failed source jobs are also retried while their `.ready` markers remain.

The server must be powered on, awake, and have the media drive mounted. This timer does not wake a powered-off computer. `Persistent=false` skips missed nights instead of starting a heavy job at the next daytime boot. systemd does not start a second instance while this service is active; the script also locks out duplicate manual invocations. A power loss or forced kill can leave a file in `.encoding`, but the next run never treats it as a finished movie; inspect and remove such leftovers only while the service is stopped. [systemd timer behavior](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).

Change settings or turn the option off:

```bash
sudo systemctl disable --now media-encode.timer # Prevent new automatic starts; an already-running encode continues.
sudo systemctl stop media-encode.service # Stop the current encode and its child processes if desired.
sudo nano /etc/systemd/system/media-encode.service # Adjust RF, speed, CPU quota, reserve, or maximum runtime for future runs.
sudo nano /etc/systemd/system/media-encode.timer # Adjust the nightly start time.
sudo systemctl daemon-reload # Load your edits.
sudo systemctl enable --now media-encode.timer # Resume the schedule when ready.
```

Changing RF does not replace previously published MP4s, and it does not change the settings of an encode already running. This workflow has journal logs but no email alerts; inspect the morning result before trusting a large unattended batch.

<a id="jellyfin"></a>

## 5. Install Jellyfin

Install Jellyfin from the official Ubuntu repository setup script and verify its published checksum before running it:

```bash
( # Run installer verification and installation in one guarded block.
set -e # Prevent installation after a failed download or checksum.
cd /tmp # Use a temporary folder for the repository setup files.
curl -fsSLO https://repo.jellyfin.org/install-debuntu.sh # Download the official Jellyfin setup script.
curl -fsSLO https://repo.jellyfin.org/install-debuntu.sh.sha256sum # Download its published checksum.
sha256sum -c install-debuntu.sh.sha256sum # Verify the downloaded script before running it.
sudo bash install-debuntu.sh # Configure Jellyfin's official Ubuntu package source.
sudo apt install -y jellyfin # Install Jellyfin from that package source.
)
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

<a id="immich"></a>

## 6. Install Immich

Install Docker Engine and the Compose plugin from Docker's official Ubuntu repository. The mount override below applies to the entire Docker daemon: all Docker workloads wait for the media drive, and restarting Docker interrupts its containers. It fits a Docker installation dedicated to Immich; if Docker already hosts other work, review this dependency before applying it. SAS and David in `hosting.md` run as separate native services. The database in Immich's Compose stack is separate from their existing PostgreSQL databases.

```bash
sudo install -m 0755 -d /etc/apt/keyrings # Create the trusted repository key folder.
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc # Download Docker's signing key.
sudo chmod a+r /etc/apt/keyrings/docker.asc # Allow apt to read the signing key.
. /etc/os-release # Load the Ubuntu release codename for the repository entry.
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null # Add Docker's official Ubuntu package source.
sudo apt update # Refresh package metadata with Docker's repository.
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin # Install Docker Engine and Compose.
sudo mkdir -p /var/lib/immich /etc/systemd/system/docker.service.d # Create the SSD directory before using it in the mount dependency.
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

Keep the database on the internal SSD and the photos/videos on the mounted 4 TB drive. For a first installation only, download the official Immich Compose and environment files and set their paths. The guarded block refuses to overwrite existing configuration. Use `nano` to replace the sample database password with a unique letters-and-numbers password before startup; do not change it on an existing database without following the database password-change procedure:

```bash
( # Keep first-install checks together so a failure prevents later downloads.
set -eu # Stop before overwriting files if the first-install checks fail.
mountpoint -q /srv/media # Require the external drive before creating upload folders.
sudo mkdir -p /opt/immich /var/lib/immich/postgres /srv/media/immich # Create compose, SSD database, and external upload folders.
sudo chown -R "$USER":"$USER" /opt/immich # Let your login maintain the Compose files.
cd /opt/immich # Enter the Immich configuration folder.
if [[ -e .env || -e docker-compose.yml ]]; then echo 'STOP: existing Immich configuration; use the update procedure'; exit 1; fi # Never overwrite either configuration file.
curl -fL -o docker-compose.yml https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml # Download Immich's official Compose file.
curl -fL -o .env https://github.com/immich-app/immich/releases/latest/download/example.env # Download its matching environment template.
sed -i 's|^UPLOAD_LOCATION=.*|UPLOAD_LOCATION=/srv/media/immich|' .env # Store uploaded photos and videos on the external drive.
sed -i 's|^DB_DATA_LOCATION=.*|DB_DATA_LOCATION=/var/lib/immich/postgres|' .env # Keep the database files on the internal SSD.
sed -i 's|^DB_PASSWORD=.*|DB_PASSWORD=REPLACE_WITH_A_LONG_LETTERS_AND_NUMBERS_PASSWORD|' .env # Set the database password placeholder to replace before startup.
chmod 600 .env # Restrict the file containing database credentials to your login.
nano .env # Replace DB_PASSWORD's placeholder with your actual password and save.
if grep -q 'REPLACE_WITH_A_LONG_LETTERS_AND_NUMBERS_PASSWORD' .env; then echo 'STOP: choose a real database password'; exit 1; fi # Reject the unedited placeholder.
grep -E '^(UPLOAD_LOCATION|DB_DATA_LOCATION|IMMICH_VERSION)=' .env # Review paths and version without printing the password.
)
```

Return to `/opt/immich` in your main shell (the setup block used a subshell). Edit the Compose file so its published web port is bound to localhost only. This keeps port `2283` private while Nginx and Tailscale provide the two access paths:

```bash
cd /opt/immich # Use the saved Compose and environment files.
grep -n -A3 -B2 '2283:' docker-compose.yml # Locate Immich's published web-port mapping.
nano docker-compose.yml # Edit the mapping to bind only to localhost.
```

In the `immich-server` `ports` list, change the mapping from `2283:2283` to `127.0.0.1:2283:2283`, then start Immich:

```bash
sudo docker compose config --quiet && sudo docker compose up -d # Start only if Compose validates; do not print resolved secrets.
sudo docker compose ps # Show container states and published ports.
sudo docker compose logs --tail=50 immich-server # Review recent Immich server startup output.
curl -I http://127.0.0.1:2283 # Confirm the local Immich web service responds.
df -hT /srv/media /var/lib/immich # Verify external uploads and internal database storage mounts.
```

> Example success: `docker compose ps` shows the Immich containers as `Up`, and `curl` returns an HTTP response such as `200` or `302`.

Open `http://localhost:2283` in the browser while the SSH tunnel from the Jellyfin section is running. Create the administrator account before inviting anyone else. Add each friend/family member as their own Immich user, and leave public registration disabled. Install the Immich mobile app and use the HTTPS URL from the access option they will use below.

<a id="private-access"></a>

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

<a id="public-access"></a>

## 8. Public HTTPS Access for Friends and Family

This option lets people use regular Jellyfin and Immich apps without installing Tailscale. It uses the existing hosting pattern: DNS points to the router's public IP, the router forwards only TCP `80` and `443` to the server, and Nginx routes HTTPS to the private application ports.

Check the public IPv4 address seen on the internet and compare it with the WAN address shown in the Xfinity app:

```bash
curl -4 https://icanhazip.com # Print the public IPv4 address currently seen by internet services.
```

> Example output is a single public IPv4 address such as `203.0.113.10`; the address shown here is illustrative.

Create DNS `A` records such as `media.example.com` and `photos.example.com` pointing to your router's public IPv4 address. Reuse the existing Xfinity TCP `80` and `443` forwards to this server; adding hostnames does not require additional forwards. Do not forward `8096`, `2283`, `5432`, SSH, or Tailscale ports. If your public IP changes, set up a DNS updater with your DNS provider. If the address reported above differs from the Xfinity WAN address, your ISP may use CGNAT; a dynamic DNS updater will not solve that, and public access will need a public IP from the ISP or another publicly reachable relay. The Tailscale option works without router port forwarding.

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
sudo nginx -t && sudo systemctl reload nginx # Reload only if the added site passes the configuration check.
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

Run the following diagnostics on the server. Then turn Wi-Fi off on a phone and open both HTTPS URLs in its browser and apps to verify actual outside access. Server-side curl alone does not prove router forwarding works:

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

<a id="plex"></a>

## 9. Jellyfin and Plex: Pros and Cons

| | Jellyfin | Plex |
|---|---|---|
| Cost and control | Free, open-source, self-hosted; no vendor account is needed for server playback. | Polished setup and user sharing tied to Plex accounts. Plex currently requires Plex Pass or Remote Watch Pass for remote playback of personal media. |
| Apps | Good browser, mobile, and TV clients; app availability and polish vary by device. | Broad, polished clients on many TVs and streaming devices; simpler for less technical family. |
| Remote access | You control the network path. Use Tailscale privately or your own HTTPS reverse proxy publicly. | Plex coordinates remote access, but it depends on Plex account services and its current subscription rules. |
| Maintenance | You manage updates, HTTPS, accounts, backups, and troubleshooting. | Easier account discovery/sharing, but depends more on Plex's service and pricing decisions. |
| Transcoding | Supports hardware acceleration when the server hardware/driver supports it; compatible H.264 files can Direct Play with little server load. | Also supports transcoding; some advanced functionality and remote playback depend on subscription. |

For this setup, Jellyfin avoids a recurring remote-playback subscription and works with either Tailscale or your own public HTTPS endpoint. Plex may be easier for relatives who already use its apps and account sharing. [Plex remote playback rules](https://support.plex.tv/articles/200289506-remote-access/) and [Plex's 2025 remote-playback change](https://www.plex.tv/blog/important-2025-plex-updates/) describe its current remote access model. Jellyfin's supported playback modes and hardware acceleration are in its [transcoding documentation](https://jellyfin.org/docs/general/post-install/transcoding/).

<a id="checks"></a>

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

> Expect the drive mounted, Jellyfin/Nginx `active (running)`, the Certbot timer `active (waiting)`, containers `Up` (and healthy where health checks exist), and Nginx `test is successful`. Containers can take several minutes to initialize; `Up` alone is not proof that login and uploads work.

Check drive health and recent kernel disk errors:

```bash
sudo smartctl -a -d sat /dev/sdX # Read SMART drive-health details; replace sdX with the verified disk.
sudo journalctl -k --since today | grep -Ei 'usb|uas|reset|I/O error|ext4' # Search today's kernel log for USB and filesystem errors.
```

> Example: SMART reports `SMART overall-health self-assessment test result: PASSED`; no matching kernel lines means this filter found nothing today, not proof the drive is healthy. Some USB bridges do not expose SMART; an unsupported-command result is not a disk-health verdict. USB reset/I/O-error lines during copying merit investigation.

Make a second backup of irreplaceable photos and a consistent Immich database dump on another disk or backup service. Copy the upload files and database dumps stored under `/srv/media/immich` (including `backups`), plus the Compose configuration and protected `.env`. A live copy of `/var/lib/immich/postgres` alone is not a reliable PostgreSQL backup. Follow the installed Immich version's dump/restore instructions and verify a restore before depending on it. Automatic database dumps left on the same 4 TB disk do not protect against losing that disk. [Immich backup and restore](https://docs.immich.app/administration/backup-and-restore/).

Useful service logs:

```bash
sudo journalctl -u jellyfin -f # Follow Jellyfin's live service log.
sudo journalctl -u nginx -f # Follow Nginx's live service log.
sudo docker compose -f /opt/immich/docker-compose.yml logs -f # Follow live logs from Immich containers.
```

### Playback and troubleshooting

Play a complete encoded title in the actual Jellyfin TV/iPhone client. Inspect Jellyfin's playback information or Dashboard while it plays: **Direct Play** serves the saved file; **Remux/Direct Stream** changes packaging and may convert audio; **video transcoding** encodes the video again and costs CPU and potentially quality. Client subtitle support, audio format, and remote bitrate limits can trigger that extra work. Use Jellyfin's reported reason to choose the next setting to change. [Jellyfin playback modes](https://jellyfin.org/docs/general/post-install/transcoding/).

Remote viewing uses the home connection's **upload** speed. Estimate average file bitrate as `file bytes × 8 ÷ duration seconds ÷ 1,000,000` in Mb/s. For example, 4 GB over two hours averages about 4.4 Mb/s, but peaks need headroom and simultaneous viewers add together. Test on cellular before inviting family; smaller files can help bandwidth, while adding CPU cannot fix a saturated upload link.

| What you see | What it means / next check |
|---|---|
| MakeMKV reports read errors or zero saved titles | Check disc/drive connection and the current key before queuing any output. |
| Queue prints `PLAN` but no `DONE` | Check whether this was `--dry-run`, an ongoing encode, a disk-space error, or a failure in the journal. |
| Timer has no next run | Check `systemctl status media-encode.timer`, whether it is enabled, and the server timezone. |
| Service says `inactive (dead)` with result success | A finite queue completed normally, possibly with nothing approved. Read the summary. |
| Service says `failed`, result timeout, or nonzero exit | Inspect the journal. A timeout discards the partial encode and retries from the beginning later; repeated timeouts need faster settings or a larger time budget. |
| Missing mount / output unexpectedly on the SSD | Stop writers, restore the external mount, and check `findmnt /srv/media`. Never format a drive merely because it failed to mount. |
| Movie exists but has wrong language or no foreign-dialogue subtitles | Recheck source tracks; the basic queue produces one selected stereo track and no subtitles. |
| File is complete but absent in Jellyfin | Check the Movies/Shows library paths, run a library scan, verify names and `media` group read/traverse permissions. |
| Video buffers while sites become slow | Check Jellyfin's transcode reason, CPU load, disk activity, and home upload capacity; reduce the overnight quota or schedule Immich's heavy jobs separately. |
| Local HTTP works but public HTTPS does not | Check the new hostname's DNS, existing router forwards, Nginx config, certificate issuance, and a real cellular test. A HEAD response alone is not an end-to-end playback check. |
| Immich upload appears successful | Open the uploaded photo/video and verify backup coverage; container status by itself does not establish either. |

For a produced movie, inspect its streams and duration:

```bash
OUTPUT='/srv/media/movies/Movie Name (year)/Movie Name (year).mp4' # Select a completed output.
ffprobe -v error -show_entries format=duration,size:stream=codec_type,codec_name,width,height,channels -of json "$OUTPUT" # Expect H.264 video, AAC audio, and approximately the source runtime.
```

Updates are deliberate maintenance work. Read Immich's release notes, back up files and its database, then update the release's Compose files and images together; do not blindly redownload `.env` over your working credentials. The existing website uptime also depends on leaving CPU/RAM and disk capacity for SAS and David.

## Official References

- [Ubuntu disk formatting](https://help.ubuntu.com/stable/ubuntu-help/disk-format.html.en)
- [Western Digital filesystem guidance](https://support-en.wd.com/app/answers/detailweb/a_id/20821)
- [MakeMKV downloads](https://www.makemkv.com/download/) and [current beta key thread](https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053)
- [HandBrake official presets](https://handbrake.fr/docs/en/latest/technical/official-presets.html), [CLI options](https://handbrake.fr/docs/en/latest/cli/command-line-reference.html), and [quality guidance](https://handbrake.fr/docs/en/latest/workflow/adjust-quality.html)
- [Jellyfin Ubuntu/Linux installation](https://jellyfin.org/docs/general/installation/linux/) and [Nginx reverse proxy](https://jellyfin.org/docs/general/networking/nginx/)
- [Immich quick start](https://docs.immich.app/overview/quick-start/) and [storage requirements](https://docs.immich.app/install/requirements/)
- [Tailscale Linux install](https://tailscale.com/docs/install/linux) and [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
