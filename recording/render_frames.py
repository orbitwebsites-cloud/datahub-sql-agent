"""
Builds DEMO_VIDEO.mp4 with ZERO live screen capture.

Pipeline:
  1. Actually run the CLI/tests as subprocesses and capture their real
     stdout (no hand-typed/fabricated output).
  2. Render each beat as a sequence of terminal-styled PNG frames with
     Pillow (a title/question banner, then the real output revealed a
     few lines at a time, then a held final frame).
  3. Assemble the frames into a silent video with ffmpeg's image2/concat
     demuxer (not gdigrab, not any screen capture).
  4. Mux the already-generated local-TTS narration (narration_master.wav,
     built earlier by build_audio.sh from durations.json) under the video.

This never touches the real screen, so there is no risk of capturing
unrelated windows/content — every pixel in the output comes from text
this script rendered itself.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FRAMES_DIR = os.path.join(HERE, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

W, H = 1280, 720
BG = (12, 12, 16)
FG = (222, 222, 222)
CYAN = (86, 214, 214)
GREEN = (120, 200, 120)
YELLOW = (230, 190, 90)
RED = (230, 110, 100)
DIM = (130, 130, 140)

FONT_PATH = r"C:\Windows\Fonts\CascadiaMono.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\consolab.ttf"
FONT_SIZE = 15
LINE_HEIGHT = 20
MARGIN_X = 30
MARGIN_TOP = 24

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
try:
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, FONT_SIZE)
except OSError:
    font_bold = font


def run_capture(cmd, cwd=REPO_ROOT):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return (result.stdout or "") + (result.stderr or "")


def classify_line(line):
    stripped = line.strip()
    if stripped.startswith("=====") :
        return CYAN, font
    if stripped.startswith("Q:"):
        return CYAN, font_bold
    if "[FLAG]" in line or "highly unusual" in line:
        return RED, font
    if stripped.startswith("[nlsql]") or stripped.startswith("-> "):
        return DIM, font
    if "PASSED" in line:
        return GREEN, font
    if "FAILED" in line or "ERROR" in line:
        return RED, font
    if stripped.startswith("[") and "]" in stripped[:40]:
        return YELLOW, font_bold
    return FG, font


def wrap_line(line, max_chars=118):
    if len(line) <= max_chars:
        return [line]
    out = []
    while len(line) > max_chars:
        out.append(line[:max_chars])
        line = line[max_chars:]
    out.append(line)
    return out


def render_frame(lines, path, max_lines=33):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    visible = lines[-max_lines:] if len(lines) > max_lines else lines
    y = MARGIN_TOP
    for line in visible:
        color, use_font = classify_line(line)
        draw.text((MARGIN_X, y), line, fill=color, font=use_font)
        y += LINE_HEIGHT
    img.save(path)


def render_title_card(path, title_lines, subtitle=None):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    big_font = ImageFont.truetype(FONT_BOLD_PATH, 40)
    small_font = ImageFont.truetype(FONT_PATH, 20)
    y = H // 2 - (len(title_lines) * 52) // 2
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=big_font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), line, fill=CYAN, font=big_font)
        y += 58
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=small_font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y + 20), subtitle, fill=DIM, font=small_font)
    img.save(path)


class FrameSequence:
    def __init__(self):
        self.entries = []  # list of (path, duration)

    def add(self, path, duration):
        self.entries.append((path, duration))

    def total(self):
        return sum(d for _, d in self.entries)


SECTION_PAUSE_MARKERS = ("[Result]", "[Lineage]", "[Anomaly check]")


def build_beat_frames(seq, idx_prefix, banner, output_text, narration_duration, buffer_after):
    """Banner appears, output lines reveal a few at a time (pausing briefly at
    each [Result]/[Lineage]/[Anomaly check] section so the reader has time to
    actually read the number before it scrolls further), then hold on the
    full final frame for the remainder of the beat's narration + buffer."""
    all_lines = [banner, ""] + output_text.splitlines()
    wrapped = []
    for l in all_lines:
        wrapped.extend(wrap_line(l))

    chunk = 3
    reveal_step = 0.12
    section_pause = 1.4
    revealed_time = 0.0
    frame_i = 0
    for i in range(0, len(wrapped), chunk):
        shown = wrapped[: i + chunk]
        fpath = os.path.join(FRAMES_DIR, f"{idx_prefix}_{frame_i:03d}.png")
        render_frame(shown, fpath)

        just_added = wrapped[i:i + chunk]
        hit_marker = any(any(m in l for m in SECTION_PAUSE_MARKERS) for l in just_added)
        dur = section_pause if hit_marker else reveal_step
        seq.add(fpath, dur)
        revealed_time += dur
        frame_i += 1

    # Final full frame (scrolled to the tail, matching what a real terminal
    # would show), held for the rest of narration + buffer.
    final_path = os.path.join(FRAMES_DIR, f"{idx_prefix}_final.png")
    render_frame(wrapped, final_path)
    hold = max(0.5, narration_duration + buffer_after - revealed_time)
    seq.add(final_path, hold)


