#!/usr/bin/env python3
"""
Load Role Definitions into L13 Role Management Service.

Reads role YAML files from a directory and registers each role with the
L13 Role Management service via its HTTP API.

Usage:
    python scripts/load_roles.py --directory .claude/roles/
    python scripts/load_roles.py --dry-run
    python scripts/load_roles.py --verbose

Examples:
    # Load all roles from default directory
    python scripts/load_roles.py

    # Preview without loading
    python scripts/load_roles.py --dry-run

    # Load from custom directory with verbose output
    python scripts/load_roles.py --directory /path/to/roles --verbose

    # Specify custom L13 service URL
    python scripts/load_roles.py --url http://localhost:8013
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


# Default configuration
DEFAULT_ROLE_DIR = ".claude/roles"
DEFAULT_L13_URL = "http://localhost:8013"
DEFAULT_TIMEOUT = 30


class RoleLoader:
    """
    Loads role definitions from YAML files and registers them with L13.
    """

    def __init__(
        self,
        role_directory: str,
        l13_url: str,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the RoleLoader.

        Args:
            role_directory: Path to directory containing role YAML files
            l13_url: Base URL of the L13 Role Management service
            dry_run: If True, preview without making API calls
            verbose: If True, print detailed output
        """
        self.role_directory = Path(role_directory).expanduser().resolve()
        self.l13_url = l13_url.rstrip("/")
        self.dry_run = dry_run
        self.verbose = verbose
        self.loaded_roles: List[Dict[str, Any]] = []
        self.failed_roles: List[Tuple[str, str]] = []
        self.skipped_roles: List[Tuple[str, str]] = []

    def log(self, message: str, force: bool = False) -> None:
        """Print message if verbose mode or force is True."""
        if self.verbose or force:
            print(message)

    def log_progress(self, message: str) -> None:
        """Print progress message (always visible)."""
        print(message)

    def find_role_files(self) -> List[Path]:
        """
        Find all YAML files in the role directory.

        Returns:
            List of paths to role YAML files
        """
        if not self.role_directory.exists():
            raise FileNotFoundError(f"Role directory not found: {self.role_directory}")

        if not self.role_directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.role_directory}")

        role_files = []
        for pattern in ["*.yaml", "*.yml"]:
            role_files.extend(self.role_directory.glob(pattern))

        return sorted(role_files)

    def parse_role_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a role YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed role data as dictionary
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"Empty YAML file: {file_path}")

        return data

    def transform_role_for_api(
        self, role_data: Dict[str, Any], file_path: Path
    ) -> Dict[str, Any]:
        """
        Transform role data from YAML format to L13 API format.

        Args:
            role_data: Raw role data from YAML
            file_path: Path to the source file (for error messages)

        Returns:
            Role data in L13 API format
        """
        # Required fields
        if "name" not in role_data:
            raise ValueError(f"Missing 'name' field in {file_path}")

        # Map YAML fields to L13 RoleCreate model
        api_data = {
            "name": role_data["name"],
            "department": role_data.get("department", "General"),
            "description": role_data.get("description", f"Role: {role_data['name']}"),
        }

        # Map role_type / taskType
        if "role_type" in role_data:
            api_data["role_type"] = role_data["role_type"]
        elif "taskType" in role_data:
            # Convert taskType to role_type enum
            type_mapping = {
                "human_primary": "human_primary",
                "ai_primary": "ai_primary",
                "hybrid": "hybrid",
            }
            api_data["role_type"] = type_mapping.get(role_data["taskType"], "hybrid")
        else:
            api_data["role_type"] = "hybrid"

        # Map skills from core_skills
        if "core_skills" in role_data:
            api_data["skills"] = [
                {
                    "name": skill,
                    "level": "intermediate",
                    "weight": 1.0,
                }
                for skill in role_data["core_skills"]
            ]
        elif "skills" in role_data:
            # Already in skill format
            api_data["skills"] = role_data["skills"]

        # Map responsibilities
        if "responsibilities" in role_data:
            api_data["responsibilities"] = role_data["responsibilities"]

        # Map keywords to tags
        if "keywords" in role_data:
            api_data["tags"] = role_data["keywords"]
        elif "tags" in role_data:
            api_data["tags"] = role_data["tags"]

        # Map capabilities to metadata
        if "capabilities" in role_data:
            api_data["metadata"] = {"capabilities": role_data["capabilities"]}

        # Map priority
        if "priority" in role_data:
            # Ensure priority is in range 1-10
            priority = int(role_data["priority"])
            api_data["priority"] = max(1, min(10, priority))

        # Map principles to metadata
        if "principles" in role_data:
            if "metadata" not in api_data:
                api_data["metadata"] = {}
            api_data["metadata"]["principles"] = role_data["principles"]

        # Map constraints if present
        if "constraints" in role_data:
            api_data["constraints"] = role_data["constraints"]

        # Map token_budget if present
        if "token_budget" in role_data:
            api_data["token_budget"] = role_data["token_budget"]

        return api_data

    def check_role_exists(self, role_name: str) -> bool:
        """
        Check if a role already exists in L13.

        Args:
            role_name: Name of the role to check

        Returns:
            True if role exists, False otherwise
        """
        try:
            response = requests.get(
                f"{self.l13_url}/roles/by-name/{role_name}",
                timeout=DEFAULT_TIMEOUT,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def register_role(self, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a role with the L13 service.

        Args:
            role_data: Role data in API format

        Returns:
            Response data from the API
        """
        response = requests.post(
            f"{self.l13_url}/roles/",
            json=role_data,
            headers={"Content-Type": "application/json"},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def load_single_role(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load a single role from a file.

        Args:
            file_path: Path to the role YAML file

        Returns:
            Loaded role data or None if failed
        """
        self.log(f"  Processing: {file_path.name}")

        try:
            # Parse YAML
            role_data = self.parse_role_file(file_path)
            self.log(f"    Parsed: {role_data.get('name', 'unknown')}")

            # Transform to API format
            api_data = self.transform_role_for_api(role_data, file_path)
            self.log(f"    Transformed to API format")

            if self.dry_run:
                self.log(f"    [DRY RUN] Would register role: {api_data['name']}")
                return api_data

            # Check if role already exists
            if self.check_role_exists(api_data["name"]):
                self.skipped_roles.append((file_path.name, "Role already exists"))
                self.log(f"    Skipped: Role already exists")
                return None

            # Register with L13
            result = self.register_role(api_data)
            self.log(f"    Registered: ID={result.get('id', 'unknown')}")
            return result

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML: {e}"
            self.failed_roles.append((file_path.name, error_msg))
            self.log(f"    Error: {error_msg}", force=True)
            return None
        except ValueError as e:
            error_msg = str(e)
            self.failed_roles.append((file_path.name, error_msg))
            self.log(f"    Error: {error_msg}", force=True)
            return None
        except requests.RequestException as e:
            error_msg = f"API error: {e}"
            self.failed_roles.append((file_path.name, error_msg))
            self.log(f"    Error: {error_msg}", force=True)
            return None

    def load_all_roles(self) -> None:
        """Load all roles from the role directory."""
        self.log_progress(f"\n{'='*60}")
        self.log_progress("Role Loader - L13 Role Management")
        self.log_progress(f"{'='*60}")
        self.log_progress(f"Role directory: {self.role_directory}")
        self.log_progress(f"L13 URL: {self.l13_url}")
        self.log_progress(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        self.log_progress(f"{'='*60}\n")

        # Find role files
        try:
            role_files = self.find_role_files()
        except (FileNotFoundError, NotADirectoryError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if not role_files:
            self.log_progress("No role files found.")
            return

        self.log_progress(f"Found {len(role_files)} role file(s)\n")

        # Load each role
        for file_path in role_files:
            result = self.load_single_role(file_path)
            if result:
                self.loaded_roles.append(result)

        self.print_summary()

    def print_summary(self) -> None:
        """Print summary of loaded roles by department."""
        self.log_progress(f"\n{'='*60}")
        self.log_progress("Summary")
        self.log_progress(f"{'='*60}")

        # Group by department
        by_department: Dict[str, List[str]] = defaultdict(list)
        for role in self.loaded_roles:
            dept = role.get("department", "Unknown")
            name = role.get("name", "Unknown")
            by_department[dept].append(name)

        if by_department:
            self.log_progress("\nRoles by Department:")
            for dept, roles in sorted(by_department.items()):
                self.log_progress(f"  {dept}:")
                for role in roles:
                    self.log_progress(f"    - {role}")

        self.log_progress(f"\nResults:")
        self.log_progress(f"  Loaded:  {len(self.loaded_roles)}")
        self.log_progress(f"  Skipped: {len(self.skipped_roles)}")
        self.log_progress(f"  Failed:  {len(self.failed_roles)}")

        if self.skipped_roles:
            self.log_progress("\nSkipped roles:")
            for name, reason in self.skipped_roles:
                self.log_progress(f"  - {name}: {reason}")

        if self.failed_roles:
            self.log_progress("\nFailed roles:")
            for name, reason in self.failed_roles:
                self.log_progress(f"  - {name}: {reason}")

        if self.dry_run:
            self.log_progress("\n[DRY RUN] No changes were made.")


def find_default_role_directory() -> Path:
    """
    Find the default role directory.

    Looks for .claude/roles/ in the current directory or project root.
    """
    # Try current directory
    cwd = Path.cwd()
    role_dir = cwd / DEFAULT_ROLE_DIR
    if role_dir.exists():
        return role_dir

    # Try parent directories (looking for .claude/roles)
    for parent in cwd.parents:
        role_dir = parent / DEFAULT_ROLE_DIR
        if role_dir.exists():
            return role_dir
        # Stop at git root
        if (parent / ".git").exists():
            break

    # Return default path even if it doesn't exist
    return cwd / DEFAULT_ROLE_DIR


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load role definitions into L13 Role Management service.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Load roles from default directory
  %(prog)s --dry-run               Preview without loading
  %(prog)s -d /path/to/roles       Load from custom directory
  %(prog)s --url http://host:8013  Use custom L13 URL
  %(prog)s -v                      Verbose output
        """,
    )

    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=None,
        help=f"Directory containing role YAML files (default: {DEFAULT_ROLE_DIR})",
    )

    parser.add_argument(
        "--url",
        type=str,
        default=os.environ.get("L13_URL", DEFAULT_L13_URL),
        help=f"L13 Role Management service URL (default: {DEFAULT_L13_URL})",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview roles without loading them",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )

    args = parser.parse_args()

    # Determine role directory
    if args.directory:
        role_dir = args.directory
    else:
        role_dir = str(find_default_role_directory())

    # Create loader and run
    loader = RoleLoader(
        role_directory=role_dir,
        l13_url=args.url,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    try:
        loader.load_all_roles()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 1

    # Return non-zero if there were failures
    if loader.failed_roles:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
