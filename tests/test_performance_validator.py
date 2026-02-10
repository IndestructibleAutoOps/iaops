"""Tests for the PerformanceValidator."""

from __future__ import annotations

import time

from indestructibleautoops.validation.performance_validator import (
    PerformanceTest,
    PerformanceValidator,
)


class TestPerformanceValidator:
    def test_basic_run(self):
        def fast_op():
            time.sleep(0.001)

        validator = PerformanceValidator(strict_mode=True)
        validator.add_test(
            PerformanceTest(
                test_id="fast_op",
                name="Fast Operation",
                test_function=fast_op,
                iterations=3,
            )
        )
        result = validator.validate({"project_root": "."})
        assert "fast_op" in result.metrics
        assert result.metrics["fast_op"]["iterations"] == 3
        assert result.metrics["fast_op"]["p95"] > 0

    def test_no_regression_on_first_run(self):
        def stable_op():
            time.sleep(0.001)

        validator = PerformanceValidator(strict_mode=True)
        validator.add_test(
            PerformanceTest(
                test_id="stable",
                name="Stable Op",
                test_function=stable_op,
                iterations=3,
            )
        )
        result = validator.validate({"project_root": "."})
        # First run has no baseline → no regression
        assert result.passed

    def test_handles_test_failure(self):
        def failing_op():
            raise RuntimeError("boom")

        validator = PerformanceValidator(strict_mode=True)
        validator.add_test(
            PerformanceTest(
                test_id="failing",
                name="Failing Op",
                test_function=failing_op,
                iterations=2,
            )
        )
        result = validator.validate({"project_root": "."})
        assert not result.passed
        assert any("boom" in i.description for i in result.issues)

    def test_source_field_populated(self):
        def noop():
            pass

        validator = PerformanceValidator(strict_mode=True)
        validator.add_test(
            PerformanceTest(
                test_id="src_test",
                name="Source Test",
                test_function=noop,
                iterations=2,
                source="api_endpoint",
            )
        )
        result = validator.validate({"project_root": "."})
        # No regression expected, but check metrics are collected
        assert "src_test" in result.metrics
