"""Assemble the recorded frames and the narration into demo/out/raah-demo.mp4.

Run from the repo root after `node demo/record.mjs`:  api/.venv/Scripts/python -m demo.build
ffmpeg comes from $FFMPEG, the imageio-ffmpeg package, or the npm package @ffmpeg-installer/ffmpeg
installed in demo/ (`cd demo && npm install`).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEMO = Path(__file__).parent
OUT = DEMO / "out"


def find_ffmpeg() -> str:
    if os.getenv("FFMPEG"):
        return os.environ["FFMPEG"]
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    for folder in (DEMO / "node_modules" / "@ffmpeg-installer").glob("*-*"):
        for name in ("ffmpeg.exe", "ffmpeg"):
            if (folder / name).exists():
                return str(folder / name)
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    sys.exit("ffmpeg not found: run `cd demo && npm install` or set FFMPEG")


def main() -> None:
    ffmpeg = find_ffmpeg()
    tl = json.loads((OUT / "timeline.json").read_text(encoding="utf-8"))
    frames, events = tl["frames"], sorted(tl["events"], key=lambda e: e["t"])
    t0 = frames[0]["t"]
    total = tl["end"] - t0

    # Video: frames arrive only when the screen changes, so each lasts until the next.
    lines = []
    for i, f in enumerate(frames):
        nxt = frames[i + 1]["t"] if i + 1 < len(frames) else tl["end"]
        lines.append(f"file 'frames/{f['file']}'\nduration {max(nxt - f['t'], 0.001):.4f}")
    lines.append(f"file 'frames/{frames[-1]['file']}'")
    (OUT / "frames.txt").write_text("\n".join(lines), encoding="utf-8")

    # Audio: the clips never overlap, so lay them end to end with exact silences between.
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "frames.txt")]
    filters, parts, cursor, n = [], [], 0.0, 0
    fmt = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    for k, e in enumerate(events):
        cmd += ["-i", str(OUT / e["file"])]
        start = e["t"] - t0
        if start > cursor:
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{start - cursor:.3f},{fmt}[s{n}]")
            parts.append(f"[s{n}]")
            n += 1
        chain = f"[{k + 1}:a]{fmt}"
        if e.get("maxlen"):
            m = e["maxlen"]
            chain += f",atrim=0:{m},afade=t=out:st={m - 1.2}:d=1.2"
        filters.append(chain + f",asetpts=N/SR/TB[c{k}]")
        parts.append(f"[c{k}]")
        dur = float(subprocess.run([ffmpeg, "-i", str(OUT / e["file"])], capture_output=True, text=True).stderr
                    .split("Duration: ")[1].split(",")[0].split(":")[-1]) if True else 0
        cursor = start + (min(dur, e["maxlen"]) if e.get("maxlen") else dur)
    filters.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{max(total - cursor, 0.1):.3f},{fmt}[s{n}]")
    parts.append(f"[s{n}]")
    filters.append(f"{''.join(parts)}concat=n={len(parts)}:v=0:a=1[aout]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "0:v", "-map", "[aout]",
        "-vf", "fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total:.2f}", "-movflags", "+faststart",
        str(OUT / "raah-demo.mp4"),
    ]
    r = subprocess.run(cmd, cwd=OUT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-3000:])
    size = (OUT / "raah-demo.mp4").stat().st_size / 1e6
    print(f"wrote {OUT / 'raah-demo.mp4'}  ({total:.0f}s, {size:.1f} MB, {len(frames)} frames, {len(events)} audio clips)")


if __name__ == "__main__":
    main()
