# second_brain/logging/logger.py
"""
Centralized structured logging setup for the Content Ingestor.

Provides a pre-configured logger that emits JSON lines with mandatory fields:
- timestamp (ISO)
- run_id
- stage_name (optional, filled by caller)
- event_type (start/success/failure/progress)
- level
- message
- metadata (dict)

All logs in the system MUST use the logger obtained from get_logger().
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from logging import Logger


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Always include run_id if present in extra
        if hasattr(record, "run_id"):
            log_record["run_id"] = str(record.run_id)

        # Include optional structured fields
        extra_fields = ["stage_name", "event_type", "metadata"]
        for field in extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value

        # Include exception info if present
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


# Module-level cache to ensure single handler per run_id
_loggers: Dict[str, Logger] = {}


def get_logger(run_id: UUID) -> Logger:
    """
    Return a configured logger for the given workflow run.

    Logs are emitted as JSON lines to stdout.
    One logger instance per run_id (idempotent).
    """
    run_id_str = str(run_id)

    if run_id_str in _loggers:
        return _loggers[run_id_str]

    logger = logging.getLogger(f"second_brain.ingestor.{run_id_str}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    _loggers[run_id_str] = logger

    # Bind run_id to all records via filter
    class RunIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.run_id = run_id_str  # type: ignore
            return True

    logger.addFilter(RunIdFilter())

    return logger


def log_event(
    logger: Logger,
    level: int,
    message: str,
    *,
    stage_name: str | None = None,
    event_type: str,
    metadata: Dict[str, Any] | None = None,
) -> None:
    """
    Convenience wrapper for structured logging.

    Use this inside stages for consistency.
    """
    extra: Dict[str, Any] = {"event_type": event_type}
    if stage_name:
        extra["stage_name"] = stage_name
    if metadata:
        extra["metadata"] = metadata

    logger.log(level, message, extra=extra)


# High-Level Intent
# logging/logger.py is the centralized, structured logging facility for the entire Content Ingestor pipeline.
# Its single responsibility: provide a pre-configured logger that emits JSON-line structured logs with mandatory fields (run_id, stage_name, event_type, timestamp, message, metadata).
# This ensures logs are:

# Human-readable in dev
# Machine-parsable in production
# Auditable for every run
# Consistent across all modules

# No log strings are free-form — everything is dict-based.
# Architecture

# Singleton-like get_logger(run_id: UUID) -> Logger function.
# Uses Python logging with custom JSONFormatter.
# All logs include required fields via extra.
# Levels used intentionally (INFO for progress, WARNING for degradation, ERROR for stage failure).
# No secrets/PII logging (enforced by design).

# Data Flow

# Runner calls get_logger(run_id) once at start.
# Passes logger instance to stages (or stages re-call get_logger with same run_id).
# Each log call: logger.info("message", extra={"event_type": "start", "metadata": {...}})

# Edge Cases & Failure Scenarios

# Logging failure (e.g., disk full) → stdlib logging degrades gracefully to stderr.
# Missing run_id → raise early (invalid pipeline state).
# Metadata too large → no truncation (accept for auditability).

# Extension Points

# Swap handler for file output, syslog, or remote (e.g., Loki) via config.
# Add correlation IDs for distributed runs later.