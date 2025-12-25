# second_brain/content_ingestor/stages/analyze_semantics.py
"""
Stage 5 (Final): Light semantic classification using AI.

Responsibility:
- Classify primary/secondary topics
- Determine content_type, difficulty_level, knowledge_type
- Purely descriptive — no judgment or scoring

AI usage strictly follows project guidelines:
- Prompt versioned and isolated
- Invocation isolated
- Output validated and bounded
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field, ValidationError, model_validator

from second_brain.content_ingestor.schema import (
    FailureType,
    StageFailure,
    StageResult,
)
from second_brain.content_ingestor.stages.base import timer
from second_brain.content_ingestor.stages.analyze_structure import _call_llm  # Reuse isolated call
from second_brain.logging_core.logger import get_logger, log_event
import logging


# Versioned prompt — intentional and stable
SEMANTICS_PROMPT = """
You are an expert content classifier. Analyze the YouTube video based on title, description, and transcript.

Classify only these attributes:
- primary_topics: 3-7 main topics (most central)
- secondary_topics: 0-5 additional notable topics
- content_type: one of [tutorial, explanation, interview, review, opinion, demonstration, vlog, news, entertainment, other]
- difficulty_level: one of [beginner, intermediate, advanced]
- knowledge_type: one of [conceptual, procedural, mixed]

Title: {title}
Description: {description}
Transcript sample: {transcript_sample}

