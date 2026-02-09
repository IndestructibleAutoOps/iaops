"""Tests for the whitelist / exemption system."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from indestructibleautoops.validation.whitelist import (
    ExemptionStatus,
    WhitelistManager,
    WhitelistRule,
)

# ── WhitelistRule unit tests ─────────────────────────────────────────


class TestWhitelistRule:
    def test_basic_match(self):
        rule = WhitelistRule(
            rule_id="r1",
            pattern="regression_.*",
            reason="test",
            approved_by="tester",
        )
        assert rule.matches_issue("regression_perf")
        assert not rule.matches_issue("threshold_min")

    def test_category_filter(self):
        rule = WhitelistRule(
            rule_id="r2",
            pattern=".*",
            reason="test",
            approved_by="tester",
            category="performance",
        )
        assert rule.matches_issue("any_issue", category="performance")
        assert not rule.matches_issue("any_issue", category="regression")
        # No category on issue → match (category filter only rejects mismatches)
        assert rule.matches_issue("any_issue", category=None)

    def test_file_pattern_filter(self):
        rule = WhitelistRule(
            rule_id="r3",
            pattern=".*",
            reason="test",
            approved_by="tester",
            file_pattern=r"src/.*\.py",
        )
        assert rule.matches_issue("x", file_path="src/main.py")
        assert not rule.matches_issue("x", file_path="docs/readme.md")

    def test_expired_rule(self):
        rule = WhitelistRule(
            rule_id="r4",
            pattern=".*",
            reason="test",
            approved_by="tester",
            expires_at=time.time() - 100,  # already expired
        )
        assert not rule.is_active()
        assert not rule.matches_issue("anything")
        assert rule.status == ExemptionStatus.EXPIRED

    def test_revoked_rule(self):
        rule = WhitelistRule(
            rule_id="r5",
            pattern=".*",
            reason="test",
            approved_by="tester",
            status=ExemptionStatus.REVOKED,
        )
        assert not rule.is_active()
        assert not rule.matches_issue("anything")

    def test_pending_review_rule(self):
        rule = WhitelistRule(
            rule_id="r6",
            pattern=".*",
            reason="test",
            approved_by="",
            status=ExemptionStatus.PENDING_REVIEW,
        )
        assert not rule.is_active()
        assert not rule.matches_issue("anything")

    def test_audit_log(self):
        rule = WhitelistRule(
            rule_id="r7",
            pattern="perf_.*",
            reason="test",
            approved_by="tester",
        )
        rule.record_match("perf_api")
        rule.record_match("perf_db")
        assert len(rule.audit_log) == 2
        assert rule.audit_log[0]["issue_id"] == "perf_api"

    def test_serialisation_roundtrip(self):
        rule = WhitelistRule(
            rule_id="r8",
            pattern="test_.*",
            reason="roundtrip test",
            approved_by="tester",
            expires_at=time.time() + 3600,
            category="regression",
            file_pattern=r"src/.*",
            max_severity="critical",
        )
        data = rule.to_dict()
        restored = WhitelistRule.from_dict(data)
        assert restored.rule_id == rule.rule_id
        assert restored.pattern == rule.pattern
        assert restored.category == rule.category
        assert restored.max_severity == rule.max_severity


# ── WhitelistManager unit tests ──────────────────────────────────────


class TestWhitelistManager:
    def test_add_and_lookup(self):
        mgr = WhitelistManager()
        rule = WhitelistRule(rule_id="m1", pattern=".*", reason="t", approved_by="x")
        mgr.add_rule(rule)
        assert mgr.get_rule("m1") is rule
        assert len(mgr.get_active_rules()) == 1

    def test_duplicate_rule_rejected(self):
        mgr = WhitelistManager()
        rule = WhitelistRule(rule_id="dup", pattern=".*", reason="t", approved_by="x")
        mgr.add_rule(rule)
        with pytest.raises(ValueError, match="Duplicate"):
            mgr.add_rule(rule)

    def test_remove_rule(self):
        mgr = WhitelistManager()
        rule = WhitelistRule(rule_id="rm1", pattern=".*", reason="t", approved_by="x")
        mgr.add_rule(rule)
        assert mgr.remove_rule("rm1")
        assert rule.status == ExemptionStatus.REVOKED
        assert len(mgr.get_active_rules()) == 0

    def test_blocker_never_suppressed(self):
        mgr = WhitelistManager()
        mgr.add_rule(
            WhitelistRule(
                rule_id="catch_all",
                pattern=".*",
                reason="catch all",
                approved_by="x",
                max_severity="critical",
            )
        )
        suppressed, _ = mgr.should_suppress("any_issue", severity="blocker")
        assert not suppressed

    def test_severity_gate(self):
        mgr = WhitelistManager()
        mgr.add_rule(
            WhitelistRule(
                rule_id="low_only",
                pattern=".*",
                reason="low sev only",
                approved_by="x",
                max_severity="warning",
            )
        )
        # warning → suppressed
        suppressed, _ = mgr.should_suppress("issue1", severity="warning")
        assert suppressed
        # error → NOT suppressed (above max_severity)
        suppressed, _ = mgr.should_suppress("issue2", severity="error")
        assert not suppressed

    def test_suppression_tracking(self):
        mgr = WhitelistManager()
        mgr.add_rule(
            WhitelistRule(
                rule_id="track",
                pattern="perf_.*",
                reason="t",
                approved_by="x",
            )
        )
        mgr.should_suppress("perf_api", severity="error")
        mgr.should_suppress("perf_db", severity="warning")
        mgr.should_suppress("other_issue", severity="error")  # no match

        stats = mgr.get_stats()
        assert stats["total_suppressions"] == 2
        assert len(stats["match_history"]) == 2

    def test_persistence_roundtrip(self, tmp_path: Path):
        mgr = WhitelistManager()
        mgr.add_rule(
            WhitelistRule(
                rule_id="persist1",
                pattern="test_.*",
                reason="persist test",
                approved_by="tester",
            )
        )
        mgr.should_suppress("test_issue", severity="error")

        save_path = tmp_path / "whitelist.json"
        mgr.save(save_path)

        loaded = WhitelistManager.load(save_path)
        assert len(loaded.get_active_rules()) == 1
        assert loaded.get_rule("persist1") is not None
        assert len(loaded.get_rule("persist1").audit_log) == 1

    def test_load_nonexistent_returns_empty(self, tmp_path: Path):
        mgr = WhitelistManager.load(tmp_path / "nonexistent.json")
        assert len(mgr.get_active_rules()) == 0

    def test_expired_rules_detected(self):
        mgr = WhitelistManager()
        mgr.add_rule(
            WhitelistRule(
                rule_id="exp1",
                pattern=".*",
                reason="t",
                approved_by="x",
                expires_at=time.time() - 1,
            )
        )
        expired = mgr.get_expired_rules()
        assert len(expired) == 1
        assert expired[0].rule_id == "exp1"

    def test_audit_report(self):
        mgr = WhitelistManager()
        mgr.add_rule(
            WhitelistRule(
                rule_id="audit1",
                pattern="perf_.*",
                reason="flaky perf",
                approved_by="lead",
            )
        )
        mgr.should_suppress("perf_api", severity="error")
        report = mgr.get_audit_report()
        assert "WHITELIST AUDIT REPORT" in report
        assert "perf_api" in report
        assert "audit1" in report


# ── Integration with StrictValidator ─────────────────────────────────


class TestWhitelistIntegration:
    def test_whitelist_suppresses_regression(self, tmp_path: Path):
        """End-to-end: a whitelisted regression is downgraded to INFO."""
        from indestructibleautoops.validation.regression import (
            RegressionSuite,
            RegressionTest,
        )
        from indestructibleautoops.validation.strict_validator import (
            StrictValidationConfig,
            StrictValidator,
        )

        # Create whitelist file — suppress both metric and perf regressions
        wl_path = tmp_path / "whitelist.json"
        wl_data = {
            "version": 1,
            "rules": [
                {
                    "rule_id": "allow_perf_drop",
                    "pattern": "(metric_regression|perf_regression)_.*",
                    "reason": "Known CI variance in test metrics",
                    "approved_by": "tech-lead",
                    "max_severity": "critical",
                    "status": "active",
                }
            ],
        }
        wl_path.write_text(json.dumps(wl_data))

        config = StrictValidationConfig(
            project_root=str(tmp_path),
            baseline_dir=str(tmp_path / ".baselines"),
            output_dir=str(tmp_path / ".validation"),
            whitelist_path=str(wl_path),
            strict_mode=True,
        )
        validator = StrictValidator(config)

        call_count = 0

        def metric_test(context):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return {"performance_metric": 70}  # regression
            return {"performance_metric": 100}

        suite = RegressionSuite(
            suite_id="wl_test",
            name="Whitelist Test Suite",
            tests=[
                RegressionTest(
                    test_id="wl_perf",
                    name="WL Perf Test",
                    description="test",
                    test_function=metric_test,
                    category="regression",
                )
            ],
        )
        validator.add_regression_suite(suite)

        # First run → baseline
        validator.validate_all()
        validator.create_baseline()

        # Second run → regression, but whitelisted
        validator.load_baseline()
        results = validator.validate_all()

        # The regression should be suppressed → overall pass
        assert results["overall_passed"], (
            f"Expected pass after whitelist suppression, "
            f"got blocking={results['summary']['blocking_issues']}"
        )
        assert results["summary"]["suppressed_issues"] > 0

    def test_blocker_not_suppressed_by_whitelist(self, tmp_path: Path):
        """BLOCKER issues (result mismatches) must never be suppressed."""
        from indestructibleautoops.validation.regression import (
            RegressionSuite,
            RegressionTest,
        )
        from indestructibleautoops.validation.strict_validator import (
            StrictValidationConfig,
            StrictValidator,
        )

        wl_path = tmp_path / "whitelist.json"
        wl_data = {
            "version": 1,
            "rules": [
                {
                    "rule_id": "catch_all",
                    "pattern": ".*",
                    "reason": "try to suppress everything",
                    "approved_by": "x",
                    "max_severity": "critical",
                    "status": "active",
                }
            ],
        }
        wl_path.write_text(json.dumps(wl_data))

        config = StrictValidationConfig(
            project_root=str(tmp_path),
            baseline_dir=str(tmp_path / ".baselines"),
            output_dir=str(tmp_path / ".validation"),
            whitelist_path=str(wl_path),
            strict_mode=True,
        )
        validator = StrictValidator(config)

        call_count = 0

        def mismatch_test(context):
            """Returns different non-numeric result on second call → BLOCKER."""
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return {"status": "degraded", "version": "2.0"}
            return {"status": "healthy", "version": "1.0"}

        suite = RegressionSuite(
            suite_id="blocker_test",
            name="Blocker Test Suite",
            tests=[
                RegressionTest(
                    test_id="blocker_mismatch",
                    name="Blocker Mismatch Test",
                    description="test",
                    test_function=mismatch_test,
                    category="regression",
                )
            ],
        )
        validator.add_regression_suite(suite)

        # First run → baseline
        validator.validate_all()
        validator.create_baseline()

        # Second run → result mismatch = BLOCKER
        validator.load_baseline()
        results = validator.validate_all()

        # BLOCKER should NOT be suppressed even with catch-all whitelist
        assert results["summary"]["blocking_issues"] > 0
        assert not results["overall_passed"]
