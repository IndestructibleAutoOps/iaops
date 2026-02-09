"""Tests for the advanced metrics collector."""

from __future__ import annotations

from pathlib import Path

import pytest

from indestructibleautoops.validation.metrics import (
    BlockingPolicy,
    MetricsValidator,
    MetricThreshold,
    collect_file_metrics,
    collect_latency_metrics,
    get_default_thresholds,
    percentile,
)


class TestPercentile:
    def test_empty_list(self):
        assert percentile([], 50) == 0.0

    def test_single_value(self):
        assert percentile([42.0], 50) == 42.0
        assert percentile([42.0], 99) == 42.0

    def test_p50(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert percentile(data, 50) == 3.0

    def test_p95(self):
        data = list(range(1, 101))
        p95 = percentile([float(x) for x in data], 95)
        assert 95.0 <= p95 <= 96.0

    def test_p99(self):
        data = list(range(1, 101))
        p99 = percentile([float(x) for x in data], 99)
        assert 99.0 <= p99 <= 100.0

    def test_unsorted_input(self):
        data = [5.0, 1.0, 3.0, 2.0, 4.0]
        assert percentile(data, 50) == 3.0


class TestLatencyMetrics:
    def test_basic_latencies(self):
        durations = [0.1, 0.2, 0.15, 0.3, 0.25]
        metrics = collect_latency_metrics(durations)
        assert "latency_p50" in metrics
        assert "latency_p95" in metrics
        assert "latency_p99" in metrics
        assert "latency_mean" in metrics
        assert metrics["latency_mean"].value == pytest.approx(0.2, abs=0.01)

    def test_empty_durations(self):
        assert collect_latency_metrics([]) == {}


class TestFileMetrics:
    def test_collect_from_project(self):
        # Use the actual iaops project
        project_root = Path(__file__).parent.parent
        metrics = collect_file_metrics(str(project_root))
        assert "file_count" in metrics
        assert "total_lines" in metrics
        assert "avg_lines_per_file" in metrics
        assert metrics["file_count"].value > 0
        assert metrics["total_lines"].value > 0

    def test_collect_from_empty_dir(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        metrics = collect_file_metrics(str(tmp_path))
        assert metrics["file_count"].value == 0.0


class TestMetricThreshold:
    def test_default_thresholds(self):
        thresholds = get_default_thresholds()
        assert len(thresholds) >= 5
        names = {t.name for t in thresholds}
        assert "code_coverage" in names
        assert "file_count" in names
        assert "security_vulnerabilities" in names

    def test_progressive_policy(self):
        thresholds = get_default_thresholds()
        latency_p95 = next(t for t in thresholds if t.name == "latency_p95")
        assert latency_p95.blocking_policy == BlockingPolicy.PROGRESSIVE
        assert latency_p95.warn_count_before_block == 3


class TestMetricsValidator:
    def test_basic_validation(self):
        validator = MetricsValidator(
            thresholds=[
                MetricThreshold(
                    name="file_count",
                    min_value=1.0,
                    regression_pct=0.10,
                    higher_is_better=True,
                )
            ],
            strict_mode=True,
            collect_coverage=False,
            collect_complexity=False,
            collect_security=False,
        )
        project_root = str(Path(__file__).parent.parent)
        result = validator.validate({"project_root": project_root})
        assert "file_count" in result.metrics
        assert result.metrics["file_count"]["value"] > 0

    def test_threshold_violation(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        validator = MetricsValidator(
            thresholds=[
                MetricThreshold(
                    name="file_count",
                    min_value=10.0,  # empty dir has 0 files
                    regression_pct=0.10,
                    higher_is_better=True,
                )
            ],
            strict_mode=True,
            collect_coverage=False,
            collect_complexity=False,
            collect_security=False,
        )
        result = validator.validate({"project_root": str(tmp_path)})
        blocking = result.get_blocking_issues()
        assert len(blocking) > 0
        assert any("below minimum" in i.title for i in blocking)

    def test_progressive_blocking(self):
        validator = MetricsValidator(
            thresholds=[
                MetricThreshold(
                    name="file_count",
                    regression_pct=0.01,  # very tight threshold
                    higher_is_better=True,
                    blocking_policy=BlockingPolicy.PROGRESSIVE,
                    warn_count_before_block=2,
                )
            ],
            strict_mode=True,
            collect_coverage=False,
            collect_complexity=False,
            collect_security=False,
        )
        project_root = str(Path(__file__).parent.parent)

        # First run — establishes baseline
        result1 = validator.validate({"project_root": project_root})
        assert result1.passed  # no baseline to compare against

    def test_no_crash_on_missing_tools(self, tmp_path: Path):
        """Validator should not crash if radon/pip-audit are missing."""
        (tmp_path / "src").mkdir()
        validator = MetricsValidator(
            strict_mode=False,
            collect_coverage=True,
            collect_complexity=True,
            collect_security=True,
        )
        result = validator.validate({"project_root": str(tmp_path)})
        # Should complete without error
        assert result.validator_name == "MetricsValidator"
