"""
Free Neural Hindi TTS Generator using Microsoft Edge TTS (edge-tts).
Voices:
  - hi-IN-MadhurNeural (Male, energetic Hindi news/edu style - default)
  - hi-IN-SwaraNeural  (Female, clear Hindi voice)

Generates per-scene MP3 files + exact audio duration via ffprobe + synced Hindi SRT subtitles.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

import edge_tts


DEFAULT_VOICE = os.getenv("HINDI_VOICE", "hi-IN-MadhurNeural").strip() or "hi-IN-MadhurNeural"
DEFAULT_RATE = os.getenv("HINDI_VOICE_RATE", "+6%").strip() or "+6%"


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


def generate_scene_audio(
    scenes: list[dict[str, Any]],
    work_dir: Path,
    prefix: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
) -> tuple[list[dict[str, Any]], Path]:
    """
    Synthesizes MP3 for each scene, attaches 'audio_path' and 'duration',
    and writes a combined synced SRT subtitle file.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    srt_lines: list[str] = []
    srt_idx = 1
    cursor = 0.0
    pad = 0.45  # breathing room between scenes

    for i, scene in enumerate(scenes):
        mp3_path = work_dir / f"{prefix}_scene_{i:02d}.mp3"
        asyncio.run(_synth_one(scene["narration"], mp3_path, voice, rate))
        dur = get_audio_duration(mp3_path)
        scene["audio_path"] = mp3_path
        scene["duration"] = dur + pad

        # Split scene narration evenly into short readable caption chunks
        chunks = _chunk_caption(scene["narration"], max_words=7 if prefix == "short" else 10)
        chunk_dur = dur / max(1, len(chunks))
        for ci, chunk in enumerate(chunks):
            t0 = cursor + ci * chunk_dur
            t1 = cursor + (ci + 1) * chunk_dur
            srt_lines.append(f"{srt_idx}\n{_fmt_srt_time(t0)} --> {_fmt_srt_time(t1)}\n{chunk}\n")
            srt_idx += 1
        cursor += scene["duration"]

    srt_path = work_dir / f"{prefix}.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return scenes, srt_path
