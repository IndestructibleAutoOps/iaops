"""Tests for the standalone RegressionDetector."""

from __future__ import annotations

from indestructibleautoops.validation.regression_detector import (
    RegressionDetector,
    detect_numeric_regression,
    detect_structural_regression,
)


class TestDetectNumericRegression:
    def test_no_regression(self):
        regressed, desc = detect_numeric_regression(95.0, 100.0, threshold=0.10)
        assert not regressed

    def test_general_regression(self):
        regressed, desc = detect_numeric_regression(80.0, 100.0, threshold=0.10)
        assert regressed
        assert "decreased" in desc

    def test_performance_regression(self):
        regressed, desc = detect_numeric_regression(
            1.5, 1.0, threshold=0.20, metric_type="performance"
        )
        assert regressed
        assert "increased" in desc

    def test_performance_no_regression(self):
        regressed, _ = detect_numeric_regression(
            1.1, 1.0, threshold=0.20, metric_type="performance"
        )
        assert not regressed

    def test_none_values(self):
        regressed, desc = detect_numeric_regression(None, 100.0)
        assert not regressed
        assert "Missing" in desc

    def test_zero_baseline(self):
        regressed, desc = detect_numeric_regression(5.0, 0.0)
        assert not regressed
        assert "zero" in desc.lower()

    def test_exact_threshold(self):
        # Exactly at 10% drop: 90 vs 100 → change = 0.10, not > 0.10
        regressed, _ = detect_numeric_regression(90.0, 100.0, threshold=0.10)
        assert not regressed


class TestDetectStructuralRegression:
    def test_no_change(self):
        data = {"a": 1, "b": "hello"}
        regressed, _ = detect_structural_regression(data, data)
        assert not regressed

    def test_missing_key(self):
        regressed, desc = detect_structural_regression({"a": 1}, {"a": 1, "b": 2})
        assert regressed
        assert "missing" in desc.lower()

    def test_added_key(self):
        regressed, desc = detect_structural_regression({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2})
        assert regressed
        assert "added" in desc.lower()

    def test_type_change(self):
        regressed, desc = detect_structural_regression({"a": "string"}, {"a": 123})
        assert regressed
        assert "Type change" in desc

    def test_empty_baseline(self):
        regressed, _ = detect_structural_regression({"a": 1}, {})
        assert not regressed


class TestRegressionDetectorClass:
    def test_detect_numeric_returns_issue(self):
        detector = RegressionDetector(metric_threshold=0.10, strict_mode=True)
        issue = detector.detect_numeric(
            current=70.0,
            baseline=100.0,
            metric_type="general",
            metric_name="coverage",
        )
        assert issue is not None
        assert issue.severity.value == "critical"
        assert "coverage" in issue.issue_id

    def test_detect_numeric_returns_none(self):
        detector = RegressionDetector()
        issue = detector.detect_numeric(current=95.0, baseline=100.0)
        assert issue is None

    def test_detect_structural_returns_blocker(self):
        detector = RegressionDetector()
        issue = detector.detect_structural(
            current={"a": 1},
            baseline={"a": 1, "b": 2},
            test_name="api_response",
        )
        assert issue is not None
        assert issue.severity.value == "blocker"
        assert "api_response" in issue.issue_id

    def test_source_field_populated(self):
        detector = RegressionDetector()
        issue = detector.detect_numeric(
            current=50.0,
            baseline=100.0,
            metric_name="throughput",
            source="api_endpoint",
        )
        assert issue is not None
        assert issue.source == "api_endpoint"
