"""
Security Scanning Utilities

Comprehensive security scanning for the V2 platform including:
- Dependency vulnerability scanning
- Static code analysis
- Secret detection
- Container security scanning
- Security report generation
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    """Security issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityIssue:
    """Represents a security issue found during scanning."""

    severity: SeverityLevel
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    cwe_id: Optional[str] = None
    cve_id: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class SecurityScanResult:
    """Results from a security scan."""

    scan_type: str
    timestamp: datetime
    issues: List[SecurityIssue]
    summary: Dict[str, int]
    duration_seconds: float
    scan_successful: bool
    error_message: Optional[str] = None


class DependencyScanner:
    """Scans Python dependencies for known vulnerabilities."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.requirements_files = [
            "requirements.txt",
            "platform/requirements.txt",
            "platform/ui/package.json",
        ]

    async def scan_python_dependencies(self) -> SecurityScanResult:
        """Scan Python dependencies using pip-audit."""
        start_time = datetime.now()
        issues: List[SecurityIssue] = []

        try:
            # Check if pip-audit is installed
            result = subprocess.run(
                ["pip-audit", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return SecurityScanResult(
                    scan_type="dependency_python",
                    timestamp=start_time,
                    issues=[],
                    summary={"error": 1},
                    duration_seconds=0,
                    scan_successful=False,
                    error_message="pip-audit not installed. Install with: pip install pip-audit",
                )

            # Scan requirements files
            for req_file in self.requirements_files:
                req_path = self.project_root / req_file
                if not req_path.exists() or not req_file.endswith(".txt"):
                    continue

                result = subprocess.run(
                    ["pip-audit", "-r", str(req_path), "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=self.project_root,
                )

                if result.returncode == 0 and result.stdout:
                    try:
                        vulnerabilities = json.loads(result.stdout)
                        for vuln in vulnerabilities.get("dependencies", []):
                            for vuln_detail in vuln.get("vulnerabilities", []):
                                issues.append(
                                    SecurityIssue(
                                        severity=self._map_severity(
                                            vuln_detail.get("severity", "medium")
                                        ),
                                        category="dependency",
                                        title=f"Vulnerable dependency: {vuln['name']}",
                                        description=vuln_detail.get(
                                            "description", "No description"
                                        ),
                                        file_path=req_file,
                                        cve_id=vuln_detail.get("id"),
                                        remediation=f"Upgrade {vuln['name']} to {vuln_detail.get('fix_versions', ['latest'])[0]}",
                                        references=[vuln_detail.get("url", "")],
                                    )
                                )
                    except json.JSONDecodeError:
                        pass

            duration = (datetime.now() - start_time).total_seconds()
            summary = self._summarize_issues(issues)

            return SecurityScanResult(
                scan_type="dependency_python",
                timestamp=start_time,
                issues=issues,
                summary=summary,
                duration_seconds=duration,
                scan_successful=True,
            )

        except subprocess.TimeoutExpired:
            return SecurityScanResult(
                scan_type="dependency_python",
                timestamp=start_time,
                issues=[],
                summary={"error": 1},
                duration_seconds=0,
                scan_successful=False,
                error_message="Dependency scan timed out",
            )
        except Exception as e:
            return SecurityScanResult(
                scan_type="dependency_python",
                timestamp=start_time,
                issues=[],
                summary={"error": 1},
                duration_seconds=0,
                scan_successful=False,
                error_message=f"Dependency scan failed: {str(e)}",
            )

    async def scan_npm_dependencies(self) -> SecurityScanResult:
        """Scan NPM dependencies using npm audit."""
        start_time = datetime.now()
        issues: List[SecurityIssue] = []

        try:
            ui_path = self.project_root / "platform" / "ui"
            if not (ui_path / "package.json").exists():
                return SecurityScanResult(
                    scan_type="dependency_npm",
                    timestamp=start_time,
                    issues=[],
                    summary={"info": 1},
                    duration_seconds=0,
                    scan_successful=True,
                    error_message="No package.json found",
                )

            result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=ui_path,
            )

            if result.stdout:
                try:
                    audit_data = json.loads(result.stdout)
                    for vuln_id, vuln_detail in audit_data.get(
                        "vulnerabilities", {}
                    ).items():
                        issues.append(
                            SecurityIssue(
                                severity=self._map_severity(
                                    vuln_detail.get("severity", "medium")
                                ),
                                category="dependency",
                                title=f"Vulnerable NPM package: {vuln_id}",
                                description=vuln_detail.get("via", [{}])[0].get(
                                    "title", "No description"
                                ),
                                file_path="platform/ui/package.json",
                                cve_id=vuln_detail.get("via", [{}])[0].get("cve"),
                                remediation=f"Upgrade to version {vuln_detail.get('fixAvailable', {}).get('version', 'latest')}",
                                references=[
                                    vuln_detail.get("via", [{}])[0].get("url", "")
                                ],
                            )
                        )
                except json.JSONDecodeError:
                    pass

            duration = (datetime.now() - start_time).total_seconds()
            summary = self._summarize_issues(issues)

            return SecurityScanResult(
                scan_type="dependency_npm",
                timestamp=start_time,
                issues=issues,
                summary=summary,
                duration_seconds=duration,
                scan_successful=True,
            )

        except Exception as e:
            return SecurityScanResult(
                scan_type="dependency_npm",
                timestamp=start_time,
                issues=[],
                summary={"error": 1},
                duration_seconds=0,
                scan_successful=False,
                error_message=f"NPM audit failed: {str(e)}",
            )

    @staticmethod
    def _map_severity(severity_str: str) -> SeverityLevel:
        """Map severity string to SeverityLevel enum."""
        severity_map = {
            "critical": SeverityLevel.CRITICAL,
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "moderate": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
            "info": SeverityLevel.INFO,
        }
        return severity_map.get(severity_str.lower(), SeverityLevel.MEDIUM)

    @staticmethod
    def _summarize_issues(issues: List[SecurityIssue]) -> Dict[str, int]:
        """Summarize issues by severity."""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for issue in issues:
            summary[issue.severity.value] += 1
        summary["total"] = len(issues)
        return summary


class StaticCodeAnalyzer:
    """Performs static code analysis for security issues."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.python_paths = [
            "platform/src",
            "platform/cli",
        ]

    async def scan_with_bandit(self) -> SecurityScanResult:
        """Scan Python code with Bandit."""
        start_time = datetime.now()
        issues: List[SecurityIssue] = []

        try:
            # Check if bandit is installed
            result = subprocess.run(
                ["bandit", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return SecurityScanResult(
                    scan_type="static_analysis_bandit",
                    timestamp=start_time,
                    issues=[],
                    summary={"error": 1},
                    duration_seconds=0,
                    scan_successful=False,
                    error_message="Bandit not installed. Install with: pip install bandit",
                )

            # Scan Python directories
            for py_path in self.python_paths:
                full_path = self.project_root / py_path
                if not full_path.exists():
                    continue

                result = subprocess.run(
                    [
                        "bandit",
                        "-r",
                        str(full_path),
                        "-f",
                        "json",
                        "-ll",  # Low severity and above
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=self.project_root,
                )

                if result.stdout:
                    try:
                        bandit_data = json.loads(result.stdout)
                        for result_item in bandit_data.get("results", []):
                            issues.append(
                                SecurityIssue(
                                    severity=self._map_bandit_severity(
                                        result_item.get("issue_severity", "MEDIUM")
                                    ),
                                    category="static_analysis",
                                    title=result_item.get("test_name", "Security issue"),
                                    description=result_item.get(
                                        "issue_text", "No description"
                                    ),
                                    file_path=result_item.get("filename"),
                                    line_number=result_item.get("line_number"),
                                    cwe_id=result_item.get("issue_cwe", {}).get("id"),
                                    remediation=result_item.get(
                                        "more_info", "Review code for security issues"
                                    ),
                                )
                            )
                    except json.JSONDecodeError:
                        pass

            duration = (datetime.now() - start_time).total_seconds()
            summary = self._summarize_issues(issues)

            return SecurityScanResult(
                scan_type="static_analysis_bandit",
                timestamp=start_time,
                issues=issues,
                summary=summary,
                duration_seconds=duration,
                scan_successful=True,
            )

        except Exception as e:
            return SecurityScanResult(
                scan_type="static_analysis_bandit",
                timestamp=start_time,
                issues=[],
                summary={"error": 1},
                duration_seconds=0,
                scan_successful=False,
                error_message=f"Bandit scan failed: {str(e)}",
            )

    @staticmethod
    def _map_bandit_severity(severity_str: str) -> SeverityLevel:
        """Map Bandit severity to SeverityLevel."""
        severity_map = {
            "HIGH": SeverityLevel.HIGH,
            "MEDIUM": SeverityLevel.MEDIUM,
            "LOW": SeverityLevel.LOW,
        }
        return severity_map.get(severity_str.upper(), SeverityLevel.MEDIUM)

    @staticmethod
    def _summarize_issues(issues: List[SecurityIssue]) -> Dict[str, int]:
        """Summarize issues by severity."""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for issue in issues:
            summary[issue.severity.value] += 1
        summary["total"] = len(issues)
        return summary


class SecretDetector:
    """Detects hardcoded secrets in code."""

    # Common secret patterns
    SECRET_PATTERNS = {
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret_key": r"aws(.{0,20})?['\"][0-9a-zA-Z/+]{40}['\"]",
        "github_token": r"ghp_[0-9a-zA-Z]{36}",
        "github_oauth": r"gho_[0-9a-zA-Z]{36}",
        "generic_api_key": r"[aA][pP][iI]_?[kK][eE][yY].*['\"][0-9a-zA-Z]{32,45}['\"]",
        "generic_secret": r"[sS][eE][cC][rR][eE][tT].*['\"][0-9a-zA-Z]{32,45}['\"]",
        "password": r"[pP][aA][sS][sS][wW][oO][rR][dD].*['\"][^'\"]{8,}['\"]",
        "private_key": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
        "jwt_token": r"eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
        "slack_token": r"xox[baprs]-([0-9a-zA-Z]{10,48})",
        "slack_webhook": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}",
        "stripe_key": r"sk_live_[0-9a-zA-Z]{24}",
        "google_oauth": r"ya29\.[0-9A-Za-z\-_]+",
        "heroku_api_key": r"[hH][eE][rR][oO][kK][uU].*[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}",
    }

    # Files to exclude from scanning
    EXCLUDE_PATTERNS = {
        "*.pyc",
        "*.pyo",
        "*.git*",
        "node_modules/*",
        "venv/*",
        ".venv/*",
        "*.min.js",
        "*.bundle.js",
        "htmlcov/*",
        "*.log",
        "backups/*",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    async def scan_for_secrets(self) -> SecurityScanResult:
        """Scan codebase for hardcoded secrets."""
        start_time = datetime.now()
        issues: List[SecurityIssue] = []

        try:
            # Scan all text files
            for file_path in self._get_scannable_files():
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        for line_num, line in enumerate(content.splitlines(), start=1):
                            for secret_type, pattern in self.SECRET_PATTERNS.items():
                                matches = re.finditer(pattern, line)
                                for match in matches:
                                    # Skip false positives (env vars, placeholders)
                                    if self._is_false_positive(match.group()):
                                        continue

                                    rel_path = file_path.relative_to(self.project_root)
                                    issues.append(
                                        SecurityIssue(
                                            severity=SeverityLevel.CRITICAL,
                                            category="secret_detection",
                                            title=f"Potential {secret_type.replace('_', ' ')} found",
                                            description=f"Found pattern matching {secret_type} in source code",
                                            file_path=str(rel_path),
                                            line_number=line_num,
                                            remediation="Remove hardcoded secrets and use environment variables or secret management",
                                        )
                                    )
                except (UnicodeDecodeError, PermissionError):
                    continue

            duration = (datetime.now() - start_time).total_seconds()
            summary = self._summarize_issues(issues)

            return SecurityScanResult(
                scan_type="secret_detection",
                timestamp=start_time,
                issues=issues,
                summary=summary,
                duration_seconds=duration,
                scan_successful=True,
            )

        except Exception as e:
            return SecurityScanResult(
                scan_type="secret_detection",
                timestamp=start_time,
                issues=[],
                summary={"error": 1},
                duration_seconds=0,
                scan_successful=False,
                error_message=f"Secret detection failed: {str(e)}",
            )

    def _get_scannable_files(self) -> List[Path]:
        """Get list of files to scan."""
        scannable_files = []

        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [
                d
                for d in dirs
                if not any(
                    Path(root, d).match(pattern) for pattern in self.EXCLUDE_PATTERNS
                )
            ]

            for file in files:
                file_path = Path(root, file)

                # Skip excluded files
                if any(file_path.match(pattern) for pattern in self.EXCLUDE_PATTERNS):
                    continue

                # Only scan text files
                if file.endswith(
                    (
                        ".py",
                        ".js",
                        ".ts",
                        ".tsx",
                        ".jsx",
                        ".env",
                        ".yml",
                        ".yaml",
                        ".json",
                        ".conf",
                        ".config",
                        ".sh",
                    )
                ):
                    scannable_files.append(file_path)

        return scannable_files

    @staticmethod
    def _is_false_positive(match_str: str) -> bool:
        """Check if matched string is likely a false positive."""
        false_positive_indicators = [
            "example",
            "sample",
            "placeholder",
            "your_",
            "my_",
            "test_",
            "<",
            ">",
            "{",
            "}",
            "[",
            "]",
            "xxx",
            "yyy",
            "zzz",
            "...",
        ]
        match_lower = match_str.lower()
        return any(indicator in match_lower for indicator in false_positive_indicators)

    @staticmethod
    def _summarize_issues(issues: List[SecurityIssue]) -> Dict[str, int]:
        """Summarize issues by severity."""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for issue in issues:
            summary[issue.severity.value] += 1
        summary["total"] = len(issues)
        return summary


class ContainerScanner:
    """Scans Docker containers for vulnerabilities."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    async def scan_with_trivy(self) -> SecurityScanResult:
        """Scan containers using Trivy."""
        start_time = datetime.now()
        issues: List[SecurityIssue] = []

        try:
            # Check if Trivy is installed
            result = subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return SecurityScanResult(
                    scan_type="container_trivy",
                    timestamp=start_time,
                    issues=[],
                    summary={"info": 1},
                    duration_seconds=0,
                    scan_successful=False,
                    error_message="Trivy not installed. Install from: https://github.com/aquasecurity/trivy",
                )

            # Get list of running containers
            containers_result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--format",
                    "{{.Names}}",
                    "--filter",
                    "name=agentic-",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if containers_result.returncode != 0:
                return SecurityScanResult(
                    scan_type="container_trivy",
                    timestamp=start_time,
                    issues=[],
                    summary={"info": 1},
                    duration_seconds=0,
                    scan_successful=False,
                    error_message="Docker not available or no containers running",
                )

            containers = containers_result.stdout.strip().split("\n")
            containers = [c for c in containers if c]

            # Scan each container
            for container_name in containers[:5]:  # Limit to 5 containers for speed
                result = subprocess.run(
                    [
                        "trivy",
                        "image",
                        "--format",
                        "json",
                        "--severity",
                        "HIGH,CRITICAL",
                        container_name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.stdout:
                    try:
                        trivy_data = json.loads(result.stdout)
                        for result_item in trivy_data.get("Results", []):
                            for vuln in result_item.get("Vulnerabilities", []):
                                issues.append(
                                    SecurityIssue(
                                        severity=self._map_trivy_severity(
                                            vuln.get("Severity", "MEDIUM")
                                        ),
                                        category="container",
                                        title=f"Container vulnerability: {vuln.get('VulnerabilityID')}",
                                        description=vuln.get("Title", "No description"),
                                        file_path=f"container:{container_name}",
                                        cve_id=vuln.get("VulnerabilityID"),
                                        remediation=f"Update {vuln.get('PkgName')} to {vuln.get('FixedVersion', 'latest')}",
                                        references=vuln.get("References", []),
                                    )
                                )
                    except json.JSONDecodeError:
                        pass

            duration = (datetime.now() - start_time).total_seconds()
            summary = self._summarize_issues(issues)

            return SecurityScanResult(
                scan_type="container_trivy",
                timestamp=start_time,
                issues=issues,
                summary=summary,
                duration_seconds=duration,
                scan_successful=True,
            )

        except Exception as e:
            return SecurityScanResult(
                scan_type="container_trivy",
                timestamp=start_time,
                issues=[],
                summary={"error": 1},
                duration_seconds=0,
                scan_successful=False,
                error_message=f"Trivy scan failed: {str(e)}",
            )

    @staticmethod
    def _map_trivy_severity(severity_str: str) -> SeverityLevel:
        """Map Trivy severity to SeverityLevel."""
        severity_map = {
            "CRITICAL": SeverityLevel.CRITICAL,
            "HIGH": SeverityLevel.HIGH,
            "MEDIUM": SeverityLevel.MEDIUM,
            "LOW": SeverityLevel.LOW,
            "UNKNOWN": SeverityLevel.INFO,
        }
        return severity_map.get(severity_str.upper(), SeverityLevel.MEDIUM)

    @staticmethod
    def _summarize_issues(issues: List[SecurityIssue]) -> Dict[str, int]:
        """Summarize issues by severity."""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for issue in issues:
            summary[issue.severity.value] += 1
        summary["total"] = len(issues)
        return summary


class SecurityReportGenerator:
    """Generates comprehensive security reports."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "security-reports"
        self.reports_dir.mkdir(exist_ok=True)

    def generate_report(
        self,
        scan_results: List[SecurityScanResult],
        output_format: str = "markdown",
    ) -> str:
        """Generate security report from scan results."""
        if output_format == "markdown":
            return self._generate_markdown_report(scan_results)
        elif output_format == "json":
            return self._generate_json_report(scan_results)
        elif output_format == "html":
            return self._generate_html_report(scan_results)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _generate_markdown_report(
        self, scan_results: List[SecurityScanResult]
    ) -> str:
        """Generate Markdown format report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines = [
            "# Security Scan Report",
            "",
            f"**Generated:** {timestamp}",
            f"**Platform:** Story Portal V2 Platform",
            "",
            "## Executive Summary",
            "",
        ]

        # Calculate totals
        total_issues = sum(r.summary.get("total", 0) for r in scan_results)
        total_critical = sum(r.summary.get("critical", 0) for r in scan_results)
        total_high = sum(r.summary.get("high", 0) for r in scan_results)
        total_medium = sum(r.summary.get("medium", 0) for r in scan_results)
        total_low = sum(r.summary.get("low", 0) for r in scan_results)

        report_lines.extend(
            [
                f"- **Total Issues:** {total_issues}",
                f"- **Critical:** {total_critical}",
                f"- **High:** {total_high}",
                f"- **Medium:** {total_medium}",
                f"- **Low:** {total_low}",
                "",
                "## Scan Results by Type",
                "",
            ]
        )

        # Results by scan type
        for scan_result in scan_results:
            report_lines.extend(
                [
                    f"### {scan_result.scan_type.replace('_', ' ').title()}",
                    "",
                    f"- **Status:** {'✅ Success' if scan_result.scan_successful else '❌ Failed'}",
                    f"- **Duration:** {scan_result.duration_seconds:.2f}s",
                    f"- **Issues Found:** {scan_result.summary.get('total', 0)}",
                    "",
                ]
            )

            if not scan_result.scan_successful:
                report_lines.append(f"**Error:** {scan_result.error_message}")
                report_lines.append("")
                continue

            if scan_result.issues:
                report_lines.append("**Issues:**")
                report_lines.append("")

                # Group by severity
                for severity in [
                    SeverityLevel.CRITICAL,
                    SeverityLevel.HIGH,
                    SeverityLevel.MEDIUM,
                    SeverityLevel.LOW,
                ]:
                    severity_issues = [
                        issue
                        for issue in scan_result.issues
                        if issue.severity == severity
                    ]
                    if severity_issues:
                        report_lines.append(
                            f"#### {severity.value.upper()} Severity"
                        )
                        report_lines.append("")
                        for issue in severity_issues[:10]:  # Limit to 10 per severity
                            report_lines.append(f"- **{issue.title}**")
                            if issue.file_path:
                                location = issue.file_path
                                if issue.line_number:
                                    location += f":{issue.line_number}"
                                report_lines.append(f"  - Location: `{location}`")
                            if issue.description:
                                report_lines.append(f"  - {issue.description}")
                            if issue.remediation:
                                report_lines.append(f"  - Fix: {issue.remediation}")
                            report_lines.append("")

        # Recommendations
        report_lines.extend(
            [
                "## Recommendations",
                "",
                "### Immediate Actions (Critical/High)",
                "",
            ]
        )

        critical_high_issues = [
            issue
            for result in scan_results
            for issue in result.issues
            if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
        ]

        if critical_high_issues:
            for i, issue in enumerate(critical_high_issues[:5], 1):
                report_lines.append(
                    f"{i}. {issue.title} - {issue.remediation or 'Review and fix'}"
                )
            report_lines.append("")
        else:
            report_lines.append("✅ No critical or high severity issues found.")
            report_lines.append("")

        report_lines.extend(
            [
                "### Best Practices",
                "",
                "1. Keep all dependencies up to date",
                "2. Use environment variables for secrets",
                "3. Implement security scanning in CI/CD",
                "4. Regular security audits",
                "5. Container image scanning before deployment",
                "",
            ]
        )

        return "\n".join(report_lines)

    def _generate_json_report(self, scan_results: List[SecurityScanResult]) -> str:
        """Generate JSON format report."""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "platform": "Story Portal V2 Platform",
            "scan_results": [
                {
                    "scan_type": result.scan_type,
                    "timestamp": result.timestamp.isoformat(),
                    "successful": result.scan_successful,
                    "duration_seconds": result.duration_seconds,
                    "summary": result.summary,
                    "issues": [
                        {
                            "severity": issue.severity.value,
                            "category": issue.category,
                            "title": issue.title,
                            "description": issue.description,
                            "file_path": issue.file_path,
                            "line_number": issue.line_number,
                            "cwe_id": issue.cwe_id,
                            "cve_id": issue.cve_id,
                            "remediation": issue.remediation,
                            "references": issue.references,
                        }
                        for issue in result.issues
                    ],
                    "error": result.error_message,
                }
                for result in scan_results
            ],
        }
        return json.dumps(report_data, indent=2)

    def _generate_html_report(self, scan_results: List[SecurityScanResult]) -> str:
        """Generate HTML format report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_issues = sum(r.summary.get("total", 0) for r in scan_results)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .severity-critical {{ color: #d9534f; font-weight: bold; }}
        .severity-high {{ color: #f0ad4e; font-weight: bold; }}
        .severity-medium {{ color: #5bc0de; font-weight: bold; }}
        .severity-low {{ color: #5cb85c; }}
        .issue {{ border-left: 4px solid #ddd; padding: 10px; margin: 10px 0; }}
        .issue-critical {{ border-left-color: #d9534f; }}
        .issue-high {{ border-left-color: #f0ad4e; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f0f0f0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Security Scan Report</h1>
        <p><strong>Generated:</strong> {timestamp}</p>
        <p><strong>Platform:</strong> Story Portal V2 Platform</p>

        <div class="summary">
            <h2>Executive Summary</h2>
            <p><strong>Total Issues Found:</strong> {total_issues}</p>
        </div>

        <h2>Scan Results</h2>
        <table>
            <tr>
                <th>Scan Type</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Issues</th>
            </tr>
"""

        for result in scan_results:
            status = "✅ Success" if result.scan_successful else "❌ Failed"
            html += f"""
            <tr>
                <td>{result.scan_type.replace('_', ' ').title()}</td>
                <td>{status}</td>
                <td>{result.duration_seconds:.2f}s</td>
                <td>{result.summary.get('total', 0)}</td>
            </tr>
"""

        html += """
        </table>
    </div>
</body>
</html>
"""
        return html

    def save_report(self, report_content: str, format_type: str) -> Path:
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"security-report-{timestamp}.{format_type}"
        report_path = self.reports_dir / filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return report_path


class SecurityScanner:
    """Main security scanner coordinator."""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path.cwd()
        self.project_root = project_root

        self.dependency_scanner = DependencyScanner(project_root)
        self.static_analyzer = StaticCodeAnalyzer(project_root)
        self.secret_detector = SecretDetector(project_root)
        self.container_scanner = ContainerScanner(project_root)
        self.report_generator = SecurityReportGenerator(project_root)

    async def run_all_scans(
        self, include_containers: bool = True
    ) -> List[SecurityScanResult]:
        """Run all security scans."""
        logger.info("🔍 Starting security scans...")

        scan_tasks = [
            ("Python Dependencies", self.dependency_scanner.scan_python_dependencies()),
            ("NPM Dependencies", self.dependency_scanner.scan_npm_dependencies()),
            ("Static Analysis (Bandit)", self.static_analyzer.scan_with_bandit()),
            ("Secret Detection", self.secret_detector.scan_for_secrets()),
        ]

        if include_containers:
            scan_tasks.append(
                ("Container Scan (Trivy)", self.container_scanner.scan_with_trivy())
            )

        results = []
        for scan_name, scan_coro in scan_tasks:
            logger.info(f"  Running {scan_name}...")
            result = await scan_coro
            results.append(result)
            if result.scan_successful:
                logger.info(
                    f"    ✅ Complete: {result.summary.get('total', 0)} issues found"
                )
            else:
                logger.warning(f"    ⚠️  {result.error_message}")

        return results

    async def generate_and_save_reports(
        self, scan_results: List[SecurityScanResult]
    ) -> Dict[str, Path]:
        """Generate and save reports in multiple formats."""
        logger.info("📝 Generating reports...")

        reports = {}

        # Markdown report
        md_content = self.report_generator.generate_report(scan_results, "markdown")
        md_path = self.report_generator.save_report(md_content, "md")
        reports["markdown"] = md_path
        logger.info(f"  ✅ Markdown report: {md_path}")

        # JSON report
        json_content = self.report_generator.generate_report(scan_results, "json")
        json_path = self.report_generator.save_report(json_content, "json")
        reports["json"] = json_path
        logger.info(f"  ✅ JSON report: {json_path}")

        # HTML report
        html_content = self.report_generator.generate_report(scan_results, "html")
        html_path = self.report_generator.save_report(html_content, "html")
        reports["html"] = html_path
        logger.info(f"  ✅ HTML report: {html_path}")

        return reports


# CLI interface
async def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Security Scanner for V2 Platform")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--no-containers",
        action="store_true",
        help="Skip container scanning",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "html", "all"],
        default="all",
        help="Report format",
    )

    args = parser.parse_args()

    scanner = SecurityScanner(args.project_root)

    # Run all scans
    results = await scanner.run_all_scans(include_containers=not args.no_containers)

    # Generate reports
    reports = await scanner.generate_and_save_reports(results)

    # Print summary
    total_issues = sum(r.summary.get("total", 0) for r in results)
    critical_issues = sum(r.summary.get("critical", 0) for r in results)
    high_issues = sum(r.summary.get("high", 0) for r in results)

    logger.info("=" * 60)
    logger.info("📊 Security Scan Summary")
    logger.info("=" * 60)
    logger.info(f"Total Issues: {total_issues}")
    logger.info(f"  Critical: {critical_issues}")
    logger.info(f"  High: {high_issues}")
    logger.info("=" * 60)
    logger.info(f"📁 Reports saved to: {scanner.report_generator.reports_dir}")

    # Exit with error code if critical issues found
    if critical_issues > 0:
        logger.error("⚠️  CRITICAL ISSUES FOUND - Review and fix immediately!")
        sys.exit(1)
    elif high_issues > 0:
        logger.warning("⚠️  HIGH SEVERITY ISSUES FOUND - Review and fix soon")
        sys.exit(1)
    else:
        logger.info("✅ No critical or high severity issues found")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
