# Home Media Server: Start Here

Your server already hosts SAS and David. Reuse its Nginx, HTTPS, SSH, firewall, and router setup. The 4 TB drive holds movies, shows, and Immich uploads; Immich's database stays on the internal SSD.

**Everyday flow:** insert a disc → copy it with MakeMKV → choose the movie or episodes → approve them for compression → watch the finished copies in Jellyfin.

MakeMKV keeps the disc's video quality. HandBrake makes smaller viewing copies. Jellyfin plays those copies. Immich is separate photo/video storage.

## 1. Set up once

Follow these in order, skipping anything you have already completed. Each link contains the exact installation commands and expected results.

| Step | What you are setting up |
|---|---|
| [Extra tools](media_server_reference.md#base-tools) | Download and disk tools needed by the later steps. |
| [4 TB drive](media_server_reference.md#drive) | Format the **empty external drive once**, mount it at `/srv/media`, and set permissions. Formatting erases the selected disk. |
| [MakeMKV and HandBrake](media_server_reference.md#software) | Programs for copying discs and compressing videos. |
| [Encoding queue](media_server_reference.md#queue) | Install the reusable script so you never need to paste its long encoder command for each movie. |
| [Jellyfin](media_server_reference.md#jellyfin) | Add Movies at `/srv/media/movies` and Shows at `/srv/media/shows`. |
| [Immich](media_server_reference.md#immich) | Store uploads on the external drive and its database on the SSD. |
| Remote access | [Tailscale](media_server_reference.md#private-access) for your own devices, or [public HTTPS](media_server_reference.md#public-access) for family without a VPN. |
| [Optional overnight service](media_server_reference.md#nightly) | Install the service, check one full movie, then optionally enable the nightly timer. |

The service commands below require that last setup step. Nothing runs automatically until you enable its timer. These instructions target Ubuntu 22.04 and ordinary DVD/Blu-ray SDR movies; UHD/HDR needs separate settings. [Jellyfin versus Plex](media_server_reference.md#plex) is also in the reference.

## 2. Add a movie

Insert the disc and replace `Movie Name (year)` with the real title:

```bash
DISC_DIR='/srv/media/rips/movies/Movie Name (year)' # Choose where this disc's original files will go.
mkdir -p "$DISC_DIR" # Create that folder.
makemkvcon info disc:0 # List the titles on the disc.
makemkvcon mkv disc:0 all "$DISC_DIR" # Copy the titles; wait for this to finish successfully.
ls -lh "$DISC_DIR" # See the copied filenames and their sizes.
```

> Expect copying progress, a success/failure count, and large MKV files. `all` includes extras, so choose the actual movie afterward. Stop if MakeMKV reports failures; the appearance of a file does not mean the copy is finished.

Use the filename shown by `ls` below. Watch a little of the source to confirm the movie, then inspect its audio tracks:

```bash
mv -i "$DISC_DIR/ACTUAL_RIPPED_FILENAME.mkv" "$DISC_DIR/Movie Name (year).mkv" # Give the chosen title a recognizable name.
INPUT="$DISC_DIR/Movie Name (year).mkv" # Select this completed movie.
HandBrakeCLI -i "$INPUT" --scan # Find the audio track containing the dialogue language you want.
```

The basic queue produces **stereo sound with no subtitles**. Check foreign-dialogue scenes before using it. Your surround-sound and subtitle preferences are still open in `0_QUESTIONS`.

When the movie and audio track are correct:

```bash
printf '1\n' > "$INPUT.audio" # Replace 1 with the desired audio-track number from the scan.
touch "$INPUT.ready" # Tell the queue this movie is complete and approved.
/usr/local/bin/media-encode --dry-run # Preview what the queue would encode.
```

> Expect `PLAN: source -> output`. `SKIP` means a finished file already exists. No planned files means nothing new is approved. Remove a movie's `.ready` file to withdraw it from future runs; do not change a source while it is queued or encoding.

For TV, use `/srv/media/rips/shows/Show Name/Season 01/Show Name - S01E01.mkv` and repeat the approval step for each episode. You still insert discs and identify episode order yourself.

## 3. Choose quality

Start with the existing example: **RF 20, encoder speed `fast`, 1080p maximum, AAC stereo at 160 kb/s**. Change one setting at a time and compare a [short sample](media_server_reference.md#samples) on your TV before encoding a whole collection.

| Setting | Useful choices | What changes |
|---|---|---|
| Quality (`RF`) | Compare 18, 20, 22, 24 | Lower numbers usually give larger, clearer copies; higher numbers usually give smaller copies with more detail lost. RF is not a percentage. |
| Encoder speed (`ENCODER_PRESET`) | `fast`, `medium`, `slow` | Slower spends more CPU time improving compression efficiency. Compare size and appearance; savings vary. |
| Audio (`AUDIO_KBPS`) | 128, 160, 192, 256 kb/s | Higher values give audio more space. Increasing bitrate does not restore surround sound to a stereo copy. |
| CPU limit (`CPUQuota`) | 100% or 200% as examples | Roughly one or two logical CPUs' worth of processing time. Lower limits leave more capacity for your websites but take longer. |
| Nightly runtime (`RuntimeMaxSec`) | Example: `8h` | Limits how long one run can work. An interrupted movie starts over next time. |

RF 20 is a useful starting point, but your source, TV, and viewing distance determine whether compression is noticeable. Check grain, dark scenes, and motion. Keep the original MKV until you are satisfied with the full result. The [full settings table](media_server_reference.md#tuning) covers supported ranges, resolution, frame rate, codecs, subtitles, memory, and disk space.

To change the installed service's settings, stop any active encode first:

```bash
sudo systemctl stop media-encode.service # Stop the current job before changing settings.
sudo nano /etc/systemd/system/media-encode.service # Edit RF/speed/audio on Environment=, or the resource limits below it.
sudo systemctl daemon-reload # Load the settings for the next run.
```

Existing MP4s are skipped even after changing quality. To redo a movie, first stop the service and move its old MP4 outside the Jellyfin library. Keep the source and its `.ready` marker.

## 4. Run now or overnight

After installing the [service and timer](media_server_reference.md#nightly), choose either:

```bash
sudo systemctl start --no-block media-encode.service # Run approved movies now; it continues if you disconnect SSH.
```

Or enable a recurring schedule:

```bash
sudo systemctl enable --now media-encode.timer # Turn on the nightly schedule, including after reboots.
systemctl list-timers --all media-encode.timer # Check when the next run will start.
```

> The example starts at **23:00 in the server's timezone**, runs for at most **eight hours**, and processes one movie at a time. Choose your preferred hours before enabling it. Edit `/etc/systemd/system/media-encode.timer` for the start time, then run `sudo systemctl daemon-reload` to load it.

The server must stay on and awake. Missed nights are skipped. Finished movies remain available; unfinished movies restart from the beginning next run. The queue keeps your original rips and moves only completed, basically validated MP4s into the Jellyfin folders. Inspect one full movie before trusting a large unattended batch.

To stop:

```bash
sudo systemctl disable --now media-encode.timer # Turn off future scheduled runs.
sudo systemctl stop media-encode.service # Also stop a job that is already running, if desired.
```

## 5. Check the result

```bash
sudo journalctl -u media-encode.service -n 40 --no-pager # Read recent progress, results, and errors.
df -h /srv/media # Check remaining storage.
```

| What you see | Meaning |
|---|---|
| `PLAN` followed by encoding progress | Working on an approved movie. |
| `DONE` | The finished MP4 was placed in Movies or Shows. Open it in Jellyfin. |
| `SKIP` | That output already exists. |
| `QUEUE FINISHED: completed=... failed=0` | The queue finished without a reported failure; watch the result to check quality and tracks. |
| `inactive (dead)` after success | Normal: the queue finished its work. |
| `FAILED`, `ERROR`, or a timeout | Read the preceding log lines. Fix the cause before relying on the next run. |

If a movie repeatedly times out, use faster settings or allow more time. If it is missing in Jellyfin, scan the library and check the movie name and folder. If it buffers, check Jellyfin's playback information for video transcoding and check your home's upload capacity for remote viewers.

For deeper checks, use the [troubleshooting reference](media_server_reference.md#checks). Back up irreplaceable Immich photos **and a consistent database dump** to a second location; the media drive itself is not a backup.
