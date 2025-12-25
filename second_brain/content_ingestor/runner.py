# second_brain/content_ingestor/runner.py
"""
Orchestration runner for the YouTube Content Ingestor pipeline.

Responsibilities:
- Initialize traceability and supporting objects
- Execute stages in fixed order
- Aggregate diagnostics
- Validate and return final content object

No business logic lives here — only orchestration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any
import logging

from second_brain.content_ingestor.schema import ContentObject, Identity, Source
from second_brain.content_ingestor.diagnostics.collector import DiagnosticsCollector
from second_brain.content_ingestor.stages import (
    validate_input,
    fetch_metadata,
    fetch_transcript,
    analyze_structure,
    analyze_semantics,
)
from second_brain.logging_core.logger import get_logger, log_event
from second_brain.logging_core import logger as log_mod  # for type hints


STAGES = [
    validate_input.process,
    fetch_metadata.process,
    fetch_transcript.process,
    analyze_structure.process,
    analyze_semantics.process,
]


def run_ingestion(url: str, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Execute the full ingestion pipeline for a YouTube URL.

    Args:
        url: YouTube video URL
        config: Optional configuration dict for stages (e.g., transcription settings)

    Returns:
        Complete content object dict conforming to ContentObject schema.
        Artifact is always produced, even on partial failure.
    """
    run_id = uuid.uuid4()
    logger = get_logger(run_id)

    log_event(
        logger,
        logging.INFO,
        "Starting YouTube content ingestion pipeline",
        event_type="pipeline_start",
        metadata={"url": url, "run_id": str(run_id)},
    )

    # Initialize traceability
    identity = Identity()
    content_object: Dict[str, Any] = {
        "identity": identity.model_dump(),
        "source": Source(url=url).model_dump(),
        "raw": {},
        "structure": {},
        "semantics": {},
        "diagnostics": {},
    }

    collector = DiagnosticsCollector(run_id)

    # Execute stages
    for stage_func in STAGES:
        stage_name = stage_func.__module__.split('.')[-1]
        log_event(
            logger,
            logging.INFO,
            f"Starting stage",
            stage_name=stage_name,
            event_type="start",
        )

        try:
            content_object, stage_result = stage_func(content_object, run_id, config or {})
            collector.add_stage_result(stage_result)

            log_event(
                logger,
                logging.INFO if stage_result.success else logging.WARNING,
                f"Stage completed",
                stage_name=stage_name,
                event_type="success" if stage_result.success else "failure",
                metadata={"success": stage_result.success},
            )
        except Exception as exc:  # pylint: disable=broad-except
            # Convert unhandled exception to stage failure
            from second_brain.content_ingestor.schema import StageResult, StageFailure, FailureType

            failure = StageFailure(
                stage=stage_name,
                type=FailureType.SOURCE_ERROR,  # conservative default
                cause="unexpected_exception",
                impact="stage aborted",
                suggested_fixes=["Review logs", "Report bug with traceback"],
            )
            stage_result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[f"Unhandled exception: {str(exc)}"],
                failures=[failure],
            )
            collector.add_stage_result(stage_result)

            log_event(
                logger,
                logging.ERROR,
                f"Unhandled exception in stage",
                stage_name=stage_name,
                event_type="failure",
                metadata={"exception": str(exc)},
            )

    # Assemble diagnostics
    content_object["diagnostics"] = collector.build_diagnostics()

    # Final validation (best effort)
    try:
        validated = ContentObject.model_validate(content_object)
        content_object = validated.model_dump(by_alias=False, exclude_none=True)
        log_event(logger, logging.INFO, "Pipeline completed successfully", event_type="pipeline_success")
    except Exception as exc:  # pylint: disable=broad-except
        log_event(
            logger,
            logging.ERROR,
            "Final schema validation failed — returning raw object",
            event_type="validation_failure",
            metadata={"validation_error": str(exc)},
        )
        # Return raw object anyway for auditability

    return content_object



# High-Level Intent
# runner.py is the orchestration heart of the Content Ingestor pipeline.
# Its sole responsibility is to:

# Generate traceability IDs
# Initialize the empty content_object with identity
# Create DiagnosticsCollector and logger
# Execute stages in strict, declared order
# Aggregate results and insert diagnostics
# Validate final object against schema
# Return the complete, validated content dict (ready for writer)

# It contains no business logic — only orchestration and error containment.
# Stages are imported explicitly (no dynamic loading) for clarity and testability.
# Architecture

# run_ingestion(url: str) -> dict: Public entry point (called by CLI).
# Fixed list of stages: [validate_input, fetch_metadata, ...]
# Each stage called with mutable content_object and run_id
# DiagnosticsCollector centralized
# Structured logging at key milestones
# Final validation via ContentObject.model_validate()
# Partial success always produces artifact

# Data Flow
# CLI → runner.run_ingestion(url)
# → generate IDs + logger + collector
# → content_object = {"identity": {...}, "source": {"url": url, ...}}
# → for each stage:
#   log start → call stage → log result → collector.add → mutate content_object
# → insert diagnostics → validate → return dict
# Edge Cases & Failure Scenarios

# Early stage failure (e.g., invalid URL) → subsequent stages skipped, diagnostics explain, artifact still produced.
# Exception in stage → caught, converted to StageResult with failure, pipeline continues.
# Schema validation failure at end → wrapped as diagnostic, raw dict still returned (graceful degradation).
# No transcript/metadata → partial object valid.

# Extension Points

# Stage list injectable via config later.
# Parallel stages (if independent) via executor.
# Pre/post hooks for future governance.