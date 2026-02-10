"""
Tests for the base security scanner framework.
"""

import pytest
from datetime import datetime
from pathlib import Path

from indestructibleautoops.security.scanner import (
    SecuritySeverity,
    SecurityIssueType,
    SecurityIssue,
    SecurityScanResult,
    SecurityScanner,
    ScannerRegistry,
)


class TestSecuritySeverity:
    """Tests for SecuritySeverity enum."""
    
    def test_from_cvss_critical(self):
        """Test CVSS score mapping to CRITICAL."""
        assert SecuritySeverity.from_cvss(9.0) == SecuritySeverity.CRITICAL
        assert SecuritySeverity.from_cvss(9.5) == SecuritySeverity.CRITICAL
        assert SecuritySeverity.from_cvss(10.0) == SecuritySeverity.CRITICAL
    
    def test_from_cvss_high(self):
        """Test CVSS score mapping to HIGH."""
        assert SecuritySeverity.from_cvss(7.0) == SecuritySeverity.HIGH
        assert SecuritySeverity.from_cvss(8.0) == SecuritySeverity.HIGH
        assert SecuritySeverity.from_cvss(8.9) == SecuritySeverity.HIGH
    
    def test_from_cvss_medium(self):
        """Test CVSS score mapping to MEDIUM."""
        assert SecuritySeverity.from_cvss(4.0) == SecuritySeverity.MEDIUM
        assert SecuritySeverity.from_cvss(5.0) == SecuritySeverity.MEDIUM
        assert SecuritySeverity.from_cvss(6.9) == SecuritySeverity.MEDIUM
    
    def test_from_cvss_low(self):
        """Test CVSS score mapping to LOW."""
        assert SecuritySeverity.from_cvss(0.1) == SecuritySeverity.LOW
        assert SecuritySeverity.from_cvss(2.0) == SecuritySeverity.LOW
        assert SecuritySeverity.from_cvss(3.9) == SecuritySeverity.LOW
    
    def test_from_cvss_info(self):
        """Test CVSS score mapping to INFO."""
        assert SecuritySeverity.from_cvss(0.0) == SecuritySeverity.INFO


class TestSecurityIssue:
    """Tests for SecurityIssue dataclass."""
    
    def test_basic_issue_creation(self):
        """Test creating a basic security issue."""
        issue = SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        )
        
        assert issue.issue_id == "CVE-2024-1234"
        assert issue.title == "Test Vulnerability"
        assert issue.severity == SecuritySeverity.CRITICAL
        assert issue.scanner_name == "TestScanner"
    
    def test_issue_with_vulnerability_details(self):
        """Test creating an issue with vulnerability details."""
        issue = SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
            cve_id="CVE-2024-1234",
            cwe_id="CWE-79",
            cvss_score=9.8,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        )
        
        assert issue.cve_id == "CVE-2024-1234"
        assert issue.cwe_id == "CWE-79"
        assert issue.cvss_score == 9.8
        assert issue.cvss_vector == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    
    def test_issue_with_dependency_details(self):
        """Test creating an issue with dependency details."""
        issue = SecurityIssue(
            issue_id="SNYK-PY-12345",
            title="Vulnerable Dependency",
            description="A test dependency vulnerability",
            severity=SecuritySeverity.HIGH,
            issue_type=SecurityIssueType.DEPENDENCY,
            scanner_name="TestScanner",
            package_name="requests",
            package_version="2.0.0",
            fixed_version="2.31.0",
        )
        
        assert issue.package_name == "requests"
        assert issue.package_version == "2.0.0"
        assert issue.fixed_version == "2.31.0"
    
    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
            references=["https://example.com/cve-2024-1234"],
        )
        
        result = issue.to_dict()
        
        assert result["issue_id"] == "CVE-2024-1234"
        assert result["severity"] == "CRITICAL"
        assert result["issue_type"] == "VULNERABILITY"
        assert result["scanner_name"] == "TestScanner"
        assert result["references"] == ["https://example.com/cve-2024-1234"]
        assert "discovered_at" in result
    
    def test_is_blocking_critical(self):
        """Test blocking check for CRITICAL severity."""
        issue = SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        )
        
        assert issue.is_blocking is True
    
    def test_is_blocking_high(self):
        """Test blocking check for HIGH severity."""
        issue = SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.HIGH,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        )
        
        assert issue.is_blocking is True
    
    def test_is_not_blocking_medium(self):
        """Test blocking check for MEDIUM severity."""
        issue = SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.MEDIUM,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        )
        
        assert issue.is_blocking is False


