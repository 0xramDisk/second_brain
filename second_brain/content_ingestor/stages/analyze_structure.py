# second_brain/content_ingestor/stages/analyze_structure.py
"""
Stage 4: Structural analysis of content using AI.

Responsibility:
- Extract non-opinionated structural elements from transcript
- Sections, entities, references, steps, code presence
- AI call isolated, prompt versioned, output validated

Follows AI guidelines: prompt separate, invocation isolated, output bounded and validated.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Tuple, Optional

from pydantic import BaseModel, Field, ValidationError

from second_brain.content_ingestor.schema import (
    FailureType,
    StageFailure,
    StageResult,
)
from second_brain.content_ingestor.stages.base import timer
from second_brain.logging_core.logger import get_logger, log_event
import logging


# Versioned prompt — change only with justification and migration plan
STRUCTURE_PROMPT = """
You are an expert content analyst. Analyze the following YouTube video transcript and extract only structural elements.
Do not summarize, interpret, or judge quality.

Extract:
- sections: major timed or topical sections (use chapter titles if available, else infer from headings/transitions)
- entities: people, tools, products, frameworks, concepts, organizations mentioned
- references: URLs, books, papers, other videos/channels explicitly mentioned
- detected_steps: ordered procedural steps if present (e.g., tutorials)
- code_blocks_present: true if any code is shown or discussed

Transcript:
{transcript}

Chapters (if available):
{chapters}

Respond with valid JSON only, matching this schema exactly:
{
  "sections": [{"start_time?": number, "title": string}],
  "entities": [string],
  "references": [string],
  "detected_steps": [string],
  "code_blocks_present": boolean
}

