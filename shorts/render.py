#!/usr/bin/env python3
"""
Render 9:16 Short v7.
- Text moved down, tighter line spacing, reduced tracking
- Semi-transparent black background behind text block
- All font sizes +6px
"""

import json, subprocess, sys, os, re
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

INPUT = sys.argv[1]
OUTPUT = sys.argv[2]
SPECS_JSON = sys.argv[3]
VIDEO_ID = sys.argv[4]
MAX_DUR = int(sys.argv[5]) if len(sys.argv) > 5 else 60

W, H = 1080, 1920
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(SCRIPT_DIR, "fonts", "GSFBold700.ttf")
FONT_MEDIUM = os.path.join(SCRIPT_DIR, "fonts", "GSFMedium500.ttf")
FONT_REGULAR = os.path.join(SCRIPT_DIR, "fonts", "GoogleSansFlex-Regular.ttf")

def run(cmd, timeout=30):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)

def run_ok(cmd, timeout=30):
    r = run(cmd, timeout)
    if r.returncode != 0:
        print(f"FAIL: {cmd}\n{r.stderr[-500:]}")
        sys.exit(1)
    return r.stdout.strip()

def get_duration(path):
    out = run_ok(f'ffprobe -v quiet -print_format json -show_format "{path}"')
    return float(json.loads(out)['format']['duration'])

def get_resolution(path):
    out = run_ok(f'ffprobe -v quiet -print_format json -show_streams "{path}"')
    for s in json.loads(out)['streams']:
        if s['codec_type'] == 'video':
            return s['width'], s['height']
    return 1920, 1080

def find_dominant_shot(input_path, duration):
    os.makedirs('/tmp/shot_frames', exist_ok=True)
    for f in os.listdir('/tmp/shot_frames'):
        os.unlink(f'/tmp/shot_frames/{f}')

    t = 3.0
    idx = 0
    timestamps = []
    color_sigs = []

    while t < duration - 1:
        path = f'/tmp/shot_frames/f{idx:03d}.jpg'
        r = run(f'ffmpeg -y -ss {t:.2f} -i "{input_path}" -frames:v 1 '
                f'-q:v 2 -vf "scale=160:120" "{path}"', timeout=10)
        if r.returncode == 0 and os.path.exists(path):
            try:
                img = Image.open(path).convert('RGB')
                w, h = img.size
                hw, hh = w // 2, h // 2
                quads = []
                for y0, x0 in [(0, 0), (0, hw), (hh, 0), (hh, hw)]:
                    crop = img.crop((x0, y0, x0 + hw, y0 + hh))
                    pixels = list(crop.getdata())
                    avg = tuple(int(sum(c) / len(c)) for c in zip(*pixels))
                    quads.extend(avg)
                timestamps.append(t)
                color_sigs.append(quads)
            except:
                pass
        t += 2.0
        idx += 1

    if len(color_sigs) < 3:
        return 2.0, min(duration, MAX_DUR)

    THRESHOLD = 45
    clusters = [0]
    centers = [list(color_sigs[0])]

    for i in range(1, len(color_sigs)):
        best_ci, best_d = 0, float('inf')
        for ci, cc in enumerate(centers):
            d = sum((a - b) ** 2 for a, b in zip(color_sigs[i], cc)) ** 0.5
            if d < best_d:
                best_d = d
                best_ci = ci
        if best_d < THRESHOLD:
            clusters.append(best_ci)
            n = sum(1 for c in clusters if c == best_ci)
            for j in range(len(centers[best_ci])):
                centers[best_ci][j] = (centers[best_ci][j] * (n - 1) + color_sigs[i][j]) / n
        else:
            clusters.append(len(centers))
            centers.append(list(color_sigs[i]))

    counts = Counter(clusters)
    dominant = counts.most_common(1)[0][0]
    dom_times = [timestamps[i] for i in range(len(clusters)) if clusters[i] == dominant]

    start_t = max(0, dom_times[0] - 1)
    end_t = min(duration, dom_times[-1] + 1)

    print(f"Frames sampled: {len(color_sigs)}, Clusters: {len(set(clusters))}")
    print(f"Dominant shot: {start_t:.1f}s - {end_t:.1f}s ({len(dom_times)} frames)")

    return start_t, end_t

def clean_board_name(raw):
    name = raw.strip()
    name = re.sub(r'\s*\(.*?\)\s*', ' ', name)
    name = re.sub(r'\s+by\s+\S.*$', '', name, flags=re.IGNORECASE)
    name = ' '.join(name.split())
    return name

