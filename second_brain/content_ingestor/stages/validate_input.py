# second_brain/content_ingestor/stages/validate_input.py
"""
Stage 1: Input validation and video_id extraction.

Responsibility:
- Confirm the provided URL is a valid YouTube URL
- Extract the canonical video_id
- Populate source.video_id and normalize source.url

Fails with INPUT_ERROR if URL is invalid.
No external network calls — pure deterministic validation.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, Tuple

from second_brain.content_ingestor.schema import (
    FailureType,
    StageFailure,
    StageResult,
)
from second_brain.content_ingestor.stages.base import timer
from second_brain.logging_core.logger import get_logger, log_event
import logging


# Comprehensive regex for YouTube URLs (covers watch, youtu.be, embeds, shorts)
YOUTUBE_REGEX = re.compile(
    r"(?:https?://)?"
    r"(?:www\.)?"
    r"(?:youtube\.com|youtu\.be|youtube-nocookie\.com)"
    r"/(?:watch\?v=|embed/|v/|shorts/)?([^&\n?#]+)"
)


def process(content_object: Dict[str, Any], run_id: uuid.UUID, config: Dict[str, Any]) -> Tuple[Dict[str, Any], StageResult]:
    """
    Validate input URL and extract video_id.

    Updates content_object["source"] with video_id on success.
    Always returns a StageResult with structured diagnostics.
    """
    stage_name = "validate_input"
    logger = get_logger(run_id)

    log_event(
        logger,
        logging.INFO,
        "Validating YouTube URL",
        stage_name=stage_name,
        event_type="start",
        metadata={"raw_url": content_object.get("source", {}).get("url")},
    )

    with timer() as end:
        source = content_object.get("source", {})
        url = source.get("url", "").strip()

        if not url:
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.INPUT_ERROR,
                cause="missing_url",
                impact="Cannot proceed without input URL",
                suggested_fixes=["Provide a valid YouTube URL via CLI"],
            )
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=["No URL provided"],
                failures=[failure],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.ERROR,
                "Validation failed: missing URL",
                stage_name=stage_name,
                event_type="failure",
            )
            return content_object, result

        match = YOUTUBE_REGEX.search(url)
        if not match:
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.INPUT_ERROR,
                cause="invalid_youtube_url",
                impact="Cannot extract video_id; pipeline will produce diagnostics-only artifact",
                suggested_fixes=[
                    "Ensure URL is from youtube.com or youtu.be",
                    "Check for typos or extra characters",
                    "Use standard watch?v= or youtu.be format",
                ],
            )
            result = StageResult(
                stage_name=stage_name,
                success=False,
                warnings=[f"URL did not match YouTube pattern: {url}"],
                failures=[failure],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.ERROR,
                "Validation failed: invalid YouTube URL",
                stage_name=stage_name,
                event_type="failure",
                metadata={"url": url},
            )
            return content_object, result

        video_id = match.group(1).split("&")[0]  # Strip extra params if any
        content_object["source"]["video_id"] = video_id
        content_object["source"]["url"] = url  # Preserve original for traceability

        result = StageResult(
            stage_name=stage_name,
            success=True,
            execution_time_ms=end(),
        )

        log_event(
            logger,
            logging.INFO,
            "URL validated and video_id extracted",
            stage_name=stage_name,
            event_type="success",
            metadata={"video_id": video_id},
        )

    return content_object, result



# High-Level Intent
# stages/validate_input.py is the first gatekeeper stage.
# Single responsibility:

# Validate that the input is a recognizable YouTube URL
# Extract the canonical video_id
# Populate source.url (normalized) and source.video_id
# Fail fast with typed INPUT_ERROR if invalid, providing clear suggested fixes

# No external calls (pure regex + string handling) → fully deterministic and instantly testable.
# Architecture

# process(content_object: dict, run_id: UUID) -> (dict, StageResult)
# Uses timer() from base.py for execution_time_ms
# Structured logging via log_event
# Returns partial success if URL is valid but malformed in minor ways (e.g., extra params preserved)
# On failure: success=False, structured StageFailure with suggested_fixes

# Data Flow
# Input content_object → has source.url from runner init
# → regex match → extract video_id
# → update content_object["source"]["video_id"]
# → return updated object + StageResult
# Edge Cases & Failure Scenarios

# Valid formats:
# https://www.youtube.com/watch?v=dQw4w9WgXcQ
# https://youtu.be/dQw4w9WgXcQ
# with extra params, timestamps, etc.

# Invalid: non-YouTube domains, missing v/id, malformed
# → INPUT_ERROR with cause="invalid_youtube_url"
# → suggested_fixes: ["Check URL spelling", "Ensure it is a direct YouTube link"]
# Empty URL → separate cause="missing_url"

# Extension Points

# Support additional YouTube domains (m.youtube.com, etc.)
# Future: accept shorts URLs explicitly