# second_brain/content_ingestor/stages/base.py
"""
Shared base definitions and utilities for all pipeline stages.

This module defines:
- The Stage function contract
- A lightweight timer for consistent execution_time_ms measurement

All stages MUST conform to the defined interface.
No business logic belongs here.
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Dict, Tuple, TypeAlias

from second_brain.content_ingestor.schema import StageResult


Stage: TypeAlias = Callable[[Dict[str, Any], uuid.UUID], Tuple[Dict[str, Any], StageResult]]
"""
Type alias for stage functions.

Signature:
    stage(content_object: dict, run_id: uuid.UUID) -> (updated_content_object: dict, StageResult)
"""


@contextmanager
def timer() -> Callable[[], float]:
    """
    Context manager that provides a stop() function returning elapsed time in milliseconds.

    Usage:
        with timer() as end:
            # do work
            pass
        execution_time_ms = end()

    Returns:
        A callable that returns elapsed milliseconds since entry.
    """
    start = time.perf_counter()

    def end() -> float:
        return (time.perf_counter() - start) * 1000

    try:
        yield end
    finally:
        pass  # No-op — caller must invoke end() if they want the time



#     High-Level Intent

# stages/base.py defines the shared interface and base utilities for all pipeline stages.
# Its sole responsibility is to enforce the Stage contract:

#     Every stage function receives a mutable content_object: dict and a run_id: uuid.UUID.
#     Every stage returns a tuple (updated_content_object: dict, StageResult).
#     Helper timer context manager standardizes execution_time_ms measurement.
#     No business logic lives here — only contract enforcement and shared diagnostics tools.

# This ensures:

#     Uniform stage behavior (testable in isolation).
#     Explicit timing for performance auditing.
#     Future stages can import and conform without duplication.

# Architecture

#     Stage type alias for clarity in type hints.
#     timer() context manager: lightweight, no external deps.
#     Docstrings emphasize contract — violations are bugs.

# Data Flow

# Runner → calls stage function → stage uses timer → processes → returns updated dict + StageResult.
# Edge Cases & Failure Scenarios

#     Stage raises exception → must be caught by stage implementation (converted to StageResult with failure).
#     Timer used incorrectly → manual timing is forbidden (enforced by review).
#     run_id not logged → stages import logger separately.

# Extension Points

#     Add shared utilities (e.g., prompt versioning) here later.
#     Replace timer with higher-precision if needed.
