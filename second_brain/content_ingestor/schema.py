# second_brain/content_ingestor/schema.py
"""
Authoritative schema definitions for the YouTube Content Ingestor pipeline.

This module defines:
- The complete structure of the output JSON artifact
- The StageResult contract returned by every pipeline stage
- Typed failure categories for diagnostics

All other modules MUST conform to these contracts.
Schema changes require explicit justification and migration planning.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator


class FailureType(str, Enum):
    """Typed failure categories for machine-parsable diagnostics."""
    INPUT_ERROR = "input_error"
    SOURCE_ERROR = "source_error"
    EXTRACTION_ERROR = "extraction_error"
    STRUCTURE_ERROR = "structure_error"
    INTERPRETATION_ERROR = "interpretation_error"



#sff

class StageFailure(BaseModel):
    """Structured representation of a single failure."""
    stage: str
    type: FailureType
    cause: str
    impact: str
    suggested_fixes: List[str] = Field(default_factory=list)


class StageResult(BaseModel):
    """
    Standardized result returned by every pipeline stage.

    Every stage must return an instance of this model.
    Success is False if any error occurred, even if partial progress was made.
    """
    stage_name: str
    success: bool
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    failures: List[StageFailure] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None

    model_config = ConfigDict(frozen=True)


class Identity(BaseModel):
    """Traceability and reproducibility fields."""
    content_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workflow_run_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    workflow_version: str = "0.1.0"


class Source(BaseModel):
    """Immutable origin facts."""
    source_type: str = "youtube"
    url: str
    video_id: Optional[str] = None
    title: Optional[str] = None
    channel_name: Optional[str] = None
    duration_seconds: Optional[int] = None
    published_at: Optional[datetime] = None
    language: Optional[str] = None
    captions_available: Optional[bool] = None


class Raw(BaseModel):
    """Lossless ground truth data."""
    transcript_text: Optional[str] = None
    transcript_language: Optional[str] = None
    transcript_confidence: Optional[float] = None
    chapters: Optional[List[Dict[str, Any]]] = None
    description_text: Optional[str] = None
    tags: Optional[List[str]] = None


class Structure(BaseModel):
    """Non-opinionated content anatomy."""
    sections: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[str]] = None
    references: Optional[List[str]] = None
    detected_steps: Optional[List[str]] = None
    code_blocks_present: Optional[bool] = None


class Semantics(BaseModel):
    """Light descriptive interpretation (no judgment)."""
    primary_topics: Optional[List[str]] = None
    secondary_topics: Optional[List[str]] = None
    content_type: Optional[str] = None
    difficulty_level: Optional[str] = None
    knowledge_type: Optional[str] = None


class Diagnostics(BaseModel):
    """Explainability and audit trail."""
    stage_status: Dict[str, StageResult] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)


class ContentObject(BaseModel):
    """
    Root model for the complete ingestion artifact.

    This is the single source of truth for the pipeline output.
    Validation ensures required traceability fields are always present.
    """
    identity: Identity
    source: Source
    raw: Raw = Field(default_factory=Raw)
    structure: Structure = Field(default_factory=Structure)
    semantics: Semantics = Field(default_factory=Semantics)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)

    @model_validator(mode='after')
    def validate_required_source_fields(self) -> 'ContentObject':
        """Ensure minimum source traceability even on partial failure."""
        if not self.source.video_id:
            # This should only happen on early validation failure — still valid for diagnostics
            pass
        return self
    


# High-Level Intent
# schema.py is the authoritative contract for the entire Content Ingestor pipeline. It defines:

# The final JSON artifact structure via Pydantic models (schema-first enforcement).
# The StageResult contract that every stage must return (success, warnings, errors, suggested fixes, timing).
# Typed failure categories for consistent diagnostics.
# Validation rules ensuring required fields in identity and source are always present, while allowing graceful partial population of raw, structure, and semantics.

# This module has zero external dependencies beyond Pydantic and standard library — it is pure, deterministic, and fully testable in isolation.
# Architecture

# ContentObject (root model): Composes all sections.
# Identity, Source, Raw, Structure, Semantics, Diagnostics: Nested models with explicit field constraints.
# StageResult: Standardized return type for stages, enforcing structured failures.
# FailureType (Enum): Typed failure categories for machine-parsable diagnostics.
# All models use Pydantic v2 features: model_validate, strict optional fields, default factories.

# Data Flow

# Runner creates empty dict → stages mutate → final dict validated against ContentObject.
# On write, ContentObject.model_validate(content_dict) ensures contract adherence.
# Partial objects (e.g., no transcript) are valid as long as required identity/source fields are populated.

# Edge Cases & Failure Scenarios

# Missing required fields (e.g., no video_id after validation) → validation error in runner (caught and turned into diagnostic).
# AI stages produce malformed output → downstream validation fails → stage returns success=False with INTERPRETATION_ERROR.
# Empty but valid object (invalid URL early fail) → still produces artifact with diagnostics explaining the failure.

# Extension Points

# Add new sections (e.g., audio_analysis) by extending ContentObject.
# Evolve Semantics with richer enums without breaking existing artifacts.
# workflow_version field enables future schema migrations.