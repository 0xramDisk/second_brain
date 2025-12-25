Second Brain — Engineering & Code Quality Standards
1. Core Engineering Values

All code in this repository must optimize for:

Clarity over cleverness

Explainability over automation

Correctness over performance

Longevity over speed of delivery

Explicitness over convenience

If a piece of code is hard to explain to your future self, it is wrong.

2. Language & Tooling
2.1 Primary Language

Python 3.11+

2.2 Required Tooling

pytest for testing

ruff or flake8 for linting

black for formatting

mypy (gradually) for type safety

typer for CLI adapters

No alternative tools unless there is a strong, documented reason.

3. Project Structure Rules
3.1 Single Responsibility per File

Each file must answer exactly one question.

Bad:

process_and_store_and_score.py


Good:

fetch_transcript.py
analyze_structure.py
write_output.py

3.2 No Hidden Control Flow

Forbidden:

side effects during import

logic in __init__.py

implicit execution on module load

Allowed:

explicit execution via main()

explicit orchestration in runners

3.3 Orchestration vs Execution

Runners orchestrate stages

Stages execute logic

Adapters translate I/O

These must never be mixed.

4. Naming Conventions
4.1 Files & Modules

snake_case.py

Descriptive, not short

Bad:

proc.py


Good:

analyze_semantics.py

4.2 Classes

PascalCase

Nouns only

class StageResult:
    ...

4.3 Functions

snake_case

Verb-first

Explicit intent

Bad:

handle()


Good:

extract_video_id()

4.4 Variables

Descriptive

Avoid abbreviations unless obvious

Bad:

res, tmp, obj


Good:

stage_result
content_object
transcript_text

5. Type Safety & Data Contracts
5.1 Type Hints Are Mandatory

All public functions must include type hints.

def extract_video_id(url: str) -> str | None:
    ...


Internal helper functions should also be typed whenever reasonable.

5.2 Schema Is the Source of Truth

All content objects must conform to schema definitions

Schema changes require:

documentation

migration plan (if persisted)

No ad-hoc fields allowed.

6. Error Handling Rules (CRITICAL)
6.1 No Unhandled Exceptions in Core Logic

Forbidden:

raise Exception("something went wrong")


Required:

capture error

convert to structured failure

attach suggested fixes

6.2 Failures Are Data

All failures must include:

stage name

failure type

cause

impact

suggested fixes

Crashes are bugs.

6.3 Partial Failure Is Acceptable

The system must:

continue where possible

record degradation clearly

never hide missing data

7. Logging Standards
7.1 Structured Logging Only

Logs must be structured (dict / JSON-like), not free-form strings.

Each log entry must include:

run_id

stage_name

event_type

timestamp

message

metadata

7.2 Logging Levels

Use levels intentionally:

DEBUG → internal details

INFO → stage progress

WARNING → degraded behavior

ERROR → stage failure (non-fatal)

CRITICAL → system invariant violated

Never log secrets or PII.

8. Testing Standards
8.1 Tests Are Required, Not Optional

No feature is “done” without tests.

Minimum required:

unit tests for stages

schema validation tests

runner orchestration tests

8.2 Golden File Testing

For pipelines:

assert output shape

assert required fields

assert diagnostics presence

Do not assert exact AI text output.

8.3 Test Readability > Test Coverage

A readable test that explains behavior is better than 10 opaque ones.

9. AI-Specific Coding Rules
9.1 AI Calls Must Be Isolated

AI calls must live in clearly named modules

No AI calls inside:

runners

schema

core orchestration logic

9.2 AI Outputs Must Be Validated

Never trust AI output blindly.

Always validate:

schema

field presence

bounds

explanation fields

9.3 No Prompt Logic in Business Logic

Prompts must:

live in dedicated files or constants

be versioned

be logged (hash or ID)

10. CLI Standards

CLI modules contain no business logic

CLI responsibility:

parse args

call runner

print high-level status

Business logic lives elsewhere.

11. Documentation Rules
11.1 Docstrings Are Mandatory

All public:

modules

classes

functions

Must have docstrings explaining:

purpose

inputs

outputs

failure behavior

11.2 Comments Explain Why, Not What

Bad:

# increment i
i += 1


Good:

# Retry once to handle transient network failure

12. Refactoring Rules

Refactoring is encouraged only if:

behavior is preserved

tests pass unchanged

intent becomes clearer

Large refactors must be:

incremental

well-logged

reversible

13. Performance & Optimization

Performance optimization is:

secondary

data-driven

explicitly justified

Never optimize prematurely.

14. Security & Data Safety (Baseline)

No hardcoded secrets

No logging of sensitive content

Explicit handling of PII when applicable

Local-first by default

15. Code Review Checklist (Self-Review)

Before committing, ask:

Can I explain this file in 2 minutes?

Is the responsibility obvious?

Are failures explicit?

Are logs meaningful?

Could I delete this file later without breaking everything?

If the answer to any is “no”, fix it.

16. Final Principle

Code is a form of knowledge.
If it cannot be trusted, it does not belong in the system.

Write code the same way you want to write Punk Records:

deliberate

structured

explainable

worthy of keeping