Rules:
- Be objective and evidence-based
- No commentary or summary
- Respond with valid JSON only, exact schema:
{
  "primary_topics": [string],
  "secondary_topics": [string],
  "content_type": string,
  "difficulty_level": string,
  "knowledge_type": string
}
""".strip()


class SemanticsResponse(BaseModel):
    """Strict validation model for semantic classification."""
    primary_topics: List[str] = Field(min_length=1, max_length=7)
    secondary_topics: List[str] = Field(default_factory=list, max_length=5)
    content_type: str = Field(pattern="^(tutorial|explanation|interview|review|opinion|demonstration|vlog|news|entertainment|other)$")
    difficulty_level: str = Field(pattern="^(beginner|intermediate|advanced)$")
    knowledge_type: str = Field(pattern="^(conceptual|procedural|mixed)$")

    @model_validator(mode='after')
    def validate_primary_not_empty(self) -> 'SemanticsResponse':
        if not self.primary_topics:
            raise ValueError("primary_topics must not be empty")
        return self

    model_config = {"extra": "forbid"}


def process(content_object: Dict[str, Any], run_id: uuid.UUID, config: Dict[str, Any]) -> Tuple[Dict[str, Any], StageResult]:
    """
    Perform light semantic classification.
    """
    stage_name = "analyze_semantics"
    logger = get_logger(run_id)

    log_event(
        logger,
        logging.INFO,
        "Starting semantic classification",
        stage_name=stage_name,
        event_type="start",
    )

    title = content_object["source"].get("title", "")
    description = content_object["raw"].get("description_text", "")
    transcript = content_object["raw"].get("transcript_text", "") or ""

    with timer() as end:
        # Graceful empty case
        if not transcript and not title:
            content_object["semantics"] = {
                "primary_topics": [],
                "secondary_topics": [],
                "content_type": None,
                "difficulty_level": None,
                "knowledge_type": None,
            }
            result = StageResult(
                stage_name=stage_name,
                success=True,
                warnings=["Insufficient content for semantic analysis"],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.INFO,
                "Semantic analysis skipped (no content)",
                stage_name=stage_name,
                event_type="success",
            )
            return content_object, result

        # Use sample to stay within token limits
        transcript_sample = transcript[:20000]  # ~7-8k tokens safe
        if len(transcript) > 20000:
            content_object["diagnostics"].setdefault("warnings", []).append("Transcript truncated for semantic analysis")

        prompt = SEMANTICS_PROMPT.format(
            title=title or "No title",
            description=description[:2000] or "No description",
            transcript_sample=transcript_sample or "No transcript",
        )

        try:
            raw_response = _call_llm(prompt)
            parsed = json.loads(raw_response)
            validated = SemanticsResponse.model_validate(parsed)

            content_object["semantics"] = {
                "primary_topics": validated.primary_topics,
                "secondary_topics": validated.secondary_topics,
                "content_type": validated.content_type,
                "difficulty_level": validated.difficulty_level,
                "knowledge_type": validated.knowledge_type,
            }

            result = StageResult(
                stage_name=stage_name,
                success=True,
                execution_time_ms=end(),
            )

            log_event(
                logger,
                logging.INFO,
                "Semantic classification completed",
                stage_name=stage_name,
                event_type="success",
                metadata={
                    "primary_topic_count": len(validated.primary_topics),
                    "content_type": validated.content_type,
                    "difficulty": validated.difficulty_level,
                    "knowledge_type": validated.knowledge_type,
                },
            )

        except json.JSONDecodeError as exc:
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.INTERPRETATION_ERROR,
                cause="invalid_json_response",
                impact="Semantics fields empty",
                suggested_fixes=["Review prompt", "Update model for JSON adherence"],
            )
            content_object["semantics"] = {
                "primary_topics": [],
                "secondary_topics": [],
                "content_type": None,
                "difficulty_level": None,
                "knowledge_type": None,
            }
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=["AI returned invalid JSON"],
                failures=[failure],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.ERROR,
                "Semantics failed: invalid JSON",
                stage_name=stage_name,
                event_type="failure",
                metadata={"raw_response_snippet": raw_response[:500]},
            )

        except ValidationError as exc:
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.INTERPRETATION_ERROR,
                cause="schema_validation_failed",
                impact="Semantics fields empty",
                suggested_fixes=["Strengthen prompt constraints", "Add response repair"],
            )
            content_object["semantics"] = {
                "primary_topics": [],
                "secondary_topics": [],
                "content_type": None,
                "difficulty_level": None,
                "knowledge_type": None,
            }
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[f"Validation failed: {exc}"],
                failures=[failure],
                execution_time_ms=end(),
            )

        except Exception as exc:  # pylint: disable=broad-except
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.INTERPRETATION_ERROR,
                cause="llm_invocation_failed",
                impact="Semantics fields empty",
                suggested_fixes=["Check model availability", "Retry later"],
            )
            content_object["semantics"] = {
                "primary_topics": [],
                "secondary_topics": [],
                "content_type": None,
                "difficulty_level": None,
                "knowledge_type": None,
            }
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[f"LLM error: {str(exc)}"],
                failures=[failure],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.ERROR,
                "Semantics failed: LLM error",
                stage_name=stage_name,
                event_type="failure",
                metadata={"exception": str(exc)},
            )

    return content_object, result

# High-Level Intent
# stages/analyze_semantics.py is the final analysis stage.
# Single responsibility: perform light descriptive semantic classification using AI.
# Extract:

# primary_topics (3-7 main topics)
# secondary_topics (optional additional)
# content_type (e.g., tutorial, explanation, interview, review, opinion, vlog)
# difficulty_level (beginner/intermediate/advanced)
# knowledge_type (conceptual/procedural/mixed)

# Strictly descriptive — no judgment of value, accuracy, or permanence.
# AI usage follows all project rules: prompt versioned and isolated, invocation isolated, output strictly validated with Pydantic, bounded, and auditable.
# Graceful degradation: no transcript → empty but valid fields.
# Architecture

# Versioned prompt as module constant
# Same isolated LLM call pattern as analyze_structure
# Strict SemanticsResponse Pydantic model with enums where possible
# Validation ensures bounded lists and valid enum values
# On any failure → INTERPRETATION_ERROR, fallback to empty defaults
# Logs metadata (topic count, classifications)

# Data Flow
# content_object → transcript + title + description
# → build prompt
# → LLM call → parse → validate SemanticsResponse
# → populate content_object["semantics"]
# → StageResult
# Edge Cases & Failure Scenarios

# No transcript → success=True with empty/null fields + warning
# Malformed JSON or invalid enum → INTERPRETATION_ERROR + fallback
# LLM timeout/network error → INTERPRETATION_ERROR + retry suggestion
# Overly vague response → validation rejects → empty fallback
# Transcript too long → same truncation as structure stage

# Extension Points

# Enum expansion (more content_types)
# Confidence scores per field
# Multi-model ensemble
# Prompt A/B testing framework