class TestSecurityScanResult:
    """Tests for SecurityScanResult dataclass."""
    
    def test_basic_scan_result_creation(self):
        """Test creating a basic scan result."""
        result = SecurityScanResult(
            scanner_name="TestScanner",
            scan_id="scan-123",
            target="/test/path",
            status="success",
        )
        
        assert result.scanner_name == "TestScanner"
        assert result.scan_id == "scan-123"
        assert result.target == "/test/path"
        assert result.status == "success"
        assert result.total_issues == 0
        assert result.blocking_count == 0
    
    def test_scan_result_with_issues(self):
        """Test scan result with issues."""
        result = SecurityScanResult(
            scanner_name="TestScanner",
            scan_id="scan-123",
            target="/test/path",
            status="success",
        )
        
        # Add some issues
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Critical Vulnerability",
            description="A critical vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-5678",
            title="High Vulnerability",
            description="A high vulnerability",
            severity=SecuritySeverity.HIGH,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        assert result.total_issues == 2
        assert result.critical_count == 1
        assert result.high_count == 1
        assert result.blocking_count == 2
    
    def test_get_issues_by_severity(self):
        """Test filtering issues by severity."""
        result = SecurityScanResult(
            scanner_name="TestScanner",
            scan_id="scan-123",
            target="/test/path",
            status="success",
        )
        
        # Add issues with different severities
        for severity in [SecuritySeverity.CRITICAL, SecuritySeverity.HIGH, SecuritySeverity.MEDIUM]:
            result.add_issue(SecurityIssue(
                issue_id=f"TEST-{severity.value}",
                title=f"{severity.value} Issue",
                description=f"A {severity.value} issue",
                severity=severity,
                issue_type=SecurityIssueType.VULNERABILITY,
                scanner_name="TestScanner",
            ))
        
        critical_issues = result.get_issues_by_severity(SecuritySeverity.CRITICAL)
        assert len(critical_issues) == 1
        assert critical_issues[0].severity == SecuritySeverity.CRITICAL
        
        high_issues = result.get_issues_by_severity(SecuritySeverity.HIGH)
        assert len(high_issues) == 1
    
    def test_get_blocking_issues(self):
        """Test getting all blocking issues."""
        result = SecurityScanResult(
            scanner_name="TestScanner",
            scan_id="scan-123",
            target="/test/path",
            status="success",
        )
        
        # Add issues
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-1",
            title="Critical",
            description="Critical",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-2",
            title="High",
            description="High",
            severity=SecuritySeverity.HIGH,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-3",
            title="Medium",
            description="Medium",
            severity=SecuritySeverity.MEDIUM,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        blocking_issues = result.get_blocking_issues()
        assert len(blocking_issues) == 2
    
    def test_has_blocking_issues(self):
        """Test checking if result has blocking issues."""
        result = SecurityScanResult(
            scanner_name="TestScanner",
            scan_id="scan-123",
            target="/test/path",
            status="success",
        )
        
        assert result.has_blocking_issues() is False
        
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-1",
            title="Critical",
            description="Critical",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        assert result.has_blocking_issues() is True
    
    def test_scan_result_to_dict(self):
        """Test converting scan result to dictionary."""
        result = SecurityScanResult(
            scanner_name="TestScanner",
            scan_id="scan-123",
            target="/test/path",
            status="success",
        )
        
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="TestScanner",
        ))
        
        result_dict = result.to_dict()
        
        assert result_dict["scanner_name"] == "TestScanner"
        assert result_dict["scan_id"] == "scan-123"
        assert result_dict["total_issues"] == 1
        assert result_dict["critical_count"] == 1
        assert len(result_dict["issues"]) == 1


