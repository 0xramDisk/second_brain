# second_brain/transcription/captions.py
"""
Caption strategy using youtube_transcript_api.
Single responsibility: fetch and concatenate captions.
"""

from __future__ import annotations

from typing import List
from second_brain.transcription.schema import TranscriptionResult
def get_captions(youtube_url: str) -> TranscriptionResult:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

        video_id = _extract_video_id(youtube_url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(segment["text"] for segment in transcript)

        return TranscriptionResult(
            success=True,
            transcript_text=text,
            method="captions",
        )
    except (TranscriptsDisabled, NoTranscriptFound):
        return TranscriptionResult(
            success=False,
            warnings=["YouTube captions unavailable"],
            suggested_fixes=["Fallback to audio transcription"],
        )
    except Exception as e:
        return TranscriptionResult(
            success=False,
            errors=[str(e)],
            suggested_fixes=["Retry caption fetch"],
        )


def _extract_video_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    raise ValueError("Invalid YouTube URL")