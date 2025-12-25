Second Brain — Engineering & Philosophy Guidelines
1. Purpose of This Project

Second Brain is a personal–to–collective knowledge system designed to:

Capture content with zero ambiguity

Transform raw information into structured understanding

Preserve what should not be lost

Resist entropy over time

Remain explainable, auditable, and reversible

This is not a note-taking app.
This is not an AI toy.

It is a knowledge lifecycle system.

2. Core Philosophy (Non-Negotiable)
2.1 Knowledge Has a Lifecycle

All knowledge passes through stages:

Experience → Capture → Interpretation → Structure → Canon → Maintenance


The system must respect this lifecycle.
Short-circuiting stages is forbidden.

2.2 Two Epistemic Zones

The vault is conceptually split into:

🧠 Raw Dump

High volume

Low friction

Messy

Temporary

Lossless

Purpose: Working memory

🧠 Punk Records

Low volume

High structure

Dense

Long-term

Canonical

Purpose: What humanity shouldn’t lose

Nothing enters Punk Records without intentional transformation.

2.3 Explainability Over Autonomy

When tradeoffs arise, prefer:

Clear explanation of failure + suggested fixes
over
Automatic correction

AI must assist, not obscure.

3. Architectural Principles

These principles apply to every module in the project.

3.1 Pipeline Over App

The system is composed of pipelines, not monolithic apps

Each pipeline is stage-based

Each stage has exactly one responsibility

3.2 Failures Are Data

No unhandled exceptions in business logic

Errors are captured, typed, and explained

Partial success is allowed

Every failure must include suggested fixes

Crashes are bugs.
Failures are information.

3.3 Scriptable First

Every meaningful action must be runnable as:

a CLI command

a script

a cron job

UI, Slack, Discord, or web interfaces are adapters, never owners of logic.

3.4 Deterministic Core

Core logic must be deterministic and testable

External calls (LLMs, APIs) must be isolated

Reprocessing must be possible without recomputation where feasible

3.5 Logs Are Part of the Product

Logging is not an afterthought.

Logs are:

structured

human-readable

machine-parsable

auditable

Logs represent system memory.

4. Modularity Rules
4.1 Business Logic Is Interface-Agnostic

Core logic must never know:

how it was triggered

who triggered it

where the output will be used

Adapters translate inputs → core contracts.

4.2 Each Module Must Be Replaceable

If a module cannot be:

deleted

rewritten

swapped

without collapsing the system — it is too tightly coupled.

4.3 Schema-First Development

Output schemas are defined before logic

Schemas are authoritative contracts

All modules must conform to schema definitions

5. AI Usage Guidelines
5.1 AI Is a Tool, Not an Authority

AI may:

extract

summarize

classify

suggest

AI may not:

silently decide permanence

rewrite canonical knowledge autonomously

hide reasoning

5.2 No Implicit Agents (Yet)

No autonomous looping behavior by default

No self-triggering actions

No hidden goals

Agent-like behavior is allowed only after:

the pipeline is trusted

failure modes are understood

governance rules are defined

5.3 AI Outputs Must Be Auditable

AI outputs must be:

structured

bounded

explainable

Exact wording is not tested.
Presence, shape, and intent are.

6. Testing Standards
6.1 Required Test Types

Every pipeline must have:

Schema tests

Stage unit tests

Runner/orchestrator tests

Golden-file tests (shape, not content)

6.2 AI Testing Philosophy

AI outputs are validated by:

field presence

type correctness

reasonable bounds

explanation existence

Never assert exact text equality.

7. Logging Standards

All logs must include:

run_id

stage_name

event_type (start / success / failure)

timestamp

message

metadata

Logs must tell a story of execution.

8. Vault Rules (Conceptual)
8.1 No Direct Writes to Punk Records

Punk Records content must be:

distilled

structured

linked

intentional

Raw input → interpretation → transformation → canon.

8.2 Threads as Sources of Truth

Threads represent current best understanding

Branches explore; threads synthesize

Threads evolve slowly

Canon beats novelty

9. Maintenance & Immune System Philosophy

The system must resist entropy over time.

Maintenance programs may:

detect redundancy

flag orphans

suggest merges

propose restructuring

They may not:

delete content silently

rewrite canon autonomously

Think immune system, not overlord.

10. Governance (Deferred, but Acknowledged)

The question:

Who is allowed to change a thread?

Is intentionally deferred.

All design must assume:

governance rules will evolve

versioning will matter

authorship and intent may become important

No irreversible decisions should be made before governance is defined.

11. Definition of “Production-Ready” (For This Project)

A feature is considered production-ready when:

It is modular

It is testable

It is explainable

It fails gracefully

It leaves an audit trail

It can be rerun safely

Performance is secondary to correctness and trust.

12. What This Project Is NOT Optimizing For

This project does NOT optimize for:

speed of feature delivery

flashy UI

aggressive automation

maximal AI autonomy

virality

It optimizes for:

clarity

longevity

trust

structural quality

intellectual honesty

13. Guiding Question (Read Often)

Before adding anything, ask:

Does this help preserve what should not be lost —
or does it add noise disguised as progress?

If unsure, don’t add it.

14. Final Note

Second Brain is a long-living system.

Decisions made here should still make sense:

in 5 years

with more data

with more contributors

with stricter governance

Build slowly.
Build clearly.
Build something that deserves to last.
