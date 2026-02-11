from __future__ import annotations

import json
from pathlib import Path

from scripts.ci.build_sign_show import build_image, generate_sbom, sign_image
from scripts.ci.dependericy_check import evaluate_dependencies, summarize
from scripts.ci.verify_gate import verify_sbom
from scripts.monitoring.anomaly_detector import AnomalyDetector
from scripts.monitoring.audit_logger import AuditLogger


def test_build_sign_commands_are_emitted(tmp_path: Path):
    image = "ghcr.io/example/app:dev"
    build_result = build_image(image, dry_run=True)
    assert build_result.command[:2] == ["docker", "build"]

    sbom_path = tmp_path / "sbom.json"
    sbom_result = generate_sbom(image, output_path=str(sbom_path), dry_run=True)
    assert sbom_result.command[0] == "syft"

    sign_result = sign_image(image, key_ref="cosign.key", annotations={"owner": "platform"}, dry_run=True)
    assert "--key" in sign_result.command
    assert any(item.startswith("owner=") for item in sign_result.command if "owner=" in item)


def test_verify_gate_accepts_valid_sbom(tmp_path: Path):
    sbom_path = tmp_path / "sbom.json"
    sbom_path.write_text(json.dumps({"components": [{"name": "demo", "version": "1.0.0"}]}), encoding="utf-8")
    assert verify_sbom(str(sbom_path))


def test_dependency_gate_flags_critical(tmp_path: Path):
    sbom = {
        "components": [{"bom-ref": "pkg:demo", "name": "demo", "version": "1.0.0", "licenses": [{"license": {"name": "Apache-2.0"}}]}],
        "vulnerabilities": [{"id": "CVE-TEST", "severity": "critical", "affects": [{"ref": "pkg:demo"}]}],
    }
    findings = evaluate_dependencies(sbom, allowed_licenses={"Apache-2.0"})
    total, blockers = summarize(findings)
    assert total == 1
    assert blockers == 1


def test_audit_logger_writes_json(tmp_path: Path):
    log_path = tmp_path / "audit.log"
    entry = AuditLogger(log_path=str(log_path)).log("deploy", subject="release-1")
    persisted = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["action"] == "deploy"
    assert persisted["severity"] == "info"


def test_anomaly_detector_flags_high_priority():
    detector = AnomalyDetector(min_priority="critical")
    events = [
        {"rule": "spawn_shell", "priority": "warning", "output": "benign"},
        {"rule": "sensitive_mount", "priority": "critical", "output": "detected"},
    ]
    anomalies = detector.scan_events(events)
    assert len(anomalies) == 1
    assert anomalies[0].rule == "sensitive_mount"
