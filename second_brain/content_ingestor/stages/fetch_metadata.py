# second_brain/content_ingestor/stages/fetch_metadata.py
"""
Stage 2: Fetch YouTube metadata using yt-dlp.

Responsibility:
- Extract title, channel, duration, publish date, language, caption availability
- Extract description and tags (lossless raw)
- Handle network/transient errors gracefully with SOURCE_ERROR diagnostics

Requires yt-dlp>=2023.07.06 (handles modern YouTube changes).
No media is downloaded.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Tuple

import yt_dlp

from second_brain.content_ingestor.schema import (
    FailureType,
    StageFailure,
    StageResult,
)
from second_brain.content_ingestor.stages.base import timer
from second_brain.logging_core.logger import get_logger, log_event
import logging


YDL_PARAMS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "skip_download": True,
    "no_playlist": True,
    "extractor_args": {"youtubetab": {"skip": ["webpage"]}},  # Faster metadata only
}


def process(content_object: Dict[str, Any], run_id: uuid.UUID, config: Dict[str, Any]) -> Tuple[Dict[str, Any], StageResult]:
    """
    Fetch metadata for the validated video_id.
    """
    stage_name = "fetch_metadata"
    logger = get_logger(run_id)

    log_event(
        logger,
        logging.INFO,
        "Fetching YouTube metadata",
        stage_name=stage_name,
        event_type="start",
        metadata={"video_id": content_object["source"].get("video_id")},
    )

    video_id = content_object["source"].get("video_id")
    if not video_id:
        # Should not happen (validate_input enforces), but defensive
        failure = StageFailure(
            stage=stage_name,
            type=FailureType.INPUT_ERROR,
            cause="missing_video_id",
            impact="Cannot fetch metadata without video_id",
            suggested_fixes=["Ensure validate_input stage succeeded"],
        )
        result = StageResult(
            stage_name=stage_name,
            success=False,
            failures=[failure],
        )
        return content_object, result

    with timer() as end:
        try:
            with yt_dlp.YoutubeDL(YDL_PARAMS) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

            if not info:
                raise yt_dlp.DownloadError("No info returned")

            # Source fields
            content_object["source"]["title"] = info.get("title")
            content_object["source"]["channel_name"] = info.get("channel") or info.get("uploader")
            content_object["source"]["duration_seconds"] = info.get("duration")
            content_object["source"]["published_at"] = (
                datetime.fromtimestamp(info["timestamp"]) if info.get("timestamp") else None
            )
            content_object["source"]["language"] = info.get("language")

            # Caption availability
            has_manual = bool(info.get("subtitles"))
            has_auto = bool(info.get("automatic_captions"))
            content_object["source"]["captions_available"] = has_manual or has_auto

            # Raw lossless fields
            content_object["raw"]["description_text"] = info.get("description")
            content_object["raw"]["tags"] = info.get("tags")

            result = StageResult(
                stage_name=stage_name,
                success=True,
                execution_time_ms=end(),
            )

            log_event(
                logger,
                logging.INFO,
                "Metadata fetched successfully",
                stage_name=stage_name,
                event_type="success",
                metadata={
                    "title": info.get("title"),
                    "channel": content_object["source"]["channel_name"],
                    "duration_seconds": info.get("duration"),
                    "captions_available": content_object["source"]["captions_available"],
                },
            )

        except yt_dlp.DownloadError as exc:
            # Covers unavailable, private, deleted, age-restricted, geo-blocked
            cause = "video_unavailable" if "unavailable" in str(exc).lower() else "download_error"
            suggested = [
                "Check if video is public and not deleted",
                "Try again later (transient YouTube issue)",
            ]
            if "age-restricted" in str(exc).lower() or "sign in" in str(exc).lower():
                cause = "age_restricted"
                suggested.append("Provide cookies.txt with logged-in session")

            failure = StageFailure(
                stage=stage_name,
                type=FailureType.SOURCE_ERROR,
                cause=cause,
                impact="Metadata unavailable; downstream stages will have limited data",
                suggested_fixes=suggested,
            )
            result = StageResult(
                stage_name=stage_name,
                success=False,
                warnings=["Metadata fetch failed"],
                failures=[failure],
                execution_time_ms=end(),
            )

            log_event(
                logger,
                logging.WARNING,
                "Metadata fetch failed",
                stage_name=stage_name,
                event_type="failure",
                metadata={"error": str(exc)},
            )

        except Exception as exc:  # pylint: disable=broad-except
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.SOURCE_ERROR,
                cause="unexpected_error",
                impact="Metadata unavailable",
                suggested_fixes=["Check internet connection", "Update yt-dlp", "Review logs"],
            )
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[f"Unexpected error: {str(exc)}"],
                failures=[failure],
                execution_time_ms=end(),
            )

            log_event(
                logger,
                logging.ERROR,
                "Unexpected error during metadata fetch",
                stage_name=stage_name,
                event_type="failure",
                metadata={"exception": str(exc)},
            )

    return content_object, result


# High-Level Intent
# stages/fetch_metadata.py fetches essential YouTube metadata using yt-dlp without downloading any media.
# Single responsibility:

# Populate source fields (title, channel_name, duration_seconds, published_at, language, captions_available)
# Populate partial raw fields (description_text, tags)
# Detect caption availability for downstream transcript stage
# Fail gracefully with SOURCE_ERROR on network/API issues, providing retry suggestions

# This is the first stage with external I/O — all calls are isolated here.
# Architecture

# Uses yt-dlp.YoutubeDL with careful params: quiet, no downloads, no playlist
# Extracts only needed fields (explicit mapping)
# Handles common yt-dlp exceptions (DownloadError, ExtractorError)
# Structured StageFailure with typed cause and suggested_fixes
# Logs key extracted values (non-PII)

# Data Flow
# content_object → has source.video_id from previous stage
# → construct info URL
# → ydl.extract_info() → info dict
# → map to schema fields
# → update content_object["source"] and ["raw"]
# → return + StageResult
# Edge Cases & Failure Scenarios

# Video unavailable/private/deleted → SOURCE_ERROR cause="video_unavailable"
# Network timeout → SOURCE_ERROR cause="network_failure" + retry suggestion
# Age-restricted (requires cookies) → SOURCE_ERROR cause="age_restricted" + "Login via cookies" fix
# Geo-restricted → similar handling
# Partial info (some fields missing) → populate what’s available, success=True
# captions_available: check automatic_captions or subtitles presence

# Extension Points

# Inject custom ydl params (cookies, proxy) via config
# Cache metadata locally for reprocessing
# Add thumbnail fetch later