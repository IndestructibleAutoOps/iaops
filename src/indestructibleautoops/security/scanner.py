"""
Base Security Scanner Framework

This module provides the foundation for enterprise-grade security scanning,
including severity levels, data structures, and a plugin system for scanner
implementations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class SecuritySeverity(Enum):
    """Security issue severity levels aligned with industry standards (CVSS)."""

    CRITICAL = "CRITICAL"  # CVSS 9.0-10.0 - Immediate action required
    HIGH = "HIGH"  # CVSS 7.0-8.9 - Urgent remediation
    MEDIUM = "MEDIUM"  # CVSS 4.0-6.9 - Planned remediation
    LOW = "LOW"  # CVSS 0.1-3.9 - Low priority
    INFO = "INFO"  # Informational findings

    @classmethod
    def from_cvss(cls, cvss_score: float) -> "SecuritySeverity":
        """Map CVSS score to SecuritySeverity."""
        if cvss_score >= 9.0:
            return cls.CRITICAL
        elif cvss_score >= 7.0:
            return cls.HIGH
        elif cvss_score >= 4.0:
            return cls.MEDIUM
        elif cvss_score >= 0.1:
            return cls.LOW
        else:
            return cls.INFO


class SecurityIssueType(Enum):
    """Types of security issues."""

    VULNERABILITY = "VULNERABILITY"  # Known CVE/CWE vulnerabilities
    DEPENDENCY = "DEPENDENCY"  # Vulnerable dependencies
    CONFIGURATION = "CONFIGURATION"  # Security misconfigurations
    SECRET = "SECRET"  # Exposed secrets/credentials
    LICENSE = "LICENSE"  # License compliance issues
    CODE_QUALITY = "CODE_QUALITY"  # Security-relevant code quality issues
    CONTAINER = "CONTAINER"  # Container image security
    INFRASTRUCTURE = "INFRASTRUCTURE"  # Infrastructure security


@dataclass
class SecurityIssue:
    """Represents a single security issue found by a scanner."""

    # Identification
    issue_id: str  # Unique identifier (e.g., CVE-2024-1234, SNYK-PY-XXXXX)
    title: str  # Human-readable title
    description: str  # Detailed description

    # Classification
    severity: SecuritySeverity  # Severity level
    issue_type: SecurityIssueType  # Type of security issue

    # Source information
    scanner_name: str  # Name of the scanner that found this
    source_path: str | None = None  # File/dependency where issue was found
    source_line: int | None = None  # Line number (if applicable)

    # Vulnerability details (if applicable)
    cve_id: str | None = None  # CVE identifier
    cwe_id: str | None = None  # CWE identifier
    cvss_score: float | None = None  # CVSS score
    cvss_vector: str | None = None  # CVSS vector string

    # Dependency details (if applicable)
    package_name: str | None = None  # Vulnerable package name
    package_version: str | None = None  # Current vulnerable version
    fixed_version: str | None = None  # Available fixed version

    # Remediation
    remediation: str | None = None  # Recommended remediation steps
    references: list[str] = field(default_factory=list)  # Reference URLs

    # Metadata
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    scan_id: str | None = None  # Associated scan ID

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "issue_id": self.issue_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "issue_type": self.issue_type.value,
            "scanner_name": self.scanner_name,
            "source_path": self.source_path,
            "source_line": self.source_line,
            "cve_id": self.cve_id,
            "cwe_id": self.cwe_id,
            "cvss_score": self.cvss_score,
            "cvss_vector": self.cvss_vector,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "fixed_version": self.fixed_version,
            "remediation": self.remediation,
            "references": self.references,
            "discovered_at": self.discovered_at.isoformat(),
            "scan_id": self.scan_id,
        }

    @property
    def is_blocking(self) -> bool:
        """Check if this issue should block deployment."""
        return self.severity in [SecuritySeverity.CRITICAL, SecuritySeverity.HIGH]


@dataclass
class SecurityScanResult:
    """Result of a security scan operation."""

    scanner_name: str  # Name of the scanner
    scan_id: str  # Unique scan identifier
    target: str  # Target of the scan (path, image, etc.)
    status: str  # Scan status (success, failed, partial)

    # Findings
    issues: list[SecurityIssue] = field(default_factory=list)

    # Statistics
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    blocking_count: int = 0

    # Metadata
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None

    def __post_init__(self):
        """Calculate statistics after initialization."""
        self._update_statistics()

    def _update_statistics(self):
        """Update statistics based on issues."""
        self.total_issues = len(self.issues)
        self.critical_count = sum(1 for i in self.issues if i.severity == SecuritySeverity.CRITICAL)
        self.high_count = sum(1 for i in self.issues if i.severity == SecuritySeverity.HIGH)
        self.medium_count = sum(1 for i in self.issues if i.severity == SecuritySeverity.MEDIUM)
        self.low_count = sum(1 for i in self.issues if i.severity == SecuritySeverity.LOW)
        self.info_count = sum(1 for i in self.issues if i.severity == SecuritySeverity.INFO)
        self.blocking_count = self.critical_count + self.high_count

    def add_issue(self, issue: SecurityIssue) -> None:
        """Add an issue to the scan result and update statistics."""
        issue.scan_id = self.scan_id
        self.issues.append(issue)
        self._update_statistics()

    def get_issues_by_severity(self, severity: SecuritySeverity) -> list[SecurityIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_blocking_issues(self) -> list[SecurityIssue]:
        """Get all blocking issues (CRITICAL + HIGH)."""
        return self.get_issues_by_severity(SecuritySeverity.CRITICAL) + self.get_issues_by_severity(
            SecuritySeverity.HIGH
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scanner_name": self.scanner_name,
            "scan_id": self.scan_id,
            "target": self.target,
            "status": self.status,
            "issues": [issue.to_dict() for issue in self.issues],
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "blocking_count": self.blocking_count,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }

    def has_blocking_issues(self) -> bool:
        """Check if this scan result has blocking issues."""
        return self.blocking_count > 0


@runtime_checkable
class SecurityScanner(Protocol):
    """Protocol for security scanner implementations."""

    @property
    def scanner_name(self) -> str:
        """Return the name of the scanner."""
        ...

    @property
    def scanner_version(self) -> str:
        """Return the version of the scanner."""
        ...

    def scan(
        self,
        target: str,
        config: dict[str, Any] | None = None,
    ) -> SecurityScanResult:
        """
        Perform a security scan on the specified target.

        Args:
            target: The target to scan (file path, directory, image, etc.)
            config: Optional configuration dictionary

        Returns:
            SecurityScanResult containing the scan findings
        """
        ...

    def is_available(self) -> bool:
        """Check if the scanner is available and properly configured."""
        ...


class ScannerRegistry:
    """Registry for managing available security scanners."""

    def __init__(self):
        self._scanners: dict[str, SecurityScanner] = {}

    def register(self, scanner: SecurityScanner) -> None:
        """Register a security scanner."""
        self._scanners[scanner.scanner_name] = scanner

    def unregister(self, scanner_name: str) -> None:
        """Unregister a security scanner."""
        self._scanners.pop(scanner_name, None)

    def get(self, scanner_name: str) -> SecurityScanner | None:
        """Get a scanner by name."""
        return self._scanners.get(scanner_name)

    def list_scanners(self) -> list[str]:
        """List all registered scanner names."""
        return list(self._scanners.keys())

    def get_available_scanners(self) -> list[SecurityScanner]:
        """Get all available scanners."""
        return [scanner for scanner in self._scanners.values() if scanner.is_available()]

    def clear(self) -> None:
        """Clear all registered scanners."""
        self._scanners.clear()


# Global scanner registry instance
scanner_registry = ScannerRegistry()
