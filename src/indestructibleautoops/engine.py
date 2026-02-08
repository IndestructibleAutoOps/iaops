from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .adapters.generic import AdapterContext, GenericAdapter, detect_adapter, load_adapters_config
from .adapters.go import GoAdapter
from .adapters.node import NodeAdapter
from .adapters.python import PythonAdapter
from .graph import DAG, dag_is_acyclic
from .hashing import Hasher
from .io import ensure_dir, read_text, write_text
from .normalize import Normalizer
from .observability import EventStream
from .patcher import Patcher
from .planner import Planner
from .scanner import NarrativeSecretScanner
from .sealing import Sealer
from .verifier import Verifier, load_jsonschema


@dataclass(frozen=True)
class EngineConfig:
    raw: dict[str, Any]
    config_path: Path
    project_root: Path
    mode: str

    @property
    def state_dir(self) -> Path:
        return self.project_root / self.raw["spec"]["stateDir"]

    @property
    def evidence_dir(self) -> Path:
        return self.project_root / self.raw["spec"]["evidenceDir"]

    @property
    def event_stream_path(self) -> Path:
        return self.project_root / self.raw["spec"]["eventStream"]

    @property
    def outputs(self) -> dict[str, str]:
        return self.raw["spec"]["outputs"]

    @property
    def inputs(self) -> dict[str, Any]:
        return self.raw["spec"]["inputs"]

    @property
    def dag_nodes(self) -> list[dict[str, Any]]:
        return self.raw["spec"]["dag"]["nodes"]

    @property
    def allow_writes(self) -> bool:
        return bool(self.raw["spec"].get("repair", {}).get("allowWrites", False))

    @property
    def governance(self) -> dict[str, Any]:
        return self.raw["spec"]["governance"]

    @property
    def config_base(self) -> Path:
        """The base directory for resolving input paths in the config.

        Config paths like 'configs/...' and 'schemas/...' are relative to the
        repository root that contains the config file, i.e. config_path's
        grandparent when the config lives in a 'configs/' subdirectory.
        We walk up from config_path.parent until we find a directory that
        makes the relative path resolve, falling back to config_path.parent.
        """
        return self.config_path.resolve().parent.parent

    def resolve_input(self, rel: str) -> Path:
        """Resolve an input path: try config_base first, then project_root."""
        p = self.config_base / rel
        if p.exists():
            return p
        p2 = self.project_root / rel
        if p2.exists():
            return p2
        return p


