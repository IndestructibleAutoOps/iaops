import hashlib
import re


class SecurityScanner:
    SIGNATURE_DBLES = re.compile(r"(?i)(secret|password|api[_-]?key|token)")
    VULNERABLE_PATTERNS = [
        re.compile(r"(<script|javascript:|on\w+\s*=)", re.IGNORECASE),
        re.compile(r"(union\s+select|select\s.*from)", re.IGNORECASE),
    ]

    def scan_file(self, path: str, content: str):
        """Run security scan on a file path + content and return a structured report."""
        report = {
            "filename": path,
            "pattern_match": False,
            "sensitive_data": False,
            "vulnerabilities": [],
        }

        if re.search(r"\.(env|key|secret)$", path):
            report["pattern_match"] = True

        if self.SIGNATURE_DBLES.search(content):
            report["sensitive_data"] = True

        for pattern in self.VULNERABLE_PATTERNS:
            if pattern.search(content):
                report["vulnerabilities"].append(f"Detected pattern: {pattern.pattern}")

        report["content_hash"] = hashlib.sha256(content.encode()).hexdigest()
        report["is_safe"] = not (
            report["pattern_match"]
            or report["sensitive_data"]
            or report["vulnerabilities"]
        )

        return report
