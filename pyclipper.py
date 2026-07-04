import re
import json
import os
import sys
import subprocess
import urllib.request
import urllib.error
import ssl
from datetime import timedelta

# pastel color codes (256-color)
P = {
    "pink":  "\033[38;5;218m",
    "blue":  "\033[38;5;153m",
    "purple": "\033[38;5;183m",
    "peach": "\033[38;5;223m",
    "mint":  "\033[38;5;157m",
    "coral": "\033[38;5;210m",
    "gray":  "\033[38;5;250m",
    "reset": "\033[0m",
}

def p(*args, color="reset", sep=" ", **kwargs):
    c = P.get(color, P["reset"])
    text = sep.join(str(a) for a in args)
    print(f"{c}{text}{P['reset']}", **kwargs)

def sep(color="purple"):
    c = P.get(color, P["purple"])
    print(f"{c}{'=' * 60}{P['reset']}")


def fetch_page(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_json(html, var_name):
    pattern = re.escape(var_name) + r"\s*=\s*(\{.*?\});"
    match = re.search(pattern, html, re.DOTALL)
    if match:
        raw = match.group(1)
        raw_clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw)
        return json.loads(raw_clean)
    return None


def find_nested(obj, *keys):
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


def timestamp_to_seconds(ts):
    ts = ts.strip().replace(",", ".")
    parts = list(map(int, ts.split(":")))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return int(ts)


def seconds_to_timestamp(sec):
    return str(timedelta(seconds=int(sec)))


def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()[:80] or "clip"


