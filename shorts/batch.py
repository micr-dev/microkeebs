#!/usr/bin/env python3
"""
Batch convert all Microkeebs sound test videos into Shorts.

Usage: python3 batch.py [--start N] [--limit N]

Each video: download -> render -> compress -> upload to catbox -> report link
One video at a time to avoid disk bloat.
"""

import json, subprocess, sys, os, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
RENDER_SCRIPT = SCRIPT_DIR / "render.py"
SPECS = SCRIPT_DIR / "specs_sanitized.json"
COOKIES = os.environ.get("COOKIES", "youtube.com_cookies.txt")
PROXY = os.environ.get("PROXY", "")
WORK_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "mk_batch"
MAX_DUR = int(os.environ.get("MAX_DUR", "60"))

os.makedirs(WORK_DIR, exist_ok=True)


def run(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r


def get_duration(path):
    out = run(f'ffprobe -v quiet -print_format json -show_format "{path}"')
    if out.returncode == 0:
        return float(json.loads(out.stdout)["format"]["duration"])
    return 0


def download_video(video_id, url, output_path):
    """Download via yt-dlp with proxy + cookies. Returns True on success."""
    proxy_arg = f"--proxy {PROXY}" if PROXY else ""
    cmd = (
        f'yt-dlp {proxy_arg} --cookies {COOKIES} '
        f'-f "bestaudio[ext=wav]+bestvideo[height<=1080][ext=mp4]/best[height<=1080][ext=mp4]/best" '
        f'-o "{output_path}.%(ext)s" --no-playlist "{url}"'
    )
    r = run(cmd, timeout=300)
    if r.returncode != 0:
        print(f"  [ERR] yt-dlp failed: {r.stderr[-300:]}")
        return False

    # Find the actual downloaded file
    base = str(output_path)
    for ext in ["mp4", "webm", "mkv", "avi"]:
        p = f"{base}.{ext}"
        if os.path.exists(p) and os.path.getsize(p) > 1024 * 1024:
            if p != output_path:
                os.rename(p, output_path)
            return True
    return False


def render_video(input_path, output_path, video_id):
    cmd = f"python3 {RENDER_SCRIPT} {input_path} {output_path} {SPECS} {video_id} {MAX_DUR}"
    r = run(cmd, timeout=600)
    if r.returncode != 0:
        print(f"  [ERR] render failed: {r.stderr[-500:]}")
        return False
    return True


OUTPUT_DIR = SCRIPT_DIR / "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def compress_upload(input_path, output_path, video_id):
    """Compress to ~15MB, save locally, and upload."""
    local_path = OUTPUT_DIR / f"{video_id}_short.mp4"
    r = run(
        f'ffmpeg -y -i "{input_path}" '
        f'-c:v libx264 -preset ultrafast -crf 30 '
        f'-c:a aac -b:a 96k -movflags +faststart '
        f'"{local_path}"',
        timeout=300
    )
    if r.returncode != 0:
        print(f"  [ERR] compress failed: {r.stderr[-300:]}")
        return None

    fsize = os.path.getsize(local_path) / 1024 / 1024
    print(f"  Saved locally: {local_path.name} ({fsize:.1f} MB)")

    # Upload to catbox
    r = run(f'curl -F "reqtype=fileupload" -F "fileToUpload=@{local_path}" '
            f'https://catbox.moe/user/api.php', timeout=120)
    if r.returncode != 0 or "Invalid uploader" in r.stdout or "error" in r.stdout.lower():
        # Try tmpfiles
        r2 = run(
            f'curl -F "file=@{local_path}" https://tmpfiles.org/api/v1/upload',
            timeout=120
        )
        if r2.returncode == 0 and "url" in r2.stdout:
            data = json.loads(r2.stdout)
            url = data["data"]["url"].replace("http:", "https:")
            return url
        print(f"  [WARN] upload failed, file saved locally")
        return str(local_path)

    url = r.stdout.strip()
    return url


def process_entry(entry, index, total):
    video_id = entry["id"]
    url = entry["youtubeUrl"]
    specs = entry.get("specs", {})

    title = specs.get("title", video_id)
    print(f"\n[{index}/{total}] {title} ({video_id})")

    video_path = WORK_DIR / f"{video_id}.mp4"
    short_path = WORK_DIR / f"{video_id}_short.mp4"

    # Skip if already done
    if short_path.exists():
        print(f"  [SKIP] Already rendered")
        return True

    # Step 1: Download
    print(f"  [1/3] Downloading...")
    if not download_video(video_id, url, video_path):
        return False

    dur = get_duration(video_path)
    print(f"  Duration: {dur:.1f}s, Size: {os.path.getsize(video_path)/1024/1024:.1f} MB")

    # Step 2: Render
    print(f"  [2/3] Rendering...")
    if not render_video(str(video_path), str(short_path), video_id):
        return False

    short_size = os.path.getsize(short_path) / 1024 / 1024
    print(f"  Rendered: {short_size:.1f} MB")

    # Step 3: Compress + Upload
    print(f"  [3/3] Compressing + uploading...")
    dl_url = compress_upload(short_path, short_path.with_suffix(".compressed.mp4"), video_id)

    # Clean up source
    os.unlink(video_path)
    os.unlink(short_path)

    if dl_url:
        print(f"  [OK] {dl_url}")
        return dl_url
    else:
        print(f"  [FAIL] Upload failed")
        return None


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    with open(SPECS) as f:
        data = json.load(f)

    # Load previous results to avoid re-processing
    out = SCRIPT_DIR / "batch_results.json"
    prev_results = []
    if out.exists():
        with open(out) as f:
            prev_results = json.load(f)
    done_ids = set(r["id"] for r in prev_results if r.get("result"))

    results = list(prev_results)
    for i, entry in enumerate(data[start:], start=start):
        if limit and i >= start + limit:
            break

        # Skip already completed entries
        if entry["id"] in done_ids:
            print(f"\n[{i + 1}/{len(data)}] {entry.get('specs', {}).get('title', entry['id'])} - SKIP (already done)")
            continue

        dl_url = process_entry(entry, i + 1, len(data))
        results.append({
            "id": entry["id"],
            "title": entry.get("specs", {}).get("title", entry["id"]),
            "url": entry.get("youtubeUrl"),
            "result": dl_url,
        })

        # Save results after each entry so progress isn't lost on kill
        out = SCRIPT_DIR / "batch_results.json"
        with open(out, "w") as f:
            json.dump(results, f, indent=2)

        # Small delay between uploads
        time.sleep(2)

    print(f"\n\nBatch complete. {len([r for r in results if r['result']])}/{len(results)} succeeded.")
    print(f"Results saved to {out}")

    # Print failed ones
    failed = [r for r in results if not r["result"]]
    if failed:
        print("\nFailed:")
        for r in failed:
            print(f"  {r['id']}: {r['url']}")


if __name__ == "__main__":
    main()
