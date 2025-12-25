# second_brain/content_ingestor/diagnostics/collector.py
"""
Diagnostics aggregation for the Content Ingestor pipeline.

Central authority for collecting and synthesizing stage results into the final
diagnostics section of the output artifact.
"""

from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from second_brain.content_ingestor.schema import Diagnostics, StageResult


class DiagnosticsCollector:
    """
    Accumulates StageResult objects and synthesizes global diagnostics.

    Thread-safe not required (single-threaded pipeline).
    """

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        self._stage_status: Dict[str, StageResult] = {}
        self._global_warnings: List[str] = []
        self._global_errors: List[str] = []
        self._global_suggested_fixes: List[str] = []

    def add_stage_result(self, result: StageResult) -> None:
        """Add a stage result and merge global fields."""
        if result.stage_name in self._stage_status:
            raise ValueError(f"Duplicate stage result for {result.stage_name}")

        self._stage_status[result.stage_name] = result

        self._global_warnings.extend(result.warnings)
        self._global_errors.extend(result.errors)
        self._global_suggested_fixes.extend(result.suggested_fixes)

        # Also merge structured failures' suggested fixes
        for failure in result.failures:
            self._global_suggested_fixes.extend(failure.suggested_fixes)

    def has_fatal_failure(self) -> bool:
        """Return True if any stage reported success=False."""
        return any(not result.success for result in self._stage_status.values())

    def build_diagnostics(self) -> Dict[str, any]:
        """Build the final diagnostics dict conforming to schema."""
        diag = Diagnostics(
            stage_status=self._stage_status.copy(),
            warnings=self._global_warnings.copy(),
            errors=self._global_errors.copy(),
            suggested_fixes=list(set(self._global_suggested_fixes)),  # dedupe
        )
        return diag.model_dump(by_alias=False, exclude_none=True)
    

# High-Level Intent
# Central aggregator for all StageResult objects.
# Responsibilities:

# Collect results by stage_name.
# Merge global warnings/errors/suggested_fixes.
# Produce the final diagnostics dict for ContentObject.
# Provide query helpers (e.g., has_fatal_failure()).

# This isolates diagnostics logic from the runner, making runner orchestration cleaner.
# Architecture

# DiagnosticsCollector class: mutable accumulator.
# Methods: add_stage_result, build_diagnostics.
# Immutable output via .build_diagnostics() returning dict ready for schema.

# Data Flow
# Runner creates collector → passes to each stage (or adds post-stage) → final build → inserted into content_object.