def format_specs(s):
    keyboard = s.get('title', s.get('Keyboard', s.get('Case', 'Unknown')))
    keycaps = s.get('Keycaps', '')
    switches = s.get('Switches', '')
    lube = s.get('Lube', '')
    stabs = s.get('Stabilizers', s.get('Stabs', ''))
    mount = s.get('Mount', '')
    plate = s.get('Plate', '')
    pcb = s.get('PCB', '')
    films = s.get('Films', '')
    springs = s.get('Springs', '')
    others = s.get('Others', '')

    sw_display = switches
    if lube and switches:
        sw_display = f"{switches} (lubed)"
    elif lube:
        sw_display = f"Lubed ({lube})"

    lines = []
    # Title
    lines.append((None, clean_board_name(keyboard)))

    # NEW ORDER: Keycaps, Switches, Stabilizers, Plate, Mount, PCB
    if keycaps:     lines.append(("Keycaps", keycaps))
    if sw_display:  lines.append(("Switches", sw_display))
    if stabs:       lines.append(("Stabilizers", stabs))
    if plate:       lines.append(("Plate", plate))
    if mount:       lines.append(("Mount", mount))
    
    # PCB includes Others
    pcb_display = pcb
    if others and others.strip() and others.strip() != '-':
        pcb_display = f"{pcb}, {others.strip()}" if pcb else others.strip()
    
    if pcb_display: lines.append(("PCB", pcb_display))

    return lines