def get_video_data(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    html = fetch_page(url)

    player = extract_json(html, "ytInitialPlayerResponse")
    data = extract_json(html, "ytInitialData")

    if not player:
        raise RuntimeError("Gagal mengambil data video (ytInitialPlayerResponse tidak ditemukan)")

    vd = player.get("videoDetails", {})
    mf = find_nested(player, "microformat", "playerMicroformatRenderer") or {}
    raw_str = json.dumps(data) if data else ""

    view_count = vd.get("viewCount", "N/A")
    like_count = None
    comment_count = None

    like_match = re.search(
        r'"segmentedLikeDislikeButtonViewModel".*?"LIKE"[^}]*"title"\s*:\s*"([^"]+)"',
        raw_str, re.DOTALL
    )
    if like_match:
        like_count = like_match.group(1)
    if not like_count:
        like_match = re.search(r'"iconName"\s*:\s*"LIKE"[^}]*"title"\s*:\s*"([^"]+)"', raw_str)
    if like_match:
        like_count = like_match.group(1)
    if not like_count:
        like_match = re.search(r'"title"\s*:\s*"([^"]+)"[^}]*"iconName"\s*:\s*"LIKE"', raw_str)
    if like_match:
        like_count = like_match.group(1)
    if like_count:
        like_count = json.loads(f'"{like_count}"') if "\\u" in like_count else like_count

    cc_match = re.search(
        r'engagement-panel-comments-section.*?"contextualInfo"\s*:\s*\{[^}]*"runs"\s*:\s*\[\{"text"\s*:\s*"([^"]+)"',
        raw_str, re.DOTALL
    )
    if cc_match:
        comment_count = cc_match.group(1)
        comment_count = json.loads(f'"{comment_count}"') if "\\u" in comment_count else comment_count

    desc = vd.get("shortDescription", "")

    formats = player.get("streamingData", {}).get("formats", []) + \
              player.get("streamingData", {}).get("adaptiveFormats", [])
    resolutions = {}
    for f in formats:
        w = f.get("width")
        h = f.get("height")
        ql = f.get("qualityLabel")
        if w and h:
            label = ql or f"{w}x{h}"
            if label not in resolutions:
                resolutions[label] = f"{w}x{h}"

    publish_date = mf.get("publishDate", "")
    upload_date = mf.get("uploadDate", "")
    category = mf.get("category", "")
    is_live = vd.get("isLive", False)
    duration_sec = int(vd.get("lengthSeconds", 0))

    sorted_labels = sorted(
        resolutions.keys(),
        key=lambda x: int(resolutions[x].split("x")[1])
    )

    return {
        "id": video_id,
        "title": vd.get("title", ""),
        "channel": vd.get("author", ""),
        "views": view_count,
        "likes": like_count,
        "comments": comment_count,
        "description": desc,
        "duration_sec": duration_sec,
        "duration_str": str(timedelta(seconds=duration_sec)),
        "publish_date": (publish_date or upload_date)[:10],
        "category": category,
        "is_live": is_live,
        "resolutions": resolutions,
        "resolution_labels": sorted_labels,
    }


def print_video_info(info):
    sep()
    p(f"  JUDUL     : {info['title']}", color="blue")
    p(f"  CHANNEL   : {info['channel']}", color="blue")
    p(f"  DURASI    : {info['duration_str']}", color="blue")
    p(f"  PUBLISH   : {info['publish_date']}", color="blue")
    p(f"  KATEGORI  : {info['category']}", color="blue")
    p(f"  LIVE      : {'Ya' if info['is_live'] else 'Tidak'}", color="blue")
    sep()
    p(f"  VIEWS     : {info['views']}", color="blue")
    p(f"  LIKES     : {info.get('likes') or 'N/A'}", color="blue")
    p(f"  COMMENTS  : {info.get('comments') or 'N/A'}", color="blue")
    sep()


def strip_md(line):
    return re.sub(r'^\s*[#*\-]+\s*|^\s*\d+\.\s*|\*', '', line).strip()


def parse_segments(text):
    segments = []
    lines = text.strip().split("\n")

    ts_pattern = re.compile(
        r'(?:(?:Perkiraan timestamp|Jam|Waktu|Timestamp)\s*[:\.]\s*)?'
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:[-–—]+|sampai|to|sd|ke)\s*'
        r'(\d{1,2}:\d{2}(?::\d{2})?)',
        re.IGNORECASE
    )

    current = {"start": None, "end": None, "title": "", "reason": "", "style": "", "caption": ""}

    for raw in lines:
        line = strip_md(raw)
        if not line:
            continue

        ts_match = ts_pattern.search(line)
        if ts_match:
            if current["start"] is not None and current["end"] is not None:
                segments.append(current)
            current = {
                "start": ts_match.group(1),
                "end": ts_match.group(2),
                "title": "", "reason": "", "style": "", "caption": ""
            }
            continue

        low = line.lower()
        if current["start"] is not None:
            if "judul" in low or "title" in low:
                current["title"] = re.sub(r'^[^:]*:\s*', '', line, count=1)
            elif "alasan" in low or "reason" in low:
                current["reason"] = re.sub(r'^[^:]*:\s*', '', line, count=1)
            elif "gaya" in low or "style" in low:
                current["style"] = re.sub(r'^[^:]*:\s*', '', line, count=1)
            elif "caption" in low:
                current["caption"] = re.sub(r'^[^:]*:\s*', '', line, count=1)
            elif not current["title"] and len(line) < 100:
                current["title"] = line

    if current["start"] is not None and current["end"] is not None:
        segments.append(current)

    if not segments:
        all_ts = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)', text)
        all_ts = list(dict.fromkeys(all_ts))
        for i in range(0, len(all_ts) - 1, 2):
            segments.append({
                "start": all_ts[i],
                "end": all_ts[i + 1],
                "title": f"Segmen {len(segments) + 1}",
                "reason": "", "style": "", "caption": ""
            })

    return segments


