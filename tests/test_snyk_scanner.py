"""
Tests for the Snyk security scanner.
"""

import json
import pytest
from unittest.mock import patch, Mock

from indestructibleautoops.security.snyk_scanner import (
    SnykScanner,
    create_snyk_scanner,
)
from indestructibleautoops.security.scanner import (
    SecuritySeverity,
    SecurityIssueType,
    SecurityScanResult,
)


class TestSnykScanner:
    """Tests for SnykScanner class."""

    def test_scanner_properties(self):
        """Test scanner name and version properties."""
        scanner = SnykScanner()
        assert scanner.scanner_name == "Snyk"
        # Version may be "unknown" if Snyk is not installed
        assert scanner.scanner_version is not None

    def test_map_snyk_severity(self):
        """Test severity mapping from Snyk to SecuritySeverity."""
        scanner = SnykScanner()
        assert scanner._map_snyk_severity("critical") == SecuritySeverity.CRITICAL
        assert scanner._map_snyk_severity("high") == SecuritySeverity.HIGH
        assert scanner._map_snyk_severity("medium") == SecuritySeverity.MEDIUM
        assert scanner._map_snyk_severity("low") == SecuritySeverity.LOW
        assert scanner._map_snyk_severity("unknown") == SecuritySeverity.LOW

    def test_map_snyk_severity_case_insensitive(self):
        """Test that severity mapping is case-insensitive."""
        scanner = SnykScanner()
        assert scanner._map_snyk_severity("CRITICAL") == SecuritySeverity.CRITICAL
        assert scanner._map_snyk_severity("High") == SecuritySeverity.HIGH
        assert scanner._map_snyk_severity("MEDIUM") == SecuritySeverity.MEDIUM
        assert scanner._map_snyk_severity("Low") == SecuritySeverity.LOW

    @patch("subprocess.run")
    def test_is_available_true(self, mock_run):
        """Test is_available returns True when Snyk is installed."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        scanner = SnykScanner()
        assert scanner.is_available() is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_is_available_false(self, mock_run):
        """Test is_available returns False when Snyk is not installed."""
        mock_run.side_effect = FileNotFoundError("snyk not found")
        scanner = SnykScanner()
        assert scanner.is_available() is False


class TestSnykScannerScan:
    """Tests for SnykScanner scan method."""

    @patch("subprocess.run")
    def test_scan_success(self, mock_run):
        """Test successful scan with vulnerabilities found."""
        snyk_output = {
            "vulnerabilities": [
                {
                    "id": "SNYK-PY-12345",
                    "title": "Test Vulnerability",
                    "description": "A test vulnerability",
                    "severity": "high",
                    "cvssScore": 7.5,
                    "cvssVector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                    "references": ["https://example.com/vuln"],
                    "packageName": "requests",
                    "version": "2.0.0",
                    "semver": {"patched": ["2.31.0"]},
                    "identifiers": {
                        "CVE": ["CVE-2024-1234"],
                        "CWE": ["CWE-79"],
                    },
                }
            ],
            "ok": False,
        }
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(snyk_output)
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = SnykScanner()
        with patch.object(scanner, "is_available", return_value=True):
            result = scanner.scan("/test/path")

        assert result.status == "success"
        assert result.total_issues == 1
        assert result.high_count == 1
        assert result.has_blocking_issues() is True

        issue = result.issues[0]
        assert issue.issue_id == "SNYK-PY-12345"
        assert issue.title == "Test Vulnerability"
        assert issue.severity == SecuritySeverity.HIGH
        assert issue.issue_type == SecurityIssueType.DEPENDENCY
        assert issue.package_name == "requests"
        assert issue.package_version == "2.0.0"
        assert issue.fixed_version == "2.31.0"
        assert issue.cve_id == "CVE-2024-1234"

    @patch("subprocess.run")
    def test_scan_failure(self, mock_run):
        """Test scan failure scenario."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Authentication failed"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        scanner = SnykScanner()
        with patch.object(scanner, "is_available", return_value=True):
            result = scanner.scan("/test/path")

        assert result.status == "failed"
        assert "Authentication failed" in result.error_message
        assert result.total_issues == 0

    @patch("subprocess.run")
    def test_scan_not_available(self, mock_run):
        """Test scan when Snyk is not available."""
        scanner = SnykScanner()
        result = scanner.scan("/test/path")

        assert result.status == "failed"
        assert "not available" in result.error_message

    @patch("subprocess.run")
    def test_parse_multiple_vulnerabilities(self, mock_run):
        """Test parsing multiple vulnerabilities with different severities."""
        snyk_output = {
            "vulnerabilities": [
                {
                    "id": "SNYK-PY-1",
                    "title": "Critical Vuln",
                    "description": "Critical",
                    "severity": "critical",
                    "cvssScore": 9.8,
                    "packageName": "pkg1",
                    "version": "1.0.0",
                },
                {
                    "id": "SNYK-PY-2",
                    "title": "High Vuln",
                    "description": "High",
                    "severity": "high",
                    "cvssScore": 7.5,
                    "packageName": "pkg2",
                    "version": "2.0.0",
                },
                {
                    "id": "SNYK-PY-3",
                    "title": "Medium Vuln",
                    "description": "Medium",
                    "severity": "medium",
                    "cvssScore": 5.0,
                    "packageName": "pkg3",
                    "version": "3.0.0",
                },
            ],
            "ok": False,
        }

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(snyk_output)
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = SnykScanner()
        with patch.object(scanner, "is_available", return_value=True):
            result = scanner.scan("/test/path")

        assert result.total_issues == 3
        assert result.critical_count == 1
        assert result.high_count == 1
        assert result.medium_count == 1
        assert result.blocking_count == 2

    @patch("subprocess.run")
    def test_scan_with_severity_threshold(self, mock_run):
        """Test scan with custom severity threshold."""
        snyk_output = {"vulnerabilities": [], "ok": True}
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(snyk_output)
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = SnykScanner()
        with patch.object(scanner, "is_available", return_value=True):
            result = scanner.scan(
                "/test/path",
                config={"severity_threshold": "high"},
            )

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--severity-threshold=high" in call_args

    @patch("subprocess.run")
    def test_scan_with_all_projects(self, mock_run):
        """Test scan with all-projects flag."""
        snyk_output = {"vulnerabilities": [], "ok": True}
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(snyk_output)
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        scanner = SnykScanner()
        with patch.object(scanner, "is_available", return_value=True):
            result = scanner.scan(
                "/test/path",
                {"scan_all_dependencies": True},
            )

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--all-projects" in call_args


class TestCreateSnykScanner:
    """Tests for create_snyk_scanner factory function."""

    def test_create_default_scanner(self):
        """Test creating scanner with default parameters."""
        scanner = create_snyk_scanner()
        assert isinstance(scanner, SnykScanner)
        assert scanner.scanner_name == "Snyk"

    def test_create_scanner_with_token(self):
        """Test creating scanner with token."""
        scanner = create_snyk_scanner(token="test-token")
        assert isinstance(scanner, SnykScanner)
        assert scanner._token == "test-token"

    def test_create_scanner_with_binary_path(self):
        """Test creating scanner with custom binary path."""
        scanner = create_snyk_scanner(binary_path="/usr/local/bin/snyk")
        assert isinstance(scanner, SnykScanner)
        assert scanner._binary_path == "/usr/local/bin/snyk"