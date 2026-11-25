"""
Main Pipeline Orchestrator for My Admission Guru Hindi Video Factory.
Usage:
  python scripts/pipeline.py --payload payload.json [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from publishers import (
    notify_mag_callback,
    upload_facebook_reel,
    upload_instagram_reel,
    upload_youtube,
)
from render_video import compile_video, render_slides
from script_gen import build_scripts
from tts_gen import generate_scene_audio


def main() -> int:
    parser = argparse.ArgumentParser(description="My Admission Guru Auto Hindi Video Factory")
    parser.add_argument("--payload", required=True, help="Path to JSON payload from myadmissionguru.com")
    parser.add_argument("--out-dir", default="out", help="Output directory for rendered MP4s")
    parser.add_argument("--dry-run", action="store_true", help="Render videos only; skip publishing & callback")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    update_id = int(payload.get("update_id") or 0)
    slug = str(payload.get("slug") or f"update-{update_id}")

    out_dir = Path(args.out_dir)
    work_dir = out_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== [1/4] Generating Hindi scripts for #{update_id}: {payload.get('title')} ===")
    bundle = build_scripts(payload)
    (out_dir / "script_bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=== [2/4] Synthesizing Neural Hindi Voiceover (edge-tts) ===")
    long_scenes, _ = generate_scene_audio(bundle["long_scenes"], work_dir, prefix="long")
    short_scenes, _ = generate_scene_audio(bundle["short_scenes"], work_dir, prefix="short")

    print("=== [3/4] Rendering 16:9 Horizontal & 9:16 Portrait Branded Videos ===")
    long_pngs = render_slides(long_scenes, bundle["meta"], "landscape", work_dir)
    short_pngs = render_slides(short_scenes, bundle["meta"], "portrait", work_dir)

    long_mp4 = out_dir / f"{slug}-horizontal-16x9.mp4"
    short_mp4 = out_dir / f"{slug}-portrait-9x16.mp4"

    compile_video(long_scenes, long_pngs, "landscape", long_mp4, work_dir)
    compile_video(short_scenes, short_pngs, "portrait", short_mp4, work_dir)
    print(f"Rendered:\n  - {long_mp4}\n  - {short_mp4}")

    if args.dry_run:
        print("=== Dry-run complete. Skipping uploads & callback. ===")
        return 0

    print("=== [4/4] Publishing to YouTube (Long + Shorts), Facebook Reels & Instagram Reels ===")
    privacy = os.getenv("YT_PRIVACY", "public").strip() or "public"
    yt_long_id = ""
    yt_short_id = ""

    try:
        yt_long_id = upload_youtube(
            long_mp4, bundle["yt_title_long"], bundle["description"], bundle["tags"], privacy=privacy
        )
    except Exception as exc:
        print(f"[youtube-long] ERROR: {exc}", file=sys.stderr)

    try:
        yt_short_id = upload_youtube(
            short_mp4, bundle["yt_title_short"], bundle["description"], bundle["tags"], privacy=privacy
        )
    except Exception as exc:
        print(f"[youtube-short] ERROR: {exc}", file=sys.stderr)

    try:
        upload_facebook_reel(short_mp4, bundle["social_caption"])
    except Exception as exc:
        print(f"[facebook] ERROR: {exc}", file=sys.stderr)

    try:
        upload_instagram_reel(short_mp4, bundle["social_caption"], update_id)
    except Exception as exc:
        print(f"[instagram] ERROR: {exc}", file=sys.stderr)

    # Notify myadmissionguru.com so the YouTube video auto-embeds on the relevant page
    callback_url = str(payload.get("callback_url") or "https://myadmissionguru.com/api/video-callback")
    if yt_long_id or yt_short_id:
        try:
            notify_mag_callback(callback_url, update_id, yt_long_id, yt_short_id)
        except Exception as exc:
            print(f"[callback] ERROR: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