def suggest_clips(info):
    video_id = info["id"]
    try:
        from khazai import Client
    except ImportError:
        p("\n[!] khazai tidak terinstal. Install dengan: pip install khazai", color="coral")
        return []

    ai = Client(system=(
        "Kamu adalah editor video profesional. Tugasmu adalah menganalisis data video YouTube "
        "dan merekomendasikan segmen-segmen terbaik untuk dibuat klip pendek (short clip). "
        "Berikan rekomendasi berdasarkan judul, deskripsi, dan metadata yang diberikan. "
        "Jawab dalam Bahasa Indonesia."
    ))

    prompt = (
        f"Analisis video YouTube berikut dan rekomendasikan 3-5 segmen terbaik untuk dijadikan "
        f"klip pendek (Short/reels):\n\n"
        f"Judul: {info['title']}\n"
        f"Channel: {info['channel']}\n"
        f"Durasi: {info['duration_str']}\n"
        f"Views: {info['views']}\n"
        f"Likes: {info['likes']}\n"
        f"Deskripsi:\n{info['description'][:1500]}\n\n"
        f"Untuk setiap segmen, gunakan format:\n"
        f"Timestamp: mm:ss - mm:ss\n"
        f"Judul: <judul klip>\n"
        f"Alasan: <alasan>\n"
        f"Gaya: <gaya>\n"
        f"Caption: <teks caption siap posting, natural dan tidak lebay, tanpa emoji, tanpa hashtag>\n"
    )

    p("")
    sep()
    p("  MENDAPATKAN REKOMENDASI KLIP DARI AI...", color="purple")
    sep()

    try:
        reply = ai(prompt=prompt, memory=False)
        segments = parse_segments(reply)
        p("")
        for i, s in enumerate(segments, 1):
            p(f"  {i}. [{s['start']} - {s['end']}] {s['title']}", color="peach")
            if s['reason']:
                p(f"          Alasan: {s['reason']}", color="gray")
            if s['style']:
                p(f"            Gaya: {s['style']}", color="gray")
            if s['caption']:
                p(f"         Caption: {s['caption']}", color="pink")
            p("")

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        sep()
        p("  CAPTION PER SEGMEN (untuk sosmed):", color="purple")
        sep()
        for i, s in enumerate(segments, 1):
            caption = s['caption'] if s['caption'] else (
                f"{info['title']} — {s['title']} [{s['start']} - {s['end']}]\n"
                f"{s['reason']}\n{s['style']}"
            )
            caption += f"\n\nTonton video lengkapnya: {video_url}"
            p("")
            p(f"  --- Segmen {i} ---", color="purple")
            p(caption, color="pink")
        p("")
        return segments
    except Exception as e:
        p(f"[!] Gagal mendapatkan rekomendasi: {e}", color="coral")
        return []


def pick_resolution_tty(labels, resolutions):
    from InquirerPy import inquirer
    default = "1080p" if "1080p" in labels else labels[-1]
    choices = [{"name": f"{l:>8s}  ({resolutions[l]})", "value": l} for l in labels]
    return inquirer.select(message="Pilih resolusi:", choices=choices, default=default).execute()


def pick_resolution_plain(labels, resolutions):
    p("\nResolusi tersedia:", color="blue")
    for i, l in enumerate(labels, 1):
        p(f"  {i}. {l:>8s}  ({resolutions[l]})", color="peach")
    default = "1080p" if "1080p" in labels else labels[-1]
    default_idx = labels.index(default) + 1
    while True:
        c = input(f"Pilih nomor [{default_idx}]: ").strip()
        if not c:
            return default
        try:
            i = int(c) - 1
            if 0 <= i < len(labels):
                return labels[i]
        except ValueError:
            pass


