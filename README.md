IndestructibleAutoOps Skeleton-to-ClosedLoop

## Governance Engine

The governance engine drives every run: it loads the pipeline spec, resolves adapters, executes the DAG steps, records events, hashes evidence, and optionally repairs or seals a project. All flows (plan, repair, verify, seal) are orchestrated through the CLI entrypoint `indestructibleautoops`.

### First-class architecture elements

- PatchSet: planner + patcher collaborate to propose and apply a governed patch set, producing a patch report under `.indestructibleautoops/`.
- HashBoundary: hashing and sealing create immutable boundaries via hash manifests and seal evidence so downstream steps can trust prior state.
- ReplayEngine: the event stream (`.indestructibleautoops/governance/event-stream.jsonl`) captures traceable events so runs are replayable and auditable.
- ClosedLoop: end-to-end loop (normalize → plan → patch → verify → seal) keeps projects in compliance by feeding verification back into future plans.