def truncate(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    while len(text) > 1 and draw.textlength(text + "\u2026", font=font) > max_width:
        text = text[:-1]
    return text + "\u2026"

def render_text_overlay(spec_lines, output_path, main_video_bottom=H):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Font sizes: +6px from v6
    title_size = 62
    label_size = 36
    value_size = 36

    # Layout
    y = 200  # moved down from 70
    line_h_title = 72  # tighter
    line_h_spec = 42   # tighter (was 46)
    pad_x = 80  # reduced tracking via tighter max_width

    # First pass: measure total block height for background
    total_h = 0
    for label, value in spec_lines:
        total_h += line_h_title if label is None else line_h_spec
    total_h += 30  # vertical padding for bg

    # Draw semi-transparent black background
    bg_y = y - 15
    bg_h = total_h
    bg_x = 40
    bg_w = W - 80
    draw.rounded_rectangle(
        [bg_x, bg_y, bg_x + bg_w, bg_y + bg_h],
        radius=16,
        fill=(0, 0, 0, 140)
    )

    for label, value in spec_lines:
        if label is None:
            font = ImageFont.truetype(FONT_BOLD, title_size)
            safe = truncate(draw, value, font, W - pad_x * 2)
            bbox = draw.textbbox((0, 0), safe, font=font)
            tw = bbox[2] - bbox[0]
            x = (W - tw) // 2
            # Heavy shadow
            for dx, dy, alpha in [(3, 3, 220), (2, 2, 240)]:
                draw.text((x + dx, y + dy), safe, font=font, fill=(0, 0, 0, alpha))
            draw.text((x, y), safe, font=font, fill=(255, 255, 255, 255))
            y += line_h_title
        else:
            font_label = ImageFont.truetype(FONT_BOLD, label_size)
            font_value = ImageFont.truetype(FONT_REGULAR, value_size)

            label_text = f"{label}: "
            label_width = draw.textlength(label_text, font=font_label)
            value_text = truncate(draw, value, font_value, W - pad_x * 2 - label_width)

            total_width = label_width + draw.textlength(value_text, font=font_value)
            x = (W - total_width) // 2

            draw.text((x + 2, y + 2), label_text, font=font_label, fill=(0, 0, 0, 200))
            draw.text((x + label_width + 2, y + 2), value_text, font=font_value, fill=(0, 0, 0, 200))
            draw.text((x, y), label_text, font=font_label, fill=(255, 255, 255, 255))
            draw.text((x + label_width, y), value_text, font=font_value, fill=(255, 255, 255, 230))
            y += line_h_spec

    img.save(output_path)
    print(f"Text overlay: {output_path} ({os.path.getsize(output_path)/1024:.0f} KB, {len(spec_lines)} lines)")

    # === Social media bar just under main footage ===
    draw_social_bar(output_path, output_path, main_video_bottom)


def draw_social_bar(image_path, output_path, anchor_y=H):
    """Draw social media icons + handles. Positioned just below main footage."""
    img = Image.open(image_path).convert('RGBA')
    draw = ImageDraw.Draw(img)

    icon_dir = os.path.join(SCRIPT_DIR, "icons")
    icon_size = 40
    font_handle = ImageFont.truetype(FONT_REGULAR, 24)

    accounts = [
        ("youtube", "@microkeebs"),
        ("instagram", "@microkeebs"),
        ("tiktok", "@microkeebs"),
        ("globe", "microkeebs.micr.dev"),
    ]

    # Measure total width
    spacing = 36
    icon_text_gap = 10
    total_w = 0
    item_widths = []
    for icon_name, handle in accounts:
        icon_path = os.path.join(icon_dir, f"{icon_name}.png")
        iw = icon_size
        hw = draw.textlength(handle, font=font_handle)
        item_w = iw + icon_text_gap + hw
        item_widths.append(item_w)
        total_w += item_w
    total_w += spacing * (len(accounts) - 1)

    # Draw semi-transparent black background
    bar_h = 80
    bar_y = int(anchor_y) + 16  # just below main footage
    bar_x = (W - total_w) // 2 - 30
    bar_w = total_w + 60
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=14,
        fill=(0, 0, 0, 130)
    )

    # Draw each icon + handle
    x = (W - total_w) // 2
    cy = bar_y + (bar_h - icon_size) // 2

    for i, (icon_name, handle) in enumerate(accounts):
        icon_path = os.path.join(icon_dir, f"{icon_name}.png")
        if os.path.exists(icon_path):
            icon_img = Image.open(icon_path).convert('RGBA').resize((icon_size, icon_size), Image.LANCZOS)
            # Center icon vertically with text
            bbox = draw.textbbox((0, 0), handle, font=font_handle)
            text_h = bbox[3] - bbox[1]
            text_y = int(cy + (icon_size - text_h) // 2 - bbox[1])
            img.paste(icon_img, (int(x), int(cy)), icon_img)
            draw.text((int(x) + icon_size + icon_text_gap, text_y), handle, font=font_handle, fill=(255, 255, 255, 220))
        x += item_widths[i] + spacing

    img.save(output_path)

def render(input_path, output_path, spec_lines, start_t, end_t):
    src_w, src_h = get_resolution(input_path)
    render_start = start_t + 2.0
    clip_dur = end_t - render_start
    out_dur = min(clip_dur, MAX_DUR)

    scale = min(W / src_w, H / src_h)
    main_w = int(src_w * scale) & ~2
    main_h = int(src_h * scale) & ~2
    main_x = (W - main_w) // 2
    main_y = (H - main_h) // 2

    text_png = "/tmp/specs_overlay.png"
    render_text_overlay(spec_lines, text_png, main_y + main_h)

    filterchain = (
        f"[0:v]split=2[bg_in][fg_in];"
        f"[bg_in]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"boxblur=6:3,"
        f"eq=brightness=-0.02[bg];"
        f"[fg_in]scale={main_w}:{main_h},"
        f"setsar=1[fg];"
        f"[bg][fg]overlay={main_x}:{main_y}[ov];"
        f"[ov][1:v]overlay=0:0[vout]"
    )

    audio_filter = "loudnorm=I=-14:TP=-1:LRA=11"
    filterchain_audio = filterchain + f";[0:a]{audio_filter}[aout]"

    cmd = (
        f'ffmpeg -y -ss {render_start:.2f} -i "{input_path}" '
        f'-i "{text_png}" '
        f'-filter_complex "{filterchain_audio}" '
        f'-map "[vout]" -map "[aout]" '
        f'-c:v libx264 -preset ultrafast -crf 26 '
        f'-pix_fmt yuv420p '
        f'-c:a aac -b:a 192k -ar 44100 '
        f'-movflags +faststart '
        f'-t {out_dur} '
        f'"{output_path}"'
    )

    print(f"Source: {src_w}x{src_h}, main: {main_w}x{main_h} at ({main_x},{main_y})")
    print(f"Shot: {start_t:.1f}s - {end_t:.1f}s, render from {render_start:.1f}s")
    print(f"Output: {out_dur:.1f}s")
    print("Rendering...")

    r = run(cmd, timeout=600)
    if r.returncode != 0:
        print(f"FFmpeg error:\n{r.stderr[-1500:]}")
        sys.exit(1)

    fsize = os.path.getsize(output_path)
    print(f"Done: {output_path} ({fsize/1024/1024:.1f} MB)")

def main():
    with open(SPECS_JSON) as f:
        all_specs = json.load(f)

    entry = next((e for e in all_specs if e['id'] == VIDEO_ID), None)
    if not entry:
        print(f"Video {VIDEO_ID} not found")
        sys.exit(1)

    lines = format_specs(entry['specs'])
    print("Specs:")
    for label, value in lines:
        name = label or "Title"
        print(f"  {name}: {value}")

    duration = get_duration(INPUT)
    print(f"Duration: {duration:.1f}s\n")

    print("Finding dominant shot...")
    start_t, end_t = find_dominant_shot(INPUT, duration)

    print()
    render(INPUT, OUTPUT, lines, start_t, end_t)

if __name__ == '__main__':
    main()
