# Microkeebs Shorts Generator

Convert YouTube sound test videos into 9:16 vertical Shorts for TikTok/Reels/Shorts.

## Requirements

- Python 3.10+
- ffmpeg (`apt install ffmpeg`)
- yt-dlp (`pip install yt-dlp`)
- Pillow (`pip install Pillow`)
- YouTube cookies file (for age-restricted videos): `youtube.com_cookies.txt` (export from browser extension)

## Usage

### Single video

```bash
python3 render.py <input_video> <output.mp4> <specs.json> <video_id> [max_duration]
```

### Batch process

1. Export your builds data to `specs_sanitized.json` (same format as the site's `builds.json`)
2. Run the batch:

```bash
# All videos
python3 batch.py

# Starting from index N, max L videos
python3 batch.py 0 75
```

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `COOKIES` | `youtube.com_cookies.txt` | Path to yt-dlp cookies file |
| `PROXY` | *(none)* | SOCKS5 proxy for yt-dlp (e.g. `socks5h://...`) |
| `MAX_DUR` | `60` | Max Short duration in seconds |
| `START` | `0` | First entry index |
| `LIMIT` | *(none)* | Max entries to process |

### Output

- `output/` — All finished Shorts as `{video_id}_short.mp4`
- `batch_results.json` — Upload URLs and status per video
- Progress is saved after each video (safe to Ctrl+C)

## What it does

1. **Downloads** the YouTube video via yt-dlp (prefers WAV audio for quality)
2. **Detects the dominant shot** by sampling frames every 2s and clustering by color
3. **Renders** a 9:16 Short with:
   - Blurred video background filling the full frame
   - Main video centered edge-to-edge
   - Board name (cleaned, no maker info) as large title
   - Spec lines: Keycaps → Switches → Stabilizers → Plate → Mount → PCB
   - Semi-transparent dark background behind text
   - Social bar (YouTube, Instagram, TikTok, Website) anchored below the video
4. **Normalizes audio** to -14 LUFS (EBU R128, optimized for TikTok)
5. **Crops to 60s max** (trims from the end)
6. **Compresses** and saves locally + uploads to tmpfiles.org