class MockScanner:
    """Mock scanner for testing."""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self._name = name
        self._version = version
        self._available = True
    
    @property
    def scanner_name(self) -> str:
        return self._name
    
    @property
    def scanner_version(self) -> str:
        return self._version
    
    def scan(self, target: str, config: dict = None) -> SecurityScanResult:
        return SecurityScanResult(
            scanner_name=self._name,
            scan_id=f"{self._name}-scan",
            target=target,
            status="success",
        )
    
    def is_available(self) -> bool:
        return self._available


class TestScannerRegistry:
    """Tests for ScannerRegistry."""
    
    def test_register_scanner(self):
        """Test registering a scanner."""
        registry = ScannerRegistry()
        scanner = MockScanner("TestScanner")
        
        registry.register(scanner)
        
        assert "TestScanner" in registry.list_scanners()
        assert registry.get("TestScanner") == scanner
    
    def test_unregister_scanner(self):
        """Test unregistering a scanner."""
        registry = ScannerRegistry()
        scanner = MockScanner("TestScanner")
        
        registry.register(scanner)
        assert "TestScanner" in registry.list_scanners()
        
        registry.unregister("TestScanner")
        assert "TestScanner" not in registry.list_scanners()
        assert registry.get("TestScanner") is None
    
    def test_get_scanner(self):
        """Test getting a scanner by name."""
        registry = ScannerRegistry()
        scanner = MockScanner("TestScanner")
        
        registry.register(scanner)
        
        retrieved = registry.get("TestScanner")
        assert retrieved == scanner
        
        # Test getting non-existent scanner
        assert registry.get("NonExistent") is None
    
    def test_list_scanners(self):
        """Test listing all scanners."""
        registry = ScannerRegistry()
        
        assert len(registry.list_scanners()) == 0
        
        scanner1 = MockScanner("Scanner1")
        scanner2 = MockScanner("Scanner2")
        
        registry.register(scanner1)
        registry.register(scanner2)
        
        scanners = registry.list_scanners()
        assert len(scanners) == 2
        assert "Scanner1" in scanners
        assert "Scanner2" in scanners
    
    def test_get_available_scanners(self):
        """Test getting only available scanners."""
        registry = ScannerRegistry()
        
        scanner1 = MockScanner("Scanner1")
        scanner2 = MockScanner("Scanner2")
        scanner2._available = False
        
        registry.register(scanner1)
        registry.register(scanner2)
        
        available = registry.get_available_scanners()
        assert len(available) == 1
        assert available[0] == scanner1
    
    def test_clear_scanners(self):
        """Test clearing all scanners."""
        registry = ScannerRegistry()
        
        scanner1 = MockScanner("Scanner1")
        scanner2 = MockScanner("Scanner2")
        
        registry.register(scanner1)
        registry.register(scanner2)
        
        assert len(registry.list_scanners()) == 2
        
        registry.clear()
        
        assert len(registry.list_scanners()) == 0


class TestIntegration:
    """Integration tests for the scanner framework."""
    
    def test_end_to_end_scan_workflow(self):
        """Test a complete scan workflow."""
        # Create a scanner
        scanner = MockScanner("IntegrationScanner")
        
        # Register scanner
        registry = ScannerRegistry()
        registry.register(scanner)
        
        # Perform scan
        result = scanner.scan(target="/test/path")
        
        # Add some issues
        result.add_issue(SecurityIssue(
            issue_id="CVE-2024-1234",
            title="Test Vulnerability",
            description="A test vulnerability",
            severity=SecuritySeverity.CRITICAL,
            issue_type=SecurityIssueType.VULNERABILITY,
            scanner_name="IntegrationScanner",
        ))
        
        # Verify result
        assert result.total_issues == 1
        assert result.has_blocking_issues() is True
        assert result.scanner_name == "IntegrationScanner"
        assert result.scan_id == "IntegrationScanner-scan"