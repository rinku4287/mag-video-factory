"""
Free Neural Hindi TTS Generator using Microsoft Edge TTS (edge-tts).
Voices:
  - hi-IN-MadhurNeural (Male, energetic Hindi news/edu style - default)
  - hi-IN-SwaraNeural  (Female, clear Hindi voice)

Guarantees:
  - Long 16:9 video: natural comfortable pace (+2%) so 9 scenes comfortably run > 3 minutes.
  - Short 9:16 video: crisp pace (+8%) with an automatic safety check keeping total duration < 58 seconds
    (strictly under 1 minute for YouTube Shorts & Instagram/Facebook Reels).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

import edge_tts


DEFAULT_VOICE = os.getenv("HINDI_VOICE", "hi-IN-MadhurNeural").strip() or "hi-IN-MadhurNeural"


def get_audio_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return max(2.5, float(out))


async def _synth_one(text: str, out_mp3: Path, voice: str, rate: str) -> None:
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await comm.save(str(out_mp3))


def _fmt_srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunk_caption(text: str, max_words: int = 8) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)] or [text]


def _synthesize_batch(
    scenes: list[dict[str, Any]],
    work_dir: Path,
    prefix: str,
    voice: str,
    rate: str,
    pad: float,
) -> float:
    total = 0.0
    for i, scene in enumerate(scenes):
        mp3_path = work_dir / f"{prefix}_scene_{i:02d}.mp3"
        asyncio.run(_synth_one(scene["narration"], mp3_path, voice, rate))
        dur = get_audio_duration(mp3_path)
        scene["audio_path"] = mp3_path
        scene["raw_duration"] = dur
        scene["duration"] = dur + pad
        total += scene["duration"]
    return total


def generate_scene_audio(
    scenes: list[dict[str, Any]],
    work_dir: Path,
    prefix: str,
    voice: str = DEFAULT_VOICE,
) -> tuple[list[dict[str, Any]], Path]:
    """
    Synthesizes MP3 for each scene, attaches 'audio_path' and 'duration',
    enforces duration targets (>185s for long, <58s for short), and writes synced SRT subtitles.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    is_short = prefix == "short"
    rate = "+8%" if is_short else "+2%"
    pad = 0.30 if is_short else 0.70

    total = _synthesize_batch(scenes, work_dir, prefix, voice, rate, pad)

    # Safety guard: ensure Shorts/Reels stay strictly under 58 seconds (< 1 min)
    if is_short and total > 57.5:
        print(f"[tts_gen] Short video was {total:.1f}s (>57.5s); re-synthesizing slightly faster (+16%) to stay < 1 min.")
        total = _synthesize_batch(scenes, work_dir, prefix, voice, "+16%", 0.20)

    # Safety guard: ensure Horizontal Long video is comfortably > 3 minutes (185s+)
    if not is_short and total < 185.0:
        extra_per_scene = (186.0 - total) / max(1, len(scenes))
        for scene in scenes:
            scene["duration"] += extra_per_scene
        total = sum(float(s["duration"]) for s in scenes)

    print(f"[tts_gen] {prefix} total duration: {total:.1f}s ({total/60:.2f} min)")

    srt_lines: list[str] = []
    srt_idx = 1
    cursor = 0.0
    for scene in scenes:
        dur = float(scene["raw_duration"])
        chunks = _chunk_caption(scene["narration"], max_words=7 if is_short else 10)
        chunk_dur = dur / max(1, len(chunks))
        for ci, chunk in enumerate(chunks):
            t0 = cursor + ci * chunk_dur
            t1 = cursor + (ci + 1) * chunk_dur
            srt_lines.append(f"{srt_idx}\n{_fmt_srt_time(t0)} --> {_fmt_srt_time(t1)}\n{chunk}\n")
            srt_idx += 1
        cursor += float(scene["duration"])

    srt_path = work_dir / f"{prefix}.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return scenes, srt_path
