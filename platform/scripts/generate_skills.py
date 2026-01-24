#!/usr/bin/env python3
"""
Generate Missing Skills for Roles using L14 Skill Library Service.

Reads role definitions to find required skills (core_skills field),
checks which skills already exist in the skill directory, and generates
missing skills using the L14 Skill Library service.

Usage:
    python scripts/generate_skills.py
    python scripts/generate_skills.py --role developer
    python scripts/generate_skills.py --batch --output-dir .claude/skills/
    python scripts/generate_skills.py --verbose

Examples:
    # Generate skills for all roles
    python scripts/generate_skills.py --batch

    # Generate skills for a specific role
    python scripts/generate_skills.py --role frontend-developer

    # Preview without generating
    python scripts/generate_skills.py --dry-run

    # Specify custom output directory
    python scripts/generate_skills.py --output-dir /path/to/skills
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
DEFAULT_SKILL_DIR = ".claude/skills"
DEFAULT_L14_URL = "http://localhost:8014"
DEFAULT_TIMEOUT = 60  # Longer timeout for generation


class SkillGenerator:
    """
    Generates missing skills from role definitions using L14.
    """

    def __init__(
        self,
        role_directory: str,
        skill_directory: str,
        l14_url: str,
        batch: bool = False,
        role_filter: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the SkillGenerator.

        Args:
            role_directory: Path to directory containing role YAML files
            skill_directory: Path to directory for skill files
            l14_url: Base URL of the L14 Skill Library service
            batch: If True, process all roles
            role_filter: If set, only process this specific role
            dry_run: If True, preview without generating
            verbose: If True, print detailed output
        """
        self.role_directory = Path(role_directory).expanduser().resolve()
        self.skill_directory = Path(skill_directory).expanduser().resolve()
        self.l14_url = l14_url.rstrip("/")
        self.batch = batch
        self.role_filter = role_filter
        self.dry_run = dry_run
        self.verbose = verbose

        # Tracking
        self.roles_processed: List[str] = []
        self.skills_generated: List[Dict[str, Any]] = []
        self.skills_skipped: List[Tuple[str, str]] = []
        self.skills_failed: List[Tuple[str, str]] = []

    def log(self, message: str, force: bool = False) -> None:
        """Print message if verbose mode or force is True."""
        if self.verbose or force:
            print(message)

    def log_progress(self, message: str) -> None:
        """Print progress message (always visible)."""
        print(message)

    def find_role_files(self) -> List[Path]:
        """
        Find role YAML files.

        Returns:
            List of paths to role YAML files
        """
        if not self.role_directory.exists():
            raise FileNotFoundError(f"Role directory not found: {self.role_directory}")

        role_files = []
        for pattern in ["*.yaml", "*.yml"]:
            role_files.extend(self.role_directory.glob(pattern))

        # Apply role filter if specified
        if self.role_filter:
            filter_lower = self.role_filter.lower()
            role_files = [
                f for f in role_files
                if filter_lower in f.stem.lower()
            ]

        return sorted(role_files)

    def find_existing_skills(self) -> Set[str]:
        """
        Find existing skill files.

        Returns:
            Set of existing skill names (without extension)
        """
        if not self.skill_directory.exists():
            return set()

        existing = set()
        for pattern in ["*.md", "*.yaml", "*.yml"]:
            for skill_file in self.skill_directory.glob(pattern):
                existing.add(skill_file.stem.lower())

        return existing

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

    def extract_required_skills(self, role_data: Dict[str, Any]) -> List[str]:
        """
        Extract required skills from role data.

        Args:
            role_data: Role data from YAML

        Returns:
            List of skill names
        """
        skills = []

        # Check core_skills field
        if "core_skills" in role_data:
            skills.extend(role_data["core_skills"])

        # Check skills field (might be more detailed)
        if "skills" in role_data:
            for skill in role_data["skills"]:
                if isinstance(skill, str):
                    skills.append(skill)
                elif isinstance(skill, dict) and "name" in skill:
                    skills.append(skill["name"])

        return list(set(skills))  # Remove duplicates

    def build_generation_request(
        self,
        skill_name: str,
        role_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a skill generation request for L14.

        Args:
            skill_name: Name of the skill to generate
            role_data: Role data for context

        Returns:
            Generation request data
        """
        role_name = role_data.get("name", "Developer")
        role_description = role_data.get(
            "description",
            f"Professional with {skill_name} expertise"
        )

        # Build responsibilities based on skill
        responsibilities = [
            f"Apply {skill_name} practices effectively",
            f"Follow established {skill_name} standards",
            f"Maintain quality in {skill_name} work",
        ]

        # Add role-specific responsibilities if available
        if "responsibilities" in role_data:
            responsibilities.extend(role_data["responsibilities"][:3])

        # Build expertise areas
        expertise = [skill_name]
        if "capabilities" in role_data:
            expertise.extend(role_data["capabilities"][:2])
        if "keywords" in role_data:
            expertise.extend(role_data["keywords"][:3])

        return {
            "role_title": f"{role_name} - {skill_name.replace('-', ' ').title()}",
            "role_description": f"{role_description}. Specialized in {skill_name}.",
            "responsibilities": responsibilities[:5],
            "expertise_areas": list(set(expertise))[:5],
            "priority": "medium",
            "category": "technical",
            "include_examples": True,
            "include_procedures": True,
            "max_token_budget": 2000,
        }

    def generate_skill_via_api(
        self,
        skill_name: str,
        request_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a skill using the L14 API.

        Args:
            skill_name: Name of the skill
            request_data: Generation request data

        Returns:
            Generated skill data or None if failed
        """
        try:
            response = requests.post(
                f"{self.l14_url}/skills/generate",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                return result
            else:
                error = result.get("error", "Unknown error")
                self.skills_failed.append((skill_name, f"Generation failed: {error}"))
                return None

        except requests.Timeout:
            self.skills_failed.append((skill_name, "Request timed out"))
            return None
        except requests.RequestException as e:
            self.skills_failed.append((skill_name, f"API error: {e}"))
            return None

    def validate_skill(self, skill_data: Dict[str, Any]) -> bool:
        """
        Validate a generated skill.

        Args:
            skill_data: Generated skill data

        Returns:
            True if valid, False otherwise
        """
        # Check for required fields
        if not skill_data:
            return False

        # Check validation result if present
        validation = skill_data.get("validation_result", {})
        if validation and not validation.get("is_valid", True):
            return False

        # Check for skill content
        skill = skill_data.get("skill", {})
        if not skill:
            return False

        return True

    def save_skill_file(
        self,
        skill_name: str,
        skill_data: Dict[str, Any],
    ) -> Path:
        """
        Save a generated skill to a file.

        Args:
            skill_name: Name of the skill
            skill_data: Generated skill data

        Returns:
            Path to the saved file
        """
        # Ensure output directory exists
        self.skill_directory.mkdir(parents=True, exist_ok=True)

        # Use raw content if available, otherwise generate from skill data
        if "raw_content" in skill_data and skill_data["raw_content"]:
            content = skill_data["raw_content"]
            file_ext = ".yaml"
        else:
            # Generate markdown content
            skill = skill_data.get("skill", {})
            definition = skill.get("definition", {})
            role = definition.get("role", {})
            responsibilities = definition.get("responsibilities", {})

            lines = [
                f"# {skill_name.replace('-', ' ').title()}",
                "",
            ]

            # Add description
            if role.get("description"):
                lines.append("## Description")
                lines.append("")
                lines.append(role["description"])
                lines.append("")

            # Add expertise areas
            if role.get("expertise_areas"):
                lines.append("## Expertise Areas")
                lines.append("")
                for area in role["expertise_areas"]:
                    lines.append(f"- {area}")
                lines.append("")

            # Add responsibilities
            if responsibilities.get("primary"):
                lines.append("## Primary Responsibilities")
                lines.append("")
                for resp in responsibilities["primary"]:
                    lines.append(f"1. {resp}")
                lines.append("")

            if responsibilities.get("secondary"):
                lines.append("## Secondary Responsibilities")
                lines.append("")
                for resp in responsibilities["secondary"]:
                    lines.append(f"- {resp}")
                lines.append("")

            # Add procedures if available
            procedures = definition.get("procedures", [])
            if procedures:
                lines.append("## Procedures")
                lines.append("")
                for proc in procedures:
                    if isinstance(proc, dict):
                        lines.append(f"### {proc.get('name', 'Procedure')}")
                        if proc.get("description"):
                            lines.append(proc["description"])
                        if proc.get("steps"):
                            for i, step in enumerate(proc["steps"], 1):
                                lines.append(f"{i}. {step}")
                    lines.append("")

            content = "\n".join(lines)
            file_ext = ".md"

        # Write file
        file_path = self.skill_directory / f"{skill_name}{file_ext}"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def generate_skill_fallback(self, skill_name: str) -> Dict[str, Any]:
        """
        Generate a basic skill template when L14 is unavailable.

        Args:
            skill_name: Name of the skill

        Returns:
            Basic skill data
        """
        title = skill_name.replace("-", " ").title()
        return {
            "success": True,
            "skill": {
                "name": skill_name,
                "definition": {
                    "role": {
                        "title": title,
                        "description": f"Skill definition for {title}",
                        "expertise_areas": [skill_name],
                    },
                    "responsibilities": {
                        "primary": [
                            f"Apply {title.lower()} best practices",
                            f"Follow {title.lower()} standards",
                        ],
                        "secondary": [
                            f"Stay updated on {title.lower()} developments",
                        ],
                    },
                    "procedures": [],
                },
            },
        }

    def process_skill(
        self,
        skill_name: str,
        role_data: Dict[str, Any],
        existing_skills: Set[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single skill.

        Args:
            skill_name: Name of the skill
            role_data: Parent role data
            existing_skills: Set of existing skill names

        Returns:
            Generated skill data or None
        """
        self.log(f"    Processing skill: {skill_name}")

        # Check if skill already exists
        if skill_name.lower() in existing_skills:
            self.skills_skipped.append((skill_name, "Already exists"))
            self.log(f"      Skipped: Already exists")
            return None

        if self.dry_run:
            self.log(f"      [DRY RUN] Would generate: {skill_name}")
            return {"skill_name": skill_name, "dry_run": True}

        # Build generation request
        request_data = self.build_generation_request(skill_name, role_data)
        self.log(f"      Generating via L14...")

        # Try L14 API first
        skill_data = self.generate_skill_via_api(skill_name, request_data)

        # Fall back to template if API unavailable
        if skill_data is None and len(self.skills_failed) > 0:
            last_error = self.skills_failed[-1][1]
            if "Connection" in last_error or "API error" in last_error:
                self.log(f"      L14 unavailable, using fallback template")
                # Remove from failed list - we're handling it
                self.skills_failed.pop()
                skill_data = self.generate_skill_fallback(skill_name)

        if skill_data is None:
            return None

        # Validate
        if not self.validate_skill(skill_data):
            self.skills_failed.append((skill_name, "Validation failed"))
            self.log(f"      Error: Validation failed", force=True)
            return None

        # Save to file
        file_path = self.save_skill_file(skill_name, skill_data)
        self.log(f"      Saved: {file_path}")

        return skill_data

    def process_role(
        self,
        file_path: Path,
        existing_skills: Set[str],
    ) -> List[Dict[str, Any]]:
        """
        Process skills for a single role.

        Args:
            file_path: Path to the role YAML file
            existing_skills: Set of existing skill names

        Returns:
            List of generated skills
        """
        self.log(f"  Processing role: {file_path.name}")

        try:
            role_data = self.parse_role_file(file_path)
            role_name = role_data.get("name", file_path.stem)
            self.roles_processed.append(role_name)
        except (yaml.YAMLError, ValueError) as e:
            self.log(f"    Error parsing role: {e}", force=True)
            return []

        # Get required skills
        required_skills = self.extract_required_skills(role_data)
        if not required_skills:
            self.log(f"    No skills defined for this role")
            return []

        self.log(f"    Required skills: {', '.join(required_skills)}")

        # Process each skill
        generated = []
        for skill_name in required_skills:
            result = self.process_skill(skill_name, role_data, existing_skills)
            if result:
                generated.append(result)
                existing_skills.add(skill_name.lower())  # Update for next iterations

        return generated

    def run(self) -> None:
        """Run the skill generation process."""
        self.log_progress(f"\n{'='*60}")
        self.log_progress("Skill Generator - L14 Skill Library")
        self.log_progress(f"{'='*60}")
        self.log_progress(f"Role directory: {self.role_directory}")
        self.log_progress(f"Skill directory: {self.skill_directory}")
        self.log_progress(f"L14 URL: {self.l14_url}")
        self.log_progress(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        if self.role_filter:
            self.log_progress(f"Role filter: {self.role_filter}")
        self.log_progress(f"{'='*60}\n")

        # Find role files
        try:
            role_files = self.find_role_files()
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if not role_files:
            self.log_progress("No role files found.")
            if self.role_filter:
                self.log_progress(f"  (No roles matching filter: {self.role_filter})")
            return

        # Check for single role vs batch mode
        if not self.batch and not self.role_filter and len(role_files) > 1:
            self.log_progress(
                f"Found {len(role_files)} roles. Use --batch to process all, "
                f"or --role <name> for a specific role."
            )
            self.log_progress("\nAvailable roles:")
            for f in role_files:
                self.log_progress(f"  - {f.stem}")
            return

        self.log_progress(f"Found {len(role_files)} role file(s)\n")

        # Find existing skills
        existing_skills = self.find_existing_skills()
        self.log_progress(f"Found {len(existing_skills)} existing skill(s)\n")

        # Process each role
        for file_path in role_files:
            generated = self.process_role(file_path, existing_skills)
            self.skills_generated.extend(generated)

        self.print_summary()

    def print_summary(self) -> None:
        """Print summary of generated skills."""
        self.log_progress(f"\n{'='*60}")
        self.log_progress("Summary")
        self.log_progress(f"{'='*60}")

        self.log_progress(f"\nRoles processed: {len(self.roles_processed)}")
        for role in self.roles_processed:
            self.log_progress(f"  - {role}")

        self.log_progress(f"\nResults:")
        self.log_progress(f"  Generated: {len(self.skills_generated)}")
        self.log_progress(f"  Skipped:   {len(self.skills_skipped)}")
        self.log_progress(f"  Failed:    {len(self.skills_failed)}")

        if self.skills_generated:
            self.log_progress("\nGenerated skills:")
            for skill in self.skills_generated:
                name = skill.get("skill_name") or skill.get("skill", {}).get("name", "unknown")
                self.log_progress(f"  - {name}")

        if self.skills_skipped:
            self.log_progress("\nSkipped skills:")
            for name, reason in self.skills_skipped:
                self.log_progress(f"  - {name}: {reason}")

        if self.skills_failed:
            self.log_progress("\nFailed skills:")
            for name, reason in self.skills_failed:
                self.log_progress(f"  - {name}: {reason}")

        if self.dry_run:
            self.log_progress("\n[DRY RUN] No files were created.")


def find_default_directory(subpath: str) -> Path:
    """
    Find a default directory.

    Looks for the subpath in the current directory or project root.
    """
    cwd = Path.cwd()
    target_dir = cwd / subpath
    if target_dir.exists():
        return target_dir

    # Try parent directories
    for parent in cwd.parents:
        target_dir = parent / subpath
        if target_dir.exists():
            return target_dir
        # Stop at git root
        if (parent / ".git").exists():
            break

    return cwd / subpath


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate missing skills for roles using L14 Skill Library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --batch                 Generate skills for all roles
  %(prog)s --role developer        Generate skills for specific role
  %(prog)s --dry-run               Preview without generating
  %(prog)s --output-dir ./skills   Custom output directory
  %(prog)s -v                      Verbose output
        """,
    )

    parser.add_argument(
        "--role-dir",
        type=str,
        default=None,
        help=f"Directory containing role YAML files (default: {DEFAULT_ROLE_DIR})",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=None,
        help=f"Output directory for generated skills (default: {DEFAULT_SKILL_DIR})",
    )

    parser.add_argument(
        "--url",
        type=str,
        default=os.environ.get("L14_URL", DEFAULT_L14_URL),
        help=f"L14 Skill Library service URL (default: {DEFAULT_L14_URL})",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all roles (batch mode)",
    )

    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="Generate skills for a specific role only",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview skills to generate without creating them",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )

    args = parser.parse_args()

    # Determine directories
    role_dir = args.role_dir or str(find_default_directory(DEFAULT_ROLE_DIR))
    skill_dir = args.output_dir or str(find_default_directory(DEFAULT_SKILL_DIR))

    # Create generator and run
    generator = SkillGenerator(
        role_directory=role_dir,
        skill_directory=skill_dir,
        l14_url=args.url,
        batch=args.batch,
        role_filter=args.role,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    try:
        generator.run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 1

    # Return non-zero if there were failures
    if generator.skills_failed:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
