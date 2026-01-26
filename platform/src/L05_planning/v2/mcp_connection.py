"""
L05 MCP Connection Utilities.

Provides health checking and connection validation for the L05 planning
pipeline when invoked via MCP tools.
"""

import subprocess
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MCPStatus(Enum):
    """MCP connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class MCPHealthResult:
    """Result of MCP health check."""
    healthy: bool
    status: MCPStatus
    server_name: str
    error: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.healthy,
            "status": self.status.value,
            "server_name": self.server_name,
            "error": self.error,
            "suggestion": self.suggestion,
        }


def check_mcp_health(server_name: str = "platform-services") -> MCPHealthResult:
    """
    Check if the platform-services MCP server is connected.

    Args:
        server_name: Name of the MCP server to check

    Returns:
        MCPHealthResult with connection status
    """
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return MCPHealthResult(
                healthy=False,
                status=MCPStatus.ERROR,
                server_name=server_name,
                error=f"claude mcp list failed: {result.stderr}",
                suggestion="Ensure Claude Code CLI is available in PATH",
            )

        # Parse output to find server status
        for line in result.stdout.split("\n"):
            if server_name in line:
                if "✓ Connected" in line:
                    return MCPHealthResult(
                        healthy=True,
                        status=MCPStatus.CONNECTED,
                        server_name=server_name,
                    )
                elif "✗" in line or "Disconnected" in line:
                    return MCPHealthResult(
                        healthy=False,
                        status=MCPStatus.DISCONNECTED,
                        server_name=server_name,
                        error="Server shows disconnected status",
                        suggestion="Restart Claude Code session to reconnect",
                    )

        return MCPHealthResult(
            healthy=False,
            status=MCPStatus.UNKNOWN,
            server_name=server_name,
            error=f"Server '{server_name}' not found in MCP list",
            suggestion="Add the server: claude mcp add platform-services ...",
        )

    except subprocess.TimeoutExpired:
        return MCPHealthResult(
            healthy=False,
            status=MCPStatus.ERROR,
            server_name=server_name,
            error="Health check timed out",
            suggestion="Claude Code CLI may be unresponsive",
        )
    except FileNotFoundError:
        return MCPHealthResult(
            healthy=False,
            status=MCPStatus.ERROR,
            server_name=server_name,
            error="Claude Code CLI not found",
            suggestion="Install Claude Code CLI or add to PATH",
        )
    except Exception as e:
        return MCPHealthResult(
            healthy=False,
            status=MCPStatus.ERROR,
            server_name=server_name,
            error=str(e),
        )


def validate_service_availability(service_name: str = "PlanningService") -> Dict[str, Any]:
    """
    Validate that a specific service can be instantiated.

    This performs a lightweight check to ensure imports work correctly.

    Args:
        service_name: Name of the service to validate

    Returns:
        Dict with validation results
    """
    results = {
        "service_name": service_name,
        "available": False,
        "imports_ok": False,
        "dependencies_ok": False,
        "errors": [],
    }

    # Check imports
    try:
        if service_name == "PlanningService":
            from src.L05_planning.services.planning_service import PlanningService
            from src.L05_planning.services import planning_service as ps_module

            results["imports_ok"] = True

            # Check cross-layer dependencies
            deps = {
                "ModelGateway": ps_module.ModelGateway is not None,
                "AgentExecutor": ps_module.AgentExecutor is not None,
                "ToolExecutor": ps_module.ToolExecutor is not None,
            }
            results["dependencies"] = deps
            results["dependencies_ok"] = all(deps.values())

            if not results["dependencies_ok"]:
                missing = [k for k, v in deps.items() if not v]
                results["errors"].append(f"Missing dependencies: {missing}")

            results["available"] = results["imports_ok"] and results["dependencies_ok"]

    except ImportError as e:
        results["errors"].append(f"Import error: {e}")
    except Exception as e:
        results["errors"].append(f"Validation error: {e}")

    return results


def get_pipeline_readiness() -> Dict[str, Any]:
    """
    Check overall L05 pipeline readiness.

    Returns comprehensive status of all components needed for execution.
    """
    readiness = {
        "ready": False,
        "mcp": None,
        "services": {},
        "issues": [],
        "suggestions": [],
    }

    # Check MCP
    mcp_health = check_mcp_health()
    readiness["mcp"] = mcp_health.to_dict()

    if not mcp_health.healthy:
        readiness["issues"].append(f"MCP not connected: {mcp_health.error}")
        if mcp_health.suggestion:
            readiness["suggestions"].append(mcp_health.suggestion)

    # Check core services
    for service in ["PlanningService"]:
        validation = validate_service_availability(service)
        readiness["services"][service] = validation

        if not validation["available"]:
            readiness["issues"].extend(validation["errors"])

    # Overall readiness
    readiness["ready"] = (
        mcp_health.healthy and
        all(s["available"] for s in readiness["services"].values())
    )

    return readiness


def format_readiness_report(readiness: Dict[str, Any]) -> str:
    """Format readiness check as human-readable report."""
    lines = ["## L05 Pipeline Readiness Check", ""]

    # Overall status
    status = "✅ Ready" if readiness["ready"] else "❌ Not Ready"
    lines.append(f"**Status:** {status}")
    lines.append("")

    # MCP
    mcp = readiness.get("mcp", {})
    mcp_status = "✓" if mcp.get("healthy") else "✗"
    lines.append(f"**MCP ({mcp.get('server_name', 'unknown')}):** {mcp_status} {mcp.get('status', 'unknown')}")

    # Services
    lines.append("")
    lines.append("**Services:**")
    for name, info in readiness.get("services", {}).items():
        svc_status = "✓" if info.get("available") else "✗"
        lines.append(f"  - {name}: {svc_status}")
        if info.get("dependencies"):
            for dep, ok in info["dependencies"].items():
                dep_status = "✓" if ok else "✗"
                lines.append(f"    - {dep}: {dep_status}")

    # Issues
    if readiness.get("issues"):
        lines.append("")
        lines.append("**Issues:**")
        for issue in readiness["issues"]:
            lines.append(f"  - {issue}")

    # Suggestions
    if readiness.get("suggestions"):
        lines.append("")
        lines.append("**Suggestions:**")
        for suggestion in readiness["suggestions"]:
            lines.append(f"  - {suggestion}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Run readiness check when executed directly
    import sys

    readiness = get_pipeline_readiness()

    if "--json" in sys.argv:
        print(json.dumps(readiness, indent=2))
    else:
        print(format_readiness_report(readiness))

    sys.exit(0 if readiness["ready"] else 1)
