"""Tests for the FunctionalValidator."""

from __future__ import annotations

from typing import Any

from indestructibleautoops.validation.functional_validator import (
    FunctionalTest,
    FunctionalValidator,
)
from indestructibleautoops.validation.validator import Severity


class TestFunctionalValidator:
    def test_basic_run_no_baseline(self):
        """First run with no baseline should pass."""

        def healthy_check(context: dict[str, Any]) -> dict[str, Any]:
            return {"status": "healthy", "uptime": 99.9, "errors": 0}

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(
            FunctionalTest(
                test_id="health",
                name="Health Check",
                test_function=healthy_check,
            )
        )
        result = validator.validate({"project_root": "."})
        assert result.passed
        assert "health" in result.metrics

    def test_structural_regression_detected(self):
        """Removing a key from output should produce a BLOCKER."""
        call_count = 0

        def changing_output(context: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return {"status": "healthy"}  # missing 'version'
            return {"status": "healthy", "version": "1.0"}

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(
            FunctionalTest(
                test_id="api",
                name="API Check",
                test_function=changing_output,
            )
        )

        # First run — establishes baseline
        result1 = validator.validate({"project_root": "."})
        assert result1.passed

        # Second run — structural change
        result2 = validator.validate({"project_root": "."})
        assert not result2.passed
        blockers = [i for i in result2.issues if i.severity == Severity.BLOCKER]
        assert len(blockers) >= 1
        assert "structural" in blockers[0].issue_id.lower()

    def test_numeric_regression_detected(self):
        """A >10% drop in a numeric metric should produce CRITICAL."""
        call_count = 0

        def metric_output(context: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return {"score": 70.0}  # 30% drop
            return {"score": 100.0}

        validator = FunctionalValidator(strict_mode=True, metric_threshold=0.10)
        validator.add_test(
            FunctionalTest(
                test_id="scoring",
                name="Score Test",
                test_function=metric_output,
            )
        )

        # First run
        result1 = validator.validate({"project_root": "."})
        assert result1.passed

        # Second run — regression
        result2 = validator.validate({"project_root": "."})
        assert not result2.passed
        critical = [i for i in result2.issues if i.severity == Severity.CRITICAL]
        assert len(critical) >= 1

    def test_no_regression_within_threshold(self):
        """A small drop within threshold should not trigger."""
        call_count = 0

        def stable_output(context: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return {"score": 95.0}  # 5% drop, within 10% threshold
            return {"score": 100.0}

        validator = FunctionalValidator(strict_mode=True, metric_threshold=0.10)
        validator.add_test(
            FunctionalTest(
                test_id="stable",
                name="Stable Test",
                test_function=stable_output,
            )
        )

        result1 = validator.validate({"project_root": "."})
        assert result1.passed

        result2 = validator.validate({"project_root": "."})
        assert result2.passed

    def test_test_function_exception(self):
        """A test that raises should produce CRITICAL."""

        def failing_test(context: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("connection refused")

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(
            FunctionalTest(
                test_id="failing",
                name="Failing Test",
                test_function=failing_test,
            )
        )
        result = validator.validate({"project_root": "."})
        assert not result.passed
        assert any("connection refused" in i.description for i in result.issues)

    def test_invalid_return_type(self):
        """A test returning non-dict should produce ERROR."""

        def bad_return(context: dict[str, Any]) -> dict[str, Any]:
            return "not a dict"  # type: ignore[return-value]

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(
            FunctionalTest(
                test_id="bad_return",
                name="Bad Return Test",
                test_function=bad_return,
            )
        )
        result = validator.validate({"project_root": "."})
        assert not result.passed
        assert any("must return a dict" in i.description for i in result.issues)

    def test_source_field_populated(self):
        """Source field should be set from FunctionalTest.source."""

        def simple(context: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("boom")

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(
            FunctionalTest(
                test_id="src_test",
                name="Source Test",
                test_function=simple,
                source="api_endpoint",
            )
        )
        result = validator.validate({"project_root": "."})
        assert result.issues[0].source == "api_endpoint"

    def test_type_change_detected(self):
        """Changing a value's type should produce BLOCKER."""
        call_count = 0

        def type_change(context: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return {"count": "five"}  # was int, now str
            return {"count": 5}

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(
            FunctionalTest(
                test_id="types",
                name="Type Test",
                test_function=type_change,
            )
        )

        result1 = validator.validate({"project_root": "."})
        assert result1.passed

        result2 = validator.validate({"project_root": "."})
        assert not result2.passed
        blockers = [i for i in result2.issues if i.severity == Severity.BLOCKER]
        assert len(blockers) >= 1

    def test_multiple_tests(self):
        """Multiple tests should all be executed."""

        def test_a(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"a": 1}

        def test_b(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"b": 2}

        validator = FunctionalValidator(strict_mode=True)
        validator.add_test(FunctionalTest(test_id="a", name="A", test_function=test_a))
        validator.add_test(FunctionalTest(test_id="b", name="B", test_function=test_b))

        result = validator.validate({"project_root": "."})
        assert result.passed
        assert "a" in result.metrics
        assert "b" in result.metrics