def main():
    with open(os.path.join(HERE, "durations.json")) as f:
        durations = json.load(f)

    print("Running the real CLI/tests to capture actual output...")
    top_products_out = run_capture(["python", "cli.py", "top 5 products by revenue"])
    anomaly_out = run_capture(["python", "cli.py", "what was total revenue in electronics in may 2026"])
    tests_out = run_capture(["python", "-m", "pytest", "tests/", "-v"])

    seq = FrameSequence()

    # Pre-roll / title card
    title_path = os.path.join(FRAMES_DIR, "000_title.png")
    render_title_card(
        title_path,
        ["METADATA-AWARE SQL AGENT"],
        "Built for the DataHub Agent Hackathon  |  Zero paid API keys required",
    )
    seq.add(title_path, 5.0)

    # Beat 1 - intro (title card held a bit longer while narration plays)
    seq.add(title_path, durations["beat1_intro"] + 2)

    # Beat 2 - normal question
    build_beat_frames(
        seq, "b2", "Q: top 5 products by revenue", top_products_out,
        durations["beat2_normal"], 8,
    )

    # Beat 3 - the anomaly punchline
    build_beat_frames(
        seq, "b3", "Q: what was total revenue in electronics in may 2026", anomaly_out,
        durations["beat3_anomaly"], 12,
    )

    # Beat 4 - free/local banner
    free_path = os.path.join(FRAMES_DIR, "004_free.png")
    render_title_card(
        free_path,
        ["ZERO PAID API KEYS"],
        "NL-to-SQL: free local template engine  |  DataHub: open source, self-hosted",
    )
    seq.add(free_path, durations["beat4_free"] + 2)

    # Beat 5 - test suite
    build_beat_frames(seq, "b5", "Test suite: python -m pytest tests/ -v", tests_out, durations["beat5_close"], 5)

    # Closing card
    close_path = os.path.join(FRAMES_DIR, "999_close.png")
    render_title_card(
        close_path,
        ["Thanks for watching!"],
        "https://github.com/orbitwebsites-cloud/datahub-sql-agent",
    )
    seq.add(close_path, 3.0)

    # Write ffmpeg concat list
    list_path = os.path.join(HERE, "frames_list.txt")
    with open(list_path, "w") as f:
        for path, dur in seq.entries:
            rel = os.path.relpath(path, HERE).replace("\\", "/")
            f.write(f"file '{rel}'\nduration {dur:.3f}\n")
        # ffmpeg concat demuxer quirk: repeat the last file once more without a duration
        last_rel = os.path.relpath(seq.entries[-1][0], HERE).replace("\\", "/")
        f.write(f"file '{last_rel}'\n")

    print(f"Total frame-sequence duration: {seq.total():.2f}s")
    print(f"Wrote {list_path} with {len(seq.entries)} entries.")


if __name__ == "__main__":
    main()