class Engine:
    def __init__(self, cfg: EngineConfig):
        self.cfg = cfg
        ensure_dir(self.cfg.state_dir)
        ensure_dir(self.cfg.evidence_dir)
        ensure_dir(self.cfg.event_stream_path.parent)
        self.events = EventStream(
            self.cfg.event_stream_path,
            schema_path=self.cfg.resolve_input(self.cfg.inputs["schemas"]["event"]),
        )
        self.hasher = Hasher(self.cfg.governance["hash"]["algorithms"])
        self.scanner = NarrativeSecretScanner(
            narrative_patterns=self.cfg.governance["banNarrative"]["patterns"],
            forbid_question_patterns=self.cfg.governance["forbidQuestions"]["patterns"],
            secret_patterns=None,
        )
        adapters_cfg = load_adapters_config(
            self.cfg.resolve_input(self.cfg.inputs["adaptersConfig"])
        )
        adapter_id = detect_adapter(self.cfg.project_root, adapters_cfg)
        self.adapter = self._build_adapter(adapter_id)

    @staticmethod
    def from_config(config_path: Path, project_root: Path, mode: str | None = None) -> Engine:
        raw = yaml.safe_load(read_text(config_path))
        config_base = config_path.resolve().parent.parent
        schema_rel = raw["spec"]["inputs"]["schemas"]["pipeline"]
        schema_path = config_base / schema_rel
        if not schema_path.exists():
            schema_path = project_root / schema_rel
        load_jsonschema(schema_path).validate(raw)
        m = mode or raw["spec"]["modes"]["default"]
        cfg = EngineConfig(raw=raw, config_path=config_path, project_root=project_root, mode=m)
        return Engine(cfg)

    def _build_adapter(self, adapter_id: str):
        ctx = AdapterContext(project_root=self.cfg.project_root, state_dir=self.cfg.state_dir)
        if adapter_id == "python":
            return PythonAdapter(ctx)
        if adapter_id == "node":
            return NodeAdapter(ctx)
        if adapter_id == "go":
            return GoAdapter(ctx)
        return GenericAdapter(ctx)

    def run(self) -> dict[str, Any]:
        trace_id = self.events.new_trace_id()
        dag = DAG.from_nodes(self.cfg.dag_nodes)
        if not dag_is_acyclic(dag):
            self.events.emit(trace_id, "governance", "dag_cycle", {"ok": False})
            return {"ok": False, "error": "dag_cycle", "traceId": trace_id}

        steps = [
            ("interface_metadata_parse", self.step_interface_metadata_parse),
            ("parameter_validation", self.step_parameter_validation),
            ("permission_resolution", self.step_permission_resolution),
            ("security_assessment", self.step_security_assessment),
            ("approval_chain_validation", self.step_approval_chain_validation),
            ("tool_execution", self.step_tool_execution),
            ("history_immutable", self.step_history_immutable),
            ("continuous_monitoring", self.step_continuous_monitoring),
        ]

        outputs: dict[str, Any] = {"ok": True, "traceId": trace_id, "mode": self.cfg.mode}
        for step_id, fn in steps:
            self.events.emit(trace_id, step_id, "start", {})
            out = fn(trace_id=trace_id, step_id=step_id)
            self.events.emit(trace_id, step_id, "end", {"result": out})
            if not out.get("ok", False):
                outputs["ok"] = False
                outputs["failedStep"] = step_id
                outputs["error"] = out.get("error", "unknown")
                break
            outputs[step_id] = out

        return outputs

    def step_interface_metadata_parse(self, trace_id: str, step_id: str) -> dict[str, Any]:
        index = self.adapter.index()
        snapshot = self.adapter.snapshot()
        scanner_findings = self.scanner.scan_index(index)
        self.events.emit(trace_id, step_id, "findings", scanner_findings)
        if scanner_findings["blocked"]:
            return {"ok": False, "error": scanner_findings["reason"], "findings": scanner_findings}
        return {
            "ok": True,
            "adapter": self.adapter.name,
            "files": len(index["files"]),
            "snapshot": snapshot,
        }

    def step_parameter_validation(self, trace_id: str, step_id: str) -> dict[str, Any]:
        policies_path = self.cfg.resolve_input(self.cfg.inputs["policiesConfig"])
        roles_path = self.cfg.resolve_input(self.cfg.inputs["rolesRegistry"])
        policies = yaml.safe_load(read_text(policies_path))
        roles = yaml.safe_load(read_text(roles_path))

        load_jsonschema(self.cfg.resolve_input(self.cfg.inputs["schemas"]["policies"])).validate(
            policies
        )
        load_jsonschema(self.cfg.resolve_input(self.cfg.inputs["schemas"]["roles"])).validate(roles)

        return {"ok": True, "policiesLoaded": True, "rolesLoaded": True}

    def step_permission_resolution(self, trace_id: str, step_id: str) -> dict[str, Any]:
        allow_writes = self.cfg.allow_writes and (self.cfg.mode in {"repair"})
        return {"ok": True, "allowWrites": allow_writes}

    def step_security_assessment(self, trace_id: str, step_id: str) -> dict[str, Any]:
        findings = self.adapter.security_scan()
        if findings.get("blocked"):
            return {"ok": False, "error": "security_blocked", "findings": findings}
        return {"ok": True, "findings": findings}

    def step_approval_chain_validation(self, trace_id: str, step_id: str) -> dict[str, Any]:
        return {"ok": True, "approval": "local-policy-auto"}

    def step_tool_execution(self, trace_id: str, step_id: str) -> dict[str, Any]:
        normalizer = Normalizer(self.cfg.project_root)
        planner = Planner(self.cfg.project_root, self.adapter)
        patcher = Patcher(
            self.cfg.project_root,
            allow_writes=(self.cfg.mode == "repair" and self.cfg.allow_writes),
        )
        verifier = Verifier(self.cfg.project_root, self.adapter)

        normalized = normalizer.run()
        plan = planner.build_plan()
        plan_path = self.cfg.project_root / self.cfg.outputs["planFile"]
        ensure_dir(plan_path.parent)
        write_text(plan_path, json.dumps(plan, indent=2, sort_keys=True))

        if self.cfg.mode == "plan":
            return {
                "ok": True,
                "normalized": normalized,
                "planOnly": True,
                "planFile": str(plan_path),
            }

        patch_report = patcher.apply(plan)
        patch_path = self.cfg.project_root / self.cfg.outputs["patchReport"]
        ensure_dir(patch_path.parent)
        write_text(patch_path, json.dumps(patch_report, indent=2, sort_keys=True))

        verify_report = verifier.run()
        verify_path = self.cfg.project_root / self.cfg.outputs["verifyReport"]
        ensure_dir(verify_path.parent)
        write_text(verify_path, json.dumps(verify_report, indent=2, sort_keys=True))

        if self.cfg.mode == "verify":
            return {
                "ok": verify_report["ok"],
                "normalized": normalized,
                "verified": True,
                "verify": verify_report,
            }

        return {
            "ok": verify_report["ok"],
            "normalized": normalized,
            "patched": patch_report,
            "verify": verify_report,
        }

    def step_history_immutable(self, trace_id: str, step_id: str) -> dict[str, Any]:
        manifest = self.hasher.hash_tree(
            self.cfg.project_root, exclude_dirs={self.cfg.state_dir.name, ".git"}
        )
        hist_path = self.cfg.evidence_dir / "hash-manifest.json"
        write_text(hist_path, json.dumps(manifest, indent=2, sort_keys=True))
        return {"ok": True, "hashManifest": str(hist_path), "files": len(manifest["files"])}

    def step_continuous_monitoring(self, trace_id: str, step_id: str) -> dict[str, Any]:
        if self.cfg.mode in {"seal", "repair", "verify"}:
            sealer = Sealer(
                self.cfg.project_root,
                self.cfg.state_dir,
                self.cfg.evidence_dir,
                self.hasher,
            )
            seal = sealer.seal()
            if self.cfg.mode == "seal" and not seal["ok"]:
                return {"ok": False, "error": "seal_failed", "seal": seal}
            return {"ok": True, "sealed": seal}
        return {"ok": True, "monitoring": "noop"}