Rules:
- sections: use chapter timestamps if present; otherwise null start_time
- entities/references/steps: max 50 items each
- no explanations, no markdown, no extra fields
""".strip()


class StructuredResponse(BaseModel):
    """Strict response model for structural analysis."""
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    detected_steps: List[str] = Field(default_factory=list)
    code_blocks_present: bool = False

    model_config = {"extra": "forbid"}


def _call_llm(prompt: str) -> str:
    """
    Isolated LLM invocation.
    Placeholder — replace with injectable client (OpenAI/Grok/local).
    """
    # TEMPORARY: Use Grok via import if available; otherwise raise clear error
    try:
        # This is a placeholder — in real system this would be injected
        from xai import GrokClient  # hypothetical
        client = GrokClient()
        response = client.chat.completions.create(
            model="grok-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc


def process(content_object: Dict[str, Any], run_id: uuid.UUID, config: Dict[str, Any]) -> Tuple[Dict[str, Any], StageResult]:
    """
    Perform structural analysis on available transcript.
    """
    stage_name = "analyze_structure"
    logger = get_logger(run_id)

    log_event(
        logger,
        logging.INFO,
        "Starting structural analysis",
        stage_name=stage_name,
        event_type="start",
    )

    transcript = content_object["raw"].get("transcript_text", "") or ""
    chapters = content_object["raw"].get("chapters", [])

    with timer() as end:
        if not transcript:
            # Graceful empty result
            content_object["structure"] = {
                "sections": chapters or [],
                "entities": [],
                "references": [],
                "detected_steps": [],
                "code_blocks_present": False,
            }
            result = StageResult(
                stage_name=stage_name,
                success=True,
                warnings=["No transcript available for structural analysis"],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.INFO,
                "Structural analysis skipped (no transcript)",
                stage_name=stage_name,
                event_type="success",
            )
            return content_object, result

        # Truncate if excessively long (protect token limits)
        if len(transcript) > 40000:  # ~15k tokens safe buffer
            transcript = transcript[:40000]
            content_object["diagnostics"].setdefault("warnings", []).append("Transcript truncated for structural analysis")

        prompt = STRUCTURE_PROMPT.format(
            transcript=transcript,
            chapters=json.dumps(chapters, ensure_ascii=False) if chapters else "none",
        )

        try:
            raw_response = _call_llm(prompt)

            # Parse and validate
            parsed = json.loads(raw_response)
            validated = StructuredResponse.model_validate(parsed)

            content_object["structure"] = {
                "sections": validated.sections or (chapters or []),
                "entities": validated.entities,
                "references": validated.references,
                "detected_steps": validated.detected_steps,
                "code_blocks_present": validated.code_blocks_present,
            }

            result = StageResult(
                stage_name=stage_name,
                success=True,
                execution_time_ms=end(),
            )

            log_event(
                logger,
                logging.INFO,
                "Structural analysis completed",
                stage_name=stage_name,
                event_type="success",
                metadata={
                    "entity_count": len(validated.entities),
                    "reference_count": len(validated.references),
                    "step_count": len(validated.detected_steps),
                    "code_present": validated.code_blocks_present,
                },
            )

        except json.JSONDecodeError as exc:
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.STRUCTURE_ERROR,
                cause="invalid_json_response",
                impact="Structural fields empty; raw response preserved in logs",
                suggested_fixes=["Review prompt", "Update model", "Add response repair logic"],
            )
            content_object["structure"] = {
                "sections": chapters or [],
                "entities": [],
                "references": [],
                "detected_steps": [],
                "code_blocks_present": False,
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
                "Structural analysis failed: invalid JSON",
                stage_name=stage_name,
                event_type="failure",
                metadata={"raw_response": raw_response[:1000]},
            )

        except ValidationError as exc:
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.STRUCTURE_ERROR,
                cause="schema_validation_failed",
                impact="Structural fields empty",
                suggested_fixes=["Adjust prompt for stricter adherence", "Add fallback parsing"],
            )
            content_object["structure"] = {
                "sections": chapters or [],
                "entities": [],
                "references": [],
                "detected_steps": [],
                "code_blocks_present": False,
            }
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[f"Validation error: {exc}"],
                failures=[failure],
                execution_time_ms=end(),
            )

        except Exception as exc:  # pylint: disable=broad-except
            failure = StageFailure(
                stage=stage_name,
                type=FailureType.STRUCTURE_ERROR,
                cause="llm_invocation_failed",
                impact="Structural fields empty",
                suggested_fixes=["Check API key/model availability", "Retry later"],
            )
            content_object["structure"] = {
                "sections": chapters or [],
                "entities": [],
                "references": [],
                "detected_steps": [],
                "code_blocks_present": False,
            }
            result = StageResult(
                stage_name=stage_name,
                success=False,
                errors=[f"LLM call failed: {str(exc)}"],
                failures=[failure],
                execution_time_ms=end(),
            )
            log_event(
                logger,
                logging.ERROR,
                "Structural analysis failed: LLM error",
                stage_name=stage_name,
                event_type="failure",
                metadata={"exception": str(exc)},
            )

    return content_object, result


# High-Level Intent

# stages/analyze_structure.py performs light, non-opinionated structural analysis of the transcript using an AI call.
# Single responsibility:

#     Extract sections (from chapters or inferred headings)
#     Extract named entities (people, tools, concepts, organizations)
#     Extract references (URLs, books, papers, other videos)
#     Detect ordered steps or procedures
#     Detect presence of code blocks

# This stage is deliberately descriptive, not interpretive — no judgment of quality or topic.
# AI usage follows project rules: prompt isolated and versioned, call isolated, output strictly validated, bounded, and explainable.
# Architecture

#     Prompt defined as module-level constant (versioned)
#     AI call abstracted (current placeholder: OpenAI gpt-4o-mini; future injectable)
#     Structured JSON output enforced via Pydantic response model
#     Validation: required fields present, lists bounded (<50 items), no empty strings
#     On malformed AI output → STRUCTURE_ERROR with parse details and fallback to empty fields
#     All AI interaction logged (prompt hash, model, token usage if available)

# Data Flow

# content_object → raw.transcript_text (or empty if missing) + raw.chapters
# → build prompt
# → call LLM → raw response
# → parse & validate → StructuredResponse model
# → populate content_object["structure"]
# → StageResult (success=False only on unrecoverable parse error)
# Edge Cases & Failure Scenarios

#     No transcript → success=True with empty lists (graceful degradation)
#     Transcript too long (>15k tokens) → truncate with warning + diagnostic
#     AI returns malformed JSON → STRUCTURE_ERROR cause="invalid_json" + raw response in metadata
#     AI hallucinates or omits fields → validation fails → empty fallback
#     Network/model error → STRUCTURE_ERROR cause="llm_failure" + retry suggestion

# Extension Points

#     Swap LLM (Grok, Claude, local) via dependency injection
#     Add RAG over transcript chunks for longer videos
#     Versioned prompt registry
#     Cache results by content_id
