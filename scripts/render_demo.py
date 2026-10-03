"""Assemble actual UI captures into a captioned demo; consensus waits are omitted.

Requires ffmpeg and Pillow. Pass --python via the bundled runtime if needed.
The manifest identifies each real capture and its observed outcome.
"""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "verification/demo-frames"
manifest = json.loads((FRAMES / "manifest.json").read_text())
segments = FRAMES / "rendered"
segments.mkdir(exist_ok=True)
font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
font = lambda n: ImageFont.truetype(font_path, n)
for i, item in enumerate(manifest):
    source = FRAMES / item["file"]
    if not source.is_file():
        raise FileNotFoundError(source)
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 1920, 112), fill="#101c25")
    draw.rectangle((0, 958, 1920, 1080), fill="#101c25")
    draw.text((45, 14), "Proof of Hunt | Actual contract execution", font=font(35), fill="white")
    draw.text((45, 61), "Captured UI snapshots of real transactions; consensus waits omitted.", font=font(24), fill="#a6bac9")
    draw.text((45, 975), f"{i+1:02d}  {item['title']}", font=font(31), fill="white")
    draw.text((45, 1025), item["detail"], font=font(23), fill="#a6bac9")
    title = segments / f"{i:02d}-caption.png"
    overlay.save(title)
    segment = segments / f"{i:02d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", str(source), "-loop", "1", "-i", str(title),
        "-filter_complex", "[0:v]scale=1840:824:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,pad=1920:1080:(ow-iw)/2:112:color=0x101c25[screen];[screen][1:v]overlay=0:0,scale=1920:1080:out_range=tv,setsar=1,format=yuv420p[out]",
        "-map", "[out]", "-t", str(item.get("seconds", 7)), "-r", "24",
        "-c:v", "libx264", "-color_range", "tv", "-preset", "fast", "-crf", "18", str(segment)], check=True)
concat = segments / "concat.txt"
concat.write_text("".join(f"file '{segments / f'{i:02d}.mp4'}'\n" for i in range(len(manifest))))
output = ROOT / "video/out/proof-of-hunt-execution.mp4"
output.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
    "-c", "copy", "-movflags", "+faststart", "-metadata", "title=Proof of Hunt - real Studio and Studionet verification", str(output)], check=True)
print(output)