def clip_video(video_id, start, end, title, resolution_label, resolutions):
    from tqdm import tqdm

    MAX_DUR = 60
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    base = sanitize_filename(title or "clip")
    out_path = os.path.join(output_dir, f"{base}_shorts.mp4")

    start_sec = timestamp_to_seconds(start)
    end_sec = timestamp_to_seconds(end)
    duration = end_sec - start_sec

    if duration > MAX_DUR:
        p(f"  [!] Segmen {duration}s melebihi maksimal {MAX_DUR}s, dipotong ke {MAX_DUR}s", color="coral")
        end_sec = start_sec + MAX_DUR
        duration = MAX_DUR

    height = resolutions[resolution_label].split("x")[1]
    temp_raw = os.path.join(output_dir, f"_temp_{video_id}.mp4")

    p(f"\n  >>> Download {start} - {seconds_to_timestamp(end_sec)} @{resolution_label}",
      color="blue", flush=True)

    try:
        proc = subprocess.run([
            "yt-dlp", "-f",
            f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
            "--merge-output-format", "mp4",
            "--progress",
            "--no-colors",
            "--no-warnings",
            "-o", temp_raw,
            f"https://www.youtube.com/watch?v={video_id}"
        ], check=True, timeout=600)
    except subprocess.CalledProcessError:
        p("  [!] Gagal download", color="coral")
        return None

    p("  >>> Convert ke portrait 1080x1920 ...", color="blue", flush=True)

    filter_complex = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
    )

    pbar2 = tqdm(total=duration, desc="Convert", unit="s", bar_format="{desc}: {n:.1f}/{total:.1f}s [{bar}]", ncols=60)

    try:
        proc = subprocess.Popen([
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-i", temp_raw,
            "-to", str(end_sec),
            "-vf", filter_complex,
            "-c:a", "aac", "-b:a", "192k",
            "-c:v", "libx264", "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path
        ], stderr=subprocess.PIPE, text=True)

        for line in proc.stderr or []:
            m = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
            if m:
                h, mnt, s, ms = map(int, m.groups())
                t = h * 3600 + mnt * 60 + s + ms / 100
                pbar2.n = min(t, duration)
                pbar2.refresh()

        proc.wait()
        pbar2.close()

        if proc.returncode != 0:
            p("  [!] Gagal konversi", color="coral")
            return None

    except Exception as e:
        pbar2.close()
        p(f"  [!] Gagal konversi: {e}", color="coral")
        return None
    finally:
        if os.path.exists(temp_raw):
            os.remove(temp_raw)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    p(f"  Done! {out_path} ({size_mb:.1f} MB)", color="mint")
    return out_path


def main():
    global p
    tty = sys.stdin.isatty()

    sep()
    p("  PYCLIPPER - YouTube Shorts/Reels Clipper", color="purple")
    sep()

    if tty:
        from InquirerPy import inquirer
        arg = inquirer.text(message="Masukkan URL YouTube atau video ID:").execute().strip()
    else:
        arg = input("Masukkan URL YouTube atau video ID: ").strip()

    if not arg:
        p("Tidak ada URL dimasukkan.", color="coral")
        return

    video_id = arg
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([a-zA-Z0-9_-]{11})", arg)
    if match:
        video_id = match.group(1)

    p(f"\nMemproses video ID: {video_id} ...", color="blue")

    try:
        info = get_video_data(video_id)
    except Exception as e:
        p(f"[ERROR] {e}", color="coral")
        return

    print_video_info(info)

    segments = suggest_clips(info)
    if not segments:
        p("Tidak ada segmen yang direkomendasikan.", color="coral")
        return

    if tty:
        from InquirerPy import inquirer
        choices = [{"name": f"[{s['start']} - {s['end']}] {s['title'][:60]}", "value": i} for i, s in enumerate(segments)]
        selected = inquirer.checkbox(message="Pilih segmen (spasi=pilih, enter=lanjut):", choices=choices).execute()
    else:
        p("\nSegmen:", color="blue")
        for i, s in enumerate(segments, 1):
            p(f"  {i}. [{s['start']} - {s['end']}] {s['title']}", color="peach")
        c = input("Pilih nomor (pisah koma, contoh 1,3): ").strip()
        if not c:
            selected = []
        else:
            selected = []
            for p in c.split(","):
                try:
                    idx = int(p.strip()) - 1
                    if 0 <= idx < len(segments):
                        selected.append(idx)
                except ValueError:
                    pass

    if not selected:
        p("Tidak ada segmen dipilih.", color="coral")
        return

    labels = info["resolution_labels"]
    if not labels:
        p("Tidak ada resolusi tersedia.", color="coral")
        return

    res_label = pick_resolution_tty(labels, info["resolutions"]) if tty else pick_resolution_plain(labels, info["resolutions"])

    p(f"\n  Resolusi dipilih: {res_label} ({info['resolutions'][res_label]})", color="blue")
    p(f"  Maksimal durasi per clip: 60 detik", color="gray")

    for idx in selected:
        seg = segments[idx]
        p(f"\n--- Memproses: {seg['title']} ({seg['start']} - {seg['end']}) ---", color="purple")
        clip_video(info["id"], seg["start"], seg["end"], seg["title"], res_label, info["resolutions"])


if __name__ == "__main__":
    main()
