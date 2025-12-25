# second_brain/content_ingestor/stages/fetch_transcript.py
"""
Stage 3: Fetch transcript using transcription subsystem.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Tuple

from second_brain.content_ingestor.schema import FailureType, StageFailure, StageResult
from second_brain.content_ingestor.stages.base import timer
from second_brain.logging_core.logger import get_logger, log_event
from second_brain.transcription import TranscriptionConfig, transcribe
import logging


def process(content_object: Dict[str, Any], run_id: uuid.UUID, config: Dict[str, Any]) -> Tuple[Dict[str, Any], StageResult]:
    """Wrapper stage for transcription."""
    stage_name = "fetch_transcript"
    logger = get_logger(run_id)

    log_event(
        logger,
        logging.INFO,
        "Starting transcription",
        stage_name=stage_name,
        event_type="start",
    )

    url = content_object["source"]["url"]
    trans_config = TranscriptionConfig(
        download_audio_dir=config.get("download_audio_dir"),
        transcribe=config.get("transcribe", True),
    )

    with timer() as end:
        try:
            result = transcribe(url, trans_config)

            if result.success:
                content_object["raw"]["transcript_text"] = result.transcript_text
                content_object["raw"]["audio_path"] = result.audio_path
                content_object["raw"]["transcript_language"] = "en"  # Assume for now
                content_object["raw"]["transcript_confidence"] = 1.0 if result.method == "captions" else 0.7

            stage_result = StageResult(
                stage_name=stage_name,
                success=result.success,
                warnings=result.warnings,
                errors=result.errors,
                failures=[StageFailure(stage=stage_name, type=FailureType.EXTRACTION_ERROR, cause=err, impact="Transcript limited", suggested_fixes=result.suggested_fixes) for err in result.errors],
                suggested_fixes=result.suggested_fixes,
                execution_time_ms=end(),
            )

            log_event(
                logger,
                logging.INFO if result.success else logging.WARNING,
                "Transcription completed",
                stage_name=stage_name,
                event_type="success" if result.success else "failure",
                metadata={"method": result.method, "audio_saved": bool(result.audio_path)},
            )

        except Exception as exc:
            stage_result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[str(exc)],
                failures=[StageFailure(stage=stage_name, type=FailureType.EXTRACTION_ERROR, cause="unexpected", impact="No transcript", suggested_fixes=["Review logs"])],
            )
            log_event(
                logger,
                logging.ERROR,
                "Transcription failed unexpectedly",
                stage_name=stage_name,
                event_type="failure",
                metadata={"exception": str(exc)},
            )

    return content_object, stage_result