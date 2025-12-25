# second_brain/transcription/schema.py
"""
Shared contracts for transcription subsystem.
Single responsibility: define result and config dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TranscriptionConfig:
    """Configuration for transcription modes."""
    download_audio_dir: Optional[str] = None  # Save path or None for temp
    transcribe: bool = True  # False: audio only


@dataclass
class TranscriptionResult:
    """Standardized result from any transcription strategy."""
    success: bool
    transcript_text: str = ""
    audio_path: Optional[str] = None
    method: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    execution_time_sec: float = 0.0