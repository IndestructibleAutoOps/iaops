#!/usr/bin/env python3
"""
Enterprise Strict Validation System — CLI Interface.

Provides a full-featured command-line interface for running
strict engineering validation, managing baselines, and integrating
with CI/CD pipelines.

Usage:
    # Create baseline
    python scripts/run_strict_validation.py --create-baseline

    # Run validation with baseline comparison
    python scripts/run_strict_validation.py --load-baseline

    # Run with whitelist
    python scripts/run_strict_validation.py --load-baseline --whitelist configs/validation_whitelist.yaml

    # Custom thresholds
    python scripts/run_strict_validation.py --load-baseline --metric-threshold 8 --performance-threshold 15

    # Relaxed mode (non-blocking)
    python scripts/run_strict_validation.py --load-baseline --relaxed
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from indestructibleautoops.validation.regression import RegressionSuite
from indestructibleautoops.validation.strict_validator import (
    StrictValidationConfig,
    StrictValidator,
    create_default_tests,
)


def load_config(args: argparse.Namespace) -> StrictValidationConfig:
    """Build StrictValidationConfig from CLI arguments."""
    return StrictValidationConfig(
        project_root=args.project_root,
        baseline_dir=args.baseline_dir,
        output_dir=args.output_dir,
        whitelist_path=args.whitelist,
        strict_mode=not args.relaxed,
        metric_threshold=args.metric_threshold / 100.0,
        performance_threshold=args.performance_threshold / 100.0,
    )


def print_validation_summary(results: dict, config: StrictValidationConfig) -> None:
    """Print a detailed validation report to stdout."""
    print("\n" + "=" * 60)
    print(" Enterprise Strict Validation System - Report")
    print("=" * 60)

    # Overall result
    status = "✅ PASSED" if results.get("overall_passed") else "❌ FAILED"
    print(f"\nOverall Status: {status}")
    print(f"Strict Mode: {'ENABLED' if config.strict_mode else 'DISABLED'}")

    # Issue statistics
    summary = results.get("summary", {})
    blocker_count = 0
    critical_count = 0
    error_count = 0
    warning_count = 0
    info_count = 0

    for _name, validator_result in results.get("validators", {}).items():
        for issue in validator_result.get("issues", []):
            sev = issue.get("severity", "").lower()
            if sev == "blocker":
                blocker_count += 1
            elif sev == "critical":
                critical_count += 1
            elif sev == "error":
                error_count += 1
            elif sev == "warning":
                warning_count += 1
            elif sev == "info":
                info_count += 1

    print("\nIssues Summary:")
    print(f"  BLOCKER:  {blocker_count}")
    print(f"  CRITICAL: {critical_count}")
    print(f"  ERROR:    {error_count}")
    print(f"  WARNING:  {warning_count}")
    print(f"  INFO:     {info_count}")
    print(f"  Suppressed: {summary.get('suppressed_issues', 0)}")

    # Validators breakdown
    print(
        f"\nValidators: {summary.get('passed_validators', 0)}/{summary.get('total_validators', 0)} passed"
    )

    # Print blocking issues
    if not results.get("overall_passed"):
        print("\nBlocking Issues:")
        for validator_name, validator_result in results.get("validators", {}).items():
            blocking_issues = [
                i for i in validator_result.get("issues", []) if i.get("blocking", False)
            ]
            if blocking_issues:
                print(f"\n  [{validator_name}]")
                for issue in blocking_issues:
                    sev = issue.get("severity", "UNKNOWN").upper()
                    title = issue.get("title", issue.get("description", ""))
                    print(f"    - [{sev}] {title}")
                    desc = issue.get("description", "")
                    if desc and desc != title:
                        print(f"      {desc}")
                    metrics = issue.get("metrics", {})
                    if "regression_pct" in metrics:
                        print(f"      Regression: {metrics['regression_pct']:.2f}%")

    # Categories
    by_category = summary.get("by_category", {})
    if by_category:
        print("\nIssues by Category:")
        for cat, count in sorted(by_category.items()):
            print(f"  {cat}: {count}")

    # Whitelist stats
    wl_stats = results.get("whitelist_stats", {})
    if wl_stats.get("total_suppressions", 0) > 0:
        print(f"\nWhitelist Suppressions: {wl_stats['total_suppressions']}")
        for entry in wl_stats.get("match_history", []):
            print(
                f"  [{entry.get('severity', '').upper()}] {entry.get('issue_id', '')} "
                f"→ suppressed by rule '{entry.get('rule_id', '')}'"
            )

    # Output file
    output_dir = config.output_dir
    latest = Path(output_dir) / "validation_latest.json"
    if latest.exists():
        print(f"\nFull report saved to: {latest}")

    print("\n" + "=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enterprise Strict Validation System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Core actions
    parser.add_argument(
        "--create-baseline",
        action="store_true",
        help="Create a new validation baseline",
    )
    parser.add_argument(
        "--load-baseline",
        action="store_true",
        help="Load and compare against existing baseline",
    )

    # Configuration
    parser.add_argument(
        "--project-root",
        type=str,
        default=str(Path(__file__).parent.parent),
        help="Project root directory",
    )
    parser.add_argument(
        "--whitelist",
        type=str,
        default=None,
        help="Path to whitelist configuration file (JSON or YAML)",
    )
    parser.add_argument(
        "--baseline-dir",
        type=str,
        default=".baselines",
        help="Directory for baseline files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".validation",
        help="Directory for validation reports",
    )

    # Thresholds (as percentages)
    parser.add_argument(
        "--metric-threshold",
        type=float,
        default=10.0,
        help="Metric regression threshold (%%)",
    )
    parser.add_argument(
        "--performance-threshold",
        type=float,
        default=20.0,
        help="Performance regression threshold (%%)",
    )

    # Mode
    parser.add_argument(
        "--relaxed",
        action="store_true",
        help="Run in relaxed mode (non-blocking)",
    )

    args = parser.parse_args()

    # Build config
    config = load_config(args)

    print("=" * 60)
    print("ENTERPRISE STRICT ENGINEERING VALIDATION")
    print("=" * 60)
    print(f"Project Root: {config.project_root}")
    print(f"Strict Mode: {'ENABLED' if config.strict_mode else 'DISABLED'}")
    print(f"Metric Threshold: {config.metric_threshold * 100:.1f}%")
    print(f"Performance Threshold: {config.performance_threshold * 100:.1f}%")
    if config.whitelist_path:
        print(f"Whitelist: {config.whitelist_path}")
    print()

    # Initialize validator
    validator = StrictValidator(config)

    # Add default regression tests
    tests = create_default_tests()
    suite = RegressionSuite(
        suite_id="default",
        name="Default Test Suite",
        tests=tests,
    )
    validator.add_regression_suite(suite)

    # Create baseline mode
    if args.create_baseline:
        print("Creating new validation baseline...")
        # Run once to populate baselines
        validator.validate_all()
        validator.create_baseline()
        print("✅ Baseline created successfully")
        print(f"   Saved to: {config.baseline_dir}/")
        sys.exit(0)

    # Load baseline if requested
    if args.load_baseline:
        try:
            validator.load_baseline()
            print(f"Loaded baseline from: {config.baseline_dir}/")
        except ValueError:
            print("No baseline found, creating new baseline...")
            validator.validate_all()
            validator.create_baseline()
            print("✅ Baseline created — re-run to compare")
            sys.exit(0)

    # Execute validation
    print("Running strict validation...")
    results = validator.validate_all()

    # Print detailed summary
    print_validation_summary(results, config)

    # Exit code
    if results.get("overall_passed"):
        print("\nValidation PASSED — Deployment can proceed")
        sys.exit(0)
    else:
        if config.strict_mode:
            print("\nValidation FAILED — Deployment blocked")
            sys.exit(1)
        else:
            print("\nValidation FAILED (relaxed mode) — Issues detected but not blocking")
            sys.exit(0)


if __name__ == "__main__":
    main()
