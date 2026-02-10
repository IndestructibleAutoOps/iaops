"""Tests for the ValidationEngine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from indestructibleautoops.validation.engine import ValidationEngine
from indestructibleautoops.validation.file_validator import FileCheckValidator
from indestructibleautoops.validation.validator import (
    BaseValidator,
    Severity,
    ValidationIssue,
    ValidationResult,
)


class _AlwaysPassValidator(BaseValidator):
    """Test helper: always passes."""

    def validate(self, context: dict[str, Any]) -> ValidationResult:
        return ValidationResult(validator_name=self.name)


class _AlwaysFailValidator(BaseValidator):
    """Test helper: always produces a CRITICAL issue."""

    def validate(self, context: dict[str, Any]) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        result.add_issue(
            ValidationIssue(
                issue_id="forced_failure",
                severity=Severity.CRITICAL,
                category="test",
                title="Forced failure",
                description="This validator always fails.",
            )
        )
        return result


class TestValidationEngine:
    def test_empty_pipeline(self, tmp_path: Path):
        engine = ValidationEngine(
            project_root=str(tmp_path),
            output_dir=str(tmp_path / ".validation"),
        )
        results = engine.run()
        assert results["overall_passed"]
        assert results["summary"]["total_validators"] == 0

    def test_register_and_run(self, tmp_path: Path):
        engine = ValidationEngine(
            project_root=str(tmp_path),
            output_dir=str(tmp_path / ".validation"),
        )
        engine.register("pass1", _AlwaysPassValidator(name="pass1"))
        engine.register("pass2", _AlwaysPassValidator(name="pass2"))

        results = engine.run()
        assert results["overall_passed"]
        assert results["summary"]["total_validators"] == 2
        assert results["summary"]["passed_validators"] == 2

    def test_pipeline_order(self, tmp_path: Path):
        engine = ValidationEngine(
            project_root=str(tmp_path),
            output_dir=str(tmp_path / ".validation"),
        )
        engine.register("alpha", _AlwaysPassValidator(name="alpha"))
        engine.register("beta", _AlwaysPassValidator(name="beta"))
        engine.register("gamma", _AlwaysPassValidator(name="gamma"))

        assert engine.pipeline_names == ["alpha", "beta", "gamma"]

    def test_failure_blocks(self, tmp_path: Path):
        engine = ValidationEngine(
            project_root=str(tmp_path),
            output_dir=str(tmp_path / ".validation"),
        )
        engine.register("good", _AlwaysPassValidator(name="good"))
        engine.register("bad", _AlwaysFailValidator(name="bad"))

        results = engine.run()
        assert not results["overall_passed"]
        assert results["summary"]["blocking_issues"] > 0

    def test_whitelist_integration(self, tmp_path: Path):
        wl_path = tmp_path / "whitelist.json"
        wl_data = {
            "version": 1,
            "rules": [
                {
                    "rule_id": "suppress_forced",
                    "pattern": "forced_failure",
                    "reason": "Test suppression",
                    "approved_by": "tester",
                    "max_severity": "critical",
                    "status": "active",
                }
            ],
        }
        wl_path.write_text(json.dumps(wl_data))

        engine = ValidationEngine(
            project_root=str(tmp_path),
            output_dir=str(tmp_path / ".validation"),
            whitelist_path=str(wl_path),
        )
        engine.register("bad", _AlwaysFailValidator(name="bad"))

        results = engine.run()
        # Failure should be suppressed
        assert results["overall_passed"]
        assert results["summary"]["suppressed_issues"] == 1

    def test_baseline_roundtrip(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("# a")

        engine = ValidationEngine(
            project_root=str(tmp_path),
            baseline_dir=str(tmp_path / ".baselines"),
            output_dir=str(tmp_path / ".validation"),
        )
        engine.register("files", FileCheckValidator(strict_mode=True))

        # First run + save baseline
        engine.run()
        engine.create_baseline()

        baseline_file = tmp_path / ".baselines" / "files.json"
        assert baseline_file.exists()

        # Load baseline and run again
        engine.load_baseline()
        results = engine.run()
        assert results["summary"]["total_validators"] == 1

    def test_results_saved(self, tmp_path: Path):
        engine = ValidationEngine(
            project_root=str(tmp_path),
            output_dir=str(tmp_path / ".validation"),
        )
        engine.register("pass1", _AlwaysPassValidator(name="pass1"))
        engine.run()

        latest = tmp_path / ".validation" / "validation_latest.json"
        assert latest.exists()
        data = json.loads(latest.read_text())
        assert data["overall_passed"]
