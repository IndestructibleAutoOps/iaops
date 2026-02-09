"""
Test regression detection in strict mode.

This script simulates a regression to verify the validation
system correctly detects and blocks it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from indestructibleautoops.validation.strict_validator import (
    RegressionSuite,
    RegressionTest,
    StrictValidationConfig,
    StrictValidator,
    create_default_tests,
)


def test_regression_detection():
    """Test that regressions are detected and blocked."""
    print("=" * 80)
    print("REGRESSION DETECTION TEST")
    print("=" * 80)
    print()

    # Create validator
    config = StrictValidationConfig(
        project_root=str(Path(__file__).parent.parent),
        strict_mode=True,
    )

    validator = StrictValidator(config)

    # Add default tests
    tests = create_default_tests()

    # Add a test that will regress
    def test_metric(context):
        """Test that checks a numeric metric."""
        # First run: return 100
        # Second run: return 80 (regression)
        if not hasattr(test_metric, "call_count"):
            test_metric.call_count = 0
        test_metric.call_count += 1

        # Simulate regression on second call
        if test_metric.call_count > 1:
            print("  ⚠️  Simulating regression: metric value dropped from 100 to 80")
            return {"performance_metric": 80}
        else:
            print("  ✓ Initial run: metric value = 100")
            return {"performance_metric": 100}

    tests.append(
        RegressionTest(
            test_id="performance_regression_test",
            name="Performance Regression Test",
            description="Test that detects performance regression",
            test_function=test_metric,
            category="performance",
        )
    )

    suite = RegressionSuite(
        suite_id="regression_test",
        name="Regression Test Suite",
        tests=tests,
    )
    validator.add_regression_suite(suite)

    # First run - create baseline
    print("STEP 1: Creating baseline...")
    print("-" * 80)
    results1 = validator.validate_all()
    validator.create_baseline()
    print()

    # Check baseline results
    baseline_issues = results1["summary"]["blocking_issues"]
    print(f"Baseline issues: {baseline_issues}")
    print()

    # Second run - simulate regression
    print("STEP 2: Running with regression...")
    print("-" * 80)
    validator.load_baseline()
    results2 = validator.validate_all()
    print()

    # Check if regression was detected
    blocking_issues = results2["summary"]["blocking_issues"]
    print(f"Blocking issues detected: {blocking_issues}")
    print()

    # Verify results
    if blocking_issues > 0:
        print("✅ REGRESSION DETECTION TEST PASSED")
        print()
        print("The validation system correctly:")
        print("  1. Created baseline metrics")
        print("  2. Detected the performance regression")
        print("  3. Blocked the deployment (strict mode)")

        # Show blocking issues
        blocking = []
        for _validator_name, validator_result in results2["validators"].items():
            for issue in validator_result.get("issues", []):
                if issue.get("blocking", False):
                    blocking.append(issue)

        if blocking:
            print()
            print("Blocking Issues Found:")
            print("-" * 80)
            for issue in blocking:
                print(f"  [{issue['severity'].upper()}] {issue['title']}")
                print(f"    {issue['description']}")
                if issue.get("metrics"):
                    print(f"    Metrics: {json.dumps(issue['metrics'], indent=6)}")
                print()

        assert True
    else:
        print("❌ REGRESSION DETECTION TEST FAILED")
        print()
        print("The validation system FAILED to detect the regression!")
        print("This is a critical issue in strict mode.")
        raise AssertionError("Regression detection failed")


def test_file_count_regression():
    """Test that file count regression is detected."""
    print("=" * 80)
    print("FILE COUNT REGRESSION TEST")
    print("=" * 80)
    print()

    config = StrictValidationConfig(
        project_root=str(Path(__file__).parent.parent),
        strict_mode=True,
    )

    validator = StrictValidator(config)

    # Add file count test
    def test_files(context):
        """Test file count."""
        from pathlib import Path

        project_root = context.get("project_root", ".")
        src_path = Path(project_root) / "src" / "indestructibleautoops"

        py_files = list(src_path.rglob("*.py"))
        return {
            "file_count": len(py_files),
            "src_path": str(src_path),
        }

    tests = [
        RegressionTest(
            test_id="file_count",
            name="File Count Test",
            description="Verify file count doesn't decrease",
            test_function=test_files,
            category="regression",
        )
    ]

    suite = RegressionSuite(
        suite_id="file_count_test",
        name="File Count Test Suite",
        tests=tests,
    )
    validator.add_regression_suite(suite)

    # First run - baseline
    print("STEP 1: Creating baseline...")
    results1 = validator.validate_all()
    validator.create_baseline()

    for _validator_name, validator_result in results1["validators"].items():
        for issue in validator_result.get("issues", []):
            if issue["issue_id"] == "test_file_count":
                # This won't be in issues, get from test results
                pass

    # Verify baseline file was created
    with open(validator._baseline_path / "RegressionValidator.json") as f:
        json.load(f)  # validate JSON is readable

    print("  ✓ Baseline created")
    print()

    # Second run - check (should pass)
    print("STEP 2: Running validation (should pass)...")
    validator.load_baseline()
    results2 = validator.validate_all()

    blocking_issues = results2["summary"]["blocking_issues"]

    if blocking_issues == 0:
        print("  ✓ No regressions detected (as expected)")
        print()
        print("✅ FILE COUNT REGRESSION TEST PASSED")
        assert True
    else:
        print("  ⚠️  Unexpected blocking issues")
        raise AssertionError("Unexpected blocking issues in file count test")


if __name__ == "__main__":
    print()
    failed = False
    try:
        test_regression_detection()
        print("\n✅ Regression Detection Test: PASSED")
    except AssertionError:
        print("\n❌ Regression Detection Test: FAILED")
        failed = True

    print()
    try:
        test_file_count_regression()
        print("\n✅ File Count Regression Test: PASSED")
    except AssertionError:
        print("\n❌ File Count Regression Test: FAILED")
        failed = True

    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    if not failed:
        print("✅ ALL TESTS PASSED")
        print("The strict engineering validation system is working correctly!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
