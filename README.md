IndestructibleAutoOps Skeleton-to-ClosedLoop
============================================

## Governance Engine

The governance engine drives every run: it loads the pipeline spec, resolves adapters, executes the DAG steps, records events, hashes evidence, and optionally repairs or seals a project. All flows (plan, repair, verify, seal) are orchestrated through the CLI entrypoint `indestructibleautoops`.

### First-class architecture elements

- PatchSet: planner + patcher collaborate to propose and apply a governed patch set, producing a patch report under `.indestructibleautoops/`.
- HashBoundary: hashing and sealing create immutable boundaries via hash manifests and seal evidence so downstream steps can trust prior state.
- ReplayEngine: the event stream (`.indestructibleautoops/governance/event-stream.jsonl`) captures traceable events so runs are replayable and auditable.
- ClosedLoop: end-to-end loop (normalize → plan → patch → verify → seal) keeps projects in compliance by feeding verification back into future plans.

Purpose
-------
- Minimal demo engine that reads a pipeline config (`configs/indestructibleautoops.pipeline.yaml`) and runs a fixed set of steps against a local project directory.
- CLI entrypoint: `python -m indestructibleautoops <command>` with modes `run`, `plan`, `verify`, `seal`, and `clean`.

How to run
----------
- Install: `pip install -e .[dev]`
- Plan only (no writes): `python -m indestructibleautoops plan --config configs/indestructibleautoops.pipeline.yaml --project .`
- Repair/apply (writes placeholders for missing files): `python -m indestructibleautoops run --config configs/indestructibleautoops.pipeline.yaml --project .`
- Verify only: `python -m indestructibleautoops verify --config configs/indestructibleautoops.pipeline.yaml --project .`
- Seal only: `python -m indestructibleautoops seal --config configs/indestructibleautoops.pipeline.yaml --project .`
- Clean engine state: `python -m indestructibleautoops clean`

Implemented and usable today
-----------------------------
- Config validation: Pipeline YAML is validated against `schemas/pipeline.schema.json`; role and policy files are schema-checked before use.
- Adapter auto-detect: Chooses python/node/go/generic based on present files in the project and required-files checks for that adapter (`src/indestructibleautoops/adapters`).
- File indexing and basic gatekeeping: Walks all files, blocks if file paths match configured narrative/question regexes (`scanner.py`).
- Normalization: Creates missing scaffolding directories (`.github/workflows`, `configs`, `schemas`, `src`, `tests`) before running (`normalize.py`).
- Planning: Emits `.indestructibleautoops/plan.json` describing missing CI workflow, missing Python project metadata, and adapter-specific repairs (e.g., create `src/` for Python) (`planner.py`).
- Patching in repair mode: If writes are allowed, missing planned files are created as placeholder text and a patch report is written (`patcher.py`).
- Verification: Checks that adapter-required files exist and records any missing items (`verifier.py`).
- Hashing and sealing: Produces SHA3-512/BLAKE3 manifests for the project (excluding `.git` and state dir) and writes evidence links (`hashing.py`, `sealing.py`).
- Event logging: Emits JSONL events validated by `schemas/event.schema.json` to the configured path for each step (`observability.py`).

Orchestration and DAG Execution
-------------------------------
- DAG-driven step execution: The main Engine.run() method executes steps in topological order based on the configured DAG dependencies.
- PipelineDAG: A complete DAG implementation with cycle detection, topological sorting, and execution context management (`orchestration.py`).
- Shared topological sort utilities: Common DAG algorithms available via `graph.py` for use across the codebase.
- OrchestrationEngine: Lightweight DAG-based orchestration engine with step registration and execution tracking (`engine.py`).
- PipelineEngine: Alternative DAG-driven pipeline execution with step reporting (`engine.py`).

Security and Governance
-----------------------
- SecurityScanner: Structured security scanner that inspects file paths and content for sensitive data patterns including:
  - Secret detection: API keys, tokens, passwords, auth strings
  - Risk patterns: XSS vulnerabilities, SQL injection attempts, path traversal attempts
  - Filename blocking: Blocks files with extensions like .env, .key, .pem, .secret
  - Content hashing: SHA256 hashes for content integrity verification
- NarrativeSecretScanner: File path-based scanner that blocks files matching narrative and question patterns (`scanner.py`).
- GovernanceSystem: Approval and monitoring system with strategy validation and continuous monitoring capabilities (`orchestration.py`).

CI and Dependencies Management
------------------------------
- CIManager: CI template management with the ability to apply CI workflow templates and update dependencies (`orchestration.py`).
- Template application: Generates minimal CI workflow templates in `.indestructibleautoops/ci/` directory.
- Dependency updates: Supports dependency logging when ALLOW_UPDATES environment variable is set.

Multi-Agent Orchestration
--------------------------
- AgentOrchestrator: Orchestrates multiple agents following DAG order with:
  - Strategy validation
  - Governance approval workflow
  - Security scanning integration
  - CI manager integration
  - Context propagation between agents