"""
Run Enterprise Strict Engineering Validation.

This script runs comprehensive validation to ensure no regression.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from indestructibleautoops.validation.strict_validator import (
    run_strict_validation,
)


def main():
    """Main validation runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Enterprise Strict Engineering Validation")
    parser.add_argument(
        "--project-root",
        type=str,
        default=str(Path(__file__).parent.parent),
        help="Project root directory",
    )
    parser.add_argument(
        "--create-baseline",
        action="store_true",
        help="Create baseline metrics",
    )
    parser.add_argument(
        "--load-baseline",
        action="store_true",
        help="Load baseline metrics for comparison",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Enable strict mode (default: True)",
    )
    parser.add_argument(
        "--allow-blocking",
        action="store_true",
        help="Allow blocking issues in non-strict mode",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ENTERPRISE STRICT ENGINEERING VALIDATION")
    print("=" * 80)
    print(f"Project Root: {args.project_root}")
    print(f"Strict Mode: {'ENABLED' if args.strict else 'DISABLED'}")
    print(f"Create Baseline: {args.create_baseline}")
    print(f"Load Baseline: {args.load_baseline}")
    print()

    # Run validation
    results = run_strict_validation(
        project_root=args.project_root,
        create_baseline=args.create_baseline,
        load_baseline=args.load_baseline,
    )

    # Exit with appropriate code
    if not results.get("overall_passed", True):
        if results.get("strict_mode", False):
            print("\n❌ VALIDATION FAILED - Deployment is BLOCKED in strict mode")
            sys.exit(1)
        else:
            print("\n⚠️  VALIDATION FAILED - Issues detected but not blocking")
            sys.exit(0)
    else:
        print("\n✅ VALIDATION PASSED - No regressions detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
