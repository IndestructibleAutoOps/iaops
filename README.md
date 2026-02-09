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
----------------------------
- Config validation: Pipeline YAML is validated against `schemas/pipeline.schema.json`; role and policy files are schema-checked before use.
- Adapter auto-detect: Chooses python/node/go/generic based on present files in the project and required-files checks for that adapter (`src/indestructibleautoops/adapters`).
- File indexing and basic gatekeeping: Walks all files, blocks if file paths match configured narrative/question regexes (`scanner.py`).
- Normalization: Creates missing scaffolding directories (`.github/workflows`, `configs`, `schemas`, `src`, `tests`) before running (`normalize.py`).
- Planning: Emits `.indestructibleautoops/plan.json` describing missing CI workflow, missing Python project metadata, and adapter-specific repairs (e.g., create `src/` for Python) (`planner.py`).
- Patching in repair mode: If writes are allowed, missing planned files are created as placeholder text and a patch report is written (`patcher.py`).
- Verification: Checks that adapter-required files exist and records any missing items (`verifier.py`).
- Hashing and sealing: Produces SHA3-512/BLAKE3 manifests for the project (excluding `.git` and state dir) and writes evidence links (`hashing.py`, `sealing.py`).
- Event logging: Emits JSONL events validated by `schemas/event.schema.json` to the configured path for each step (`observability.py`).

Placeholders / fictional capabilities (not implemented)
-------------------------------------------------------
- No real multi-agent orchestration or policy execution despite the role/policy configs; they are only schema-validated and not enforced beyond simple checks.
- No vulnerability/secret/content scanning beyond filename regex matches; `security_scan` is a stub that always passes.
- No actual CI templates or dependency updates are applied; patching only writes minimal placeholder files when allowed.
- DAG in the config is only checked for cycles; step execution order is hard-coded, not driven by the DAG.
- Approval chains, continuous monitoring, and governance beyond hash/seal recording are placeholders with fixed responses.
