"""
Branded Hindi Motion-Graphics Video Renderer for My Admission Guru.
Renders crisp 1920x1080 (16:9 Horizontal) and 1080x1920 (9:16 Portrait) slides via
Playwright Chromium (perfect Devanagari font shaping) and compiles MP4s with FFmpeg.
"""

from __future__ import annotations

import base64
import html
import subprocess
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"


def _data_uri(path: Path, mime: str) -> str:
    if not path.is_file():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _build_slide_html(
    scene: dict[str, Any],
    meta: dict[str, Any],
    orientation: str,
    step_num: int,
    total_steps: int,
    logo_uri: str,
    mascot_uri: str,
) -> str:
    is_port = orientation == "portrait"
    w, h = (1080, 1920) if is_port else (1920, 1080)
    accent = meta.get("accent", "#dc2626")
    badge = meta.get("badge_short" if is_port else "badge_hi", "LIVE UPDATE")

    heading = html.escape(str(scene.get("heading", "")))
    subheading = html.escape(str(scene.get("subheading", "")))
    highlight = html.escape(str(scene.get("highlight", "")))

    # Build main card body based on scene kind
    body_html = ""
    rows = scene.get("rows") or []
    bullets = scene.get("bullets") or []

    if rows:
        tr_html = "".join(
            f'<div class="kv-row"><div class="kv-k">{html.escape(str(k))}</div>'
            f'<div class="kv-v">{html.escape(str(v))}</div></div>'
            for k, v in rows
        )
        body_html = f'<div class="kv-card">{tr_html}</div>'
    elif bullets:
        li_html = "".join(
            f'<div class="bul-item"><span class="bul-dot">{idx + 1}</span><span>{html.escape(str(b))}</span></div>'
            for idx, b in enumerate(bullets)
        )
        body_html = f'<div class="bul-card">{li_html}</div>'

    highlight_html = f'<div class="hl-pill">{highlight}</div>' if highlight else ""
    logo_img = f'<img class="logo" src="{logo_uri}" alt="Logo" />' if logo_uri else ""
    mascot_img = f'<img class="mascot" src="{mascot_uri}" alt="Guru" />' if mascot_uri else ""

    dots = "".join(
        f'<span class="step-dot {"active" if i == step_num else ""}"></span>'
        for i in range(total_steps)
    )

    return f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="utf-8" />
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@500;700;800;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: {w}px;
    height: {h}px;
    overflow: hidden;
    font-family: 'Noto Sans Devanagari', 'Nirmala UI', 'Mangal', sans-serif;
    background: radial-gradient(circle at 15% 15%, #172a56 0%, #09132b 58%, #040917 100%);
    color: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
  }}
  .bg-orb {{
    position: absolute;
    border-radius: 50%;
    filter: blur(110px);
    opacity: 0.28;
    pointer-events: none;
  }}
  .orb-1 {{ width: 520px; height: 520px; background: {accent}; top: -140px; right: -100px; }}
  .orb-2 {{ width: 480px; height: 480px; background: #f59e0b; bottom: -120px; left: -120px; }}

  /* Top Brand Bar */
  .topbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: { '48px 54px 24px' if is_port else '34px 64px 20px' };
    z-index: 2;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 18px;
  }}
  .logo {{
    width: { '78px' if is_port else '72px' };
    height: { '78px' if is_port else '72px' };
    border-radius: 18px;
    border: 3px solid rgba(255,255,255,0.25);
    background: #fff;
  }}
  .brand-txt strong {{
    display: block;
    font-size: { '34px' if is_port else '32px' };
    font-weight: 900;
    letter-spacing: 0.5px;
    color: #fff;
  }}
  .brand-txt span {{
    font-size: { '22px' if is_port else '20px' };
    color: #fbbf24;
    font-weight: 700;
  }}
  .badge {{
    background: {accent};
    color: #fff;
    padding: { '14px 26px' if is_port else '12px 28px' };
    border-radius: 999px;
    font-size: { '26px' if is_port else '24px' };
    font-weight: 800;
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    border: 2px solid rgba(255,255,255,0.25);
  }}

  /* Main Stage */
  .stage {{
    flex: 1;
    display: flex;
    flex-direction: { 'column' if is_port else 'row' };
    align-items: center;
    justify-content: center;
    gap: { '34px' if is_port else '48px' };
    padding: { '24px 56px 40px' if is_port else '10px 72px 24px' };
    z-index: 2;
  }}
  .content-col {{
    flex: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: { '26px' if is_port else '22px' };
  }}
  .hl-pill {{
    align-self: flex-start;
    background: linear-gradient(90deg, #f59e0b, #fbbf24);
    color: #111827;
    font-size: { '34px' if is_port else '28px' };
    font-weight: 900;
    padding: 12px 28px;
    border-radius: 14px;
    box-shadow: 0 12px 28px rgba(245, 158, 11, 0.35);
  }}
  h1 {{
    font-size: { '56px' if is_port else '54px' };
    line-height: 1.22;
    font-weight: 900;
    color: #ffffff;
    text-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}
  .sub {{
    font-size: { '30px' if is_port else '27px' };
    color: #93c5fd;
    font-weight: 700;
  }}

  .kv-card, .bul-card {{
    background: rgba(255, 255, 255, 0.08);
    border: 2px solid rgba(255, 255, 255, 0.16);
    border-radius: 26px;
    padding: { '28px 30px' if is_port else '24px 32px' };
    backdrop-filter: blur(12px);
    display: flex;
    flex-direction: column;
    gap: { '18px' if is_port else '14px' };
    box-shadow: 0 20px 50px rgba(0,0,0,0.35);
  }}
  .kv-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    padding-bottom: 14px;
    border-bottom: 1.5px solid rgba(255,255,255,0.12);
  }}
  .kv-row:last-child {{ border-bottom: 0; padding-bottom: 0; }}
  .kv-k {{
    font-size: { '28px' if is_port else '25px' };
    color: #cbd5e1;
    font-weight: 700;
    flex: 0 0 42%;
  }}
  .kv-v {{
    font-size: { '30px' if is_port else '27px' };
    color: #fef08a;
    font-weight: 800;
    text-align: right;
    flex: 1;
  }}

  .bul-item {{
    display: flex;
    align-items: flex-start;
    gap: 18px;
    font-size: { '30px' if is_port else '27px' };
    line-height: 1.4;
    font-weight: 700;
    color: #f1f5f9;
  }}
  .bul-dot {{
    flex: none;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: {accent};
    color: #fff;
    display: grid;
    place-items: center;
    font-weight: 900;
    font-size: 24px;
  }}

  .mascot-wrap {{
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .mascot {{
    height: { '340px' if is_port else '460px' };
    width: auto;
    filter: drop-shadow(0 18px 36px rgba(0,0,0,0.45));
  }}

  /* Bottom Ticker */
  .footer {{
    background: linear-gradient(90deg, #0f172a, #1e293b);
    border-top: 4px solid #fbbf24;
    padding: { '28px 54px 180px' if is_port else '20px 64px' };
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 2;
  }}
  .footer-cta {{
    font-size: { '30px' if is_port else '26px' };
    font-weight: 800;
    color: #fbbf24;
  }}
  .steps {{
    display: flex;
    gap: 10px;
  }}
  .step-dot {{
    width: 16px;
    height: 16px;
    border-radius: 999px;
    background: rgba(255,255,255,0.25);
  }}
  .step-dot.active {{
    width: 44px;
    background: #fbbf24;
  }}
</style>
</head>
<body>
  <div class="bg-orb orb-1"></div>
  <div class="bg-orb orb-2"></div>

  <header class="topbar">
    <div class="brand">
      {logo_img}
      <div class="brand-txt">
        <strong>MY ADMISSION GURU</strong>
        <span>myadmissionguru.com</span>
      </div>
    </div>
    <div class="badge">{html.escape(badge)}</div>
  </header>

  <main class="stage">
    <div class="content-col">
      {highlight_html}
      <h1>{heading}</h1>
      <div class="sub">{subheading}</div>
      {body_html}
    </div>
    <div class="mascot-wrap">
      {mascot_img}
    </div>
  </main>

  <footer class="footer">
    <div class="footer-cta">👉 Direct Link &amp; Free PDF: myadmissionguru.com</div>
    <div class="steps">{dots}</div>
  </footer>
</body>
</html>"""


def render_slides(
    scenes: list[dict[str, Any]],
    meta: dict[str, Any],
    orientation: str,
    work_dir: Path,
) -> list[Path]:
    w, h = (1080, 1920) if orientation == "portrait" else (1920, 1080)
    logo_uri = _data_uri(ASSETS_DIR / "logo.png", "image/png")
    mascot_uri = _data_uri(ASSETS_DIR / "mascot.webp", "image/webp")

    png_paths: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        for i, scene in enumerate(scenes):
            html_str = _build_slide_html(
                scene, meta, orientation, i, len(scenes), logo_uri, mascot_uri
            )
            page.set_content(html_str, wait_until="networkidle")
            out_png = work_dir / f"{orientation}_slide_{i:02d}.png"
            page.screenshot(path=str(out_png), type="png")
            png_paths.append(out_png)
        browser.close()
    return png_paths


def compile_video(
    scenes: list[dict[str, Any]],
    png_paths: list[Path],
    orientation: str,
    out_mp4: Path,
    work_dir: Path,
) -> Path:
    """
    Compiles per-scene PNG + MP3 into smooth MP4 segments with gentle motion,
    concatenates them cleanly, and outputs YouTube/IG/FB-compatible H.264 + AAC MP4.
    """
    w, h = (1080, 1920) if orientation == "portrait" else (1920, 1080)
    fps = 30
    seg_paths: list[Path] = []

    for i, (scene, png) in enumerate(zip(scenes, png_paths)):
        dur = float(scene["duration"])
        audio = Path(scene["audio_path"])
        seg = work_dir / f"{orientation}_seg_{i:02d}.mp4"
        frames = max(30, int(round(dur * fps)))

        # Subtle Ken Burns slow zoom (1.0 -> 1.04) + fade in/out for broadcast polish
        vf = (
            f"scale={w}:{h},"
            f"zoompan=z='min(zoom+0.00025,1.04)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0.5, dur - 0.25):.2f}:d=0.25,"
            f"format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(png),
            "-i", str(audio),
            "-vf", vf,
            "-af", f"apad=whole_dur={dur:.2f}",
            "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-movflags", "+faststart",
            str(seg),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        seg_paths.append(seg)

    concat_list = work_dir / f"{orientation}_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in seg_paths),
        encoding="utf-8",
    )

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_mp4
