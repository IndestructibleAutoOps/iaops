"""
Enterprise Strict Engineering Validation System.

Provides comprehensive validation tools to detect and block
critical regressions in quality, performance, and functionality,
with false-positive suppression via a whitelist mechanism.
"""

from .metrics import (
    BlockingPolicy,
    MetricResult,
    MetricsValidator,
    MetricThreshold,
    get_default_thresholds,
    percentile,
)
from .regression import RegressionSuite, RegressionTest, RegressionValidator
from .strict_validator import (
    StrictValidationConfig,
    StrictValidator,
    run_strict_validation,
)
from .validator import STRICT_MODE, BaseValidator, Severity, ValidationResult
from .whitelist import ExemptionStatus, WhitelistManager, WhitelistRule

__all__ = [
    # Core validation
    "BaseValidator",
    "ValidationResult",
    "Severity",
    "STRICT_MODE",
    # Regression testing
    "RegressionTest",
    "RegressionSuite",
    "RegressionValidator",
    # Advanced metrics
    "MetricsValidator",
    "MetricThreshold",
    "MetricResult",
    "BlockingPolicy",
    "get_default_thresholds",
    "percentile",
    # Strict validation
    "StrictValidator",
    "StrictValidationConfig",
    "run_strict_validation",
    # Whitelist / exemptions
    "WhitelistManager",
    "WhitelistRule",
    "ExemptionStatus",
]
