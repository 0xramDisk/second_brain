# second_brain/transcription/whisper.py
"""
Whisper strategy: audio extraction + transcription.
Single responsibility: manage audio lifecycle and model invocation.
Model cached module-level; GPU detection.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional

import torch
import whisper

from second_brain.transcription.schema import TranscriptionResult

# Module-level cache
_MODEL: Optional[whisper.Whisper] = None
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _load_model(model_name: str = "base") -> whisper.Whisper:
    global _MODEL  # pylint: disable=global-statement
    if _MODEL is None:
        _MODEL = whisper.load_model(model_name, device=_DEVICE)
    return _MODEL


def transcribe_audio(youtube_url: str, save_dir: Optional[str], do_transcribe: bool) -> TranscriptionResult:
    try:
        if save_dir:
            audio_path = os.path.join(save_dir, f"{_extract_video_id(youtube_url)}.wav")
            os.makedirs(save_dir, exist_ok=True)
        else:
            tmpdir = tempfile.TemporaryDirectory()
            audio_path = os.path.join(tmpdir.name, "audio.wav")

        _download_audio(youtube_url, audio_path)

        result = TranscriptionResult(
            success=True,
            audio_path=audio_path if save_dir else None,
            method="whisper",
            warnings=["Used audio fallback (slower)"],
        )

        if do_transcribe:
            model = _load_model()
            whisper_result = model.transcribe(audio_path)
            text = whisper_result.get("text", "").strip()

            if not text:
                result.success = False
                result.errors = ["Whisper returned empty transcript"]
                result.suggested_fixes = ["Check audio quality", "Try larger model"]
            else:
                result.transcript_text = text

        if not save_dir:
            tmpdir.cleanup()  # Delete temp audio

        return result

    except Exception as e:
        return TranscriptionResult(
            success=False,
            errors=[str(e)],
            suggested_fixes=["Ensure yt-dlp/whisper installed", "Check ffmpeg"],
        )


def _extract_video_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    raise ValueError("Invalid YouTube URL")


def _download_audio(youtube_url: str, output_path: str) -> None:
    output_template = output_path.replace(".wav", ".%(ext)s")
    command = [
        "yt-dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "wav",
        "-o", output_template,
        youtube_url,
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)