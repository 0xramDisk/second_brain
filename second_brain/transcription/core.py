# second_brain/transcription/core.py
"""
Orchestrator for transcription strategies.
Single responsibility: sequence strategies, map to result contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import time

from second_brain.transcription.captions import get_captions
from second_brain.transcription.whisper import transcribe_audio
from second_brain.transcription.schema import TranscriptionConfig, TranscriptionResult

@dataclass
class TranscriptionConfig:
    """Config for transcription modes."""
    download_audio_dir: Optional[str] = None  # None: temp, str: save path
    transcribe: bool = True  # False: download only


@dataclass
class TranscriptionResult:
    success: bool
    transcript_text: str = ""
    audio_path: Optional[str] = None  # Saved audio if requested
    method: Optional[str] = None  # "captions", "whisper"
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    execution_time_sec: float = 0.0


def transcribe(youtube_url: str, config: TranscriptionConfig = TranscriptionConfig()) -> TranscriptionResult:
    """Orchestrate transcription with fallback."""
    start = time.time()

    # Try captions (fast path)
    captions_result = get_captions(youtube_url)
    if captions_result.success:
        captions_result.execution_time_sec = time.time() - start
        return captions_result

    # Fallback to whisper (audio required)
    whisper_result = transcribe_audio(youtube_url, config.download_audio_dir, config.transcribe)
    whisper_result.execution_time_sec = time.time() - start

    # Merge warnings/errors from captions attempt
    whisper_result.warnings.extend(captions_result.warnings)
    whisper_result.errors.extend(captions_result.errors)
    whisper_result.suggested_fixes.extend(captions_result.suggested_fixes)

    return whisper_result