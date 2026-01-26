#!/usr/bin/env python3
"""
Service Catalog Validator
Path: platform/tools/catalog_validator.py

Usage:
    python catalog_validator.py                   # Validate
    python catalog_validator.py --fix             # Auto-fix
    python catalog_validator.py --fix --dry-run   # Preview fixes
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class DiscoveredService:
    name: str
    path: Path
    layer: str
    methods: List[str]
    docstring: Optional[str]


@dataclass
class CatalogValidationResult:
    valid: bool
    registered_services: int
    discovered_services: int
    missing_entries: List[str]
    orphaned_entries: List[str]


class CatalogValidator:
    SERVICE_CLASS_SUFFIXES = ('Service', 'Store', 'Manager', 'Engine',
                              'Handler', 'Adapter', 'Cache', 'Monitor',
                              'Resolver', 'Validator', 'Estimator', 'Injector')

    EXCLUDE_PATTERNS = [r'test', r'__pycache__', r'\.pyc$', r'base_', r'abstract']

    def __init__(self, platform_root: Path):
        self.root = platform_root
        self.catalog_path = platform_root / "src/L12_nl_interface/data/service_catalog.json"

    def _extract_layer(self, path: Path) -> str:
        for part in path.parts:
            if part.startswith('L') and '_' in part:
                return part.split('_')[0]
        return "Unknown"

    def _is_excluded(self, path: Path) -> bool:
        path_str = str(path).lower()
        return any(re.search(p, path_str) for p in self.EXCLUDE_PATTERNS)

    def _parse_service_file(self, path: Path) -> List[DiscoveredService]:
        services = []
        if self._is_excluded(path):
            return services

        try:
            content = path.read_text()
            tree = ast.parse(content)
        except Exception:
            return services

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.endswith(self.SERVICE_CLASS_SUFFIXES):
                    if any(base.id == 'ABC' for base in node.bases
                           if isinstance(base, ast.Name)):
                        continue

                    methods = [
                        item.name for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not item.name.startswith('_')
                    ]

                    services.append(DiscoveredService(
                        name=node.name,
                        path=path,
                        layer=self._extract_layer(path),
                        methods=methods,
                        docstring=ast.get_docstring(node)
                    ))

        return services

    def discover_services(self) -> List[DiscoveredService]:
        services = []
        src_path = self.root / "src"

        if not src_path.exists():
            return services

        for py_file in src_path.rglob("*.py"):
            services.extend(self._parse_service_file(py_file))

        return services

    def load_catalog(self) -> Dict:
        if not self.catalog_path.exists():
            return {}
        with open(self.catalog_path) as f:
            return json.load(f)

    def _get_catalog_names(self, catalog: Dict) -> Set[str]:
        """Extract service names from catalog, handling both schema formats."""
        # Format 1: {"services": [{"name": "X"}, ...]}
        if "services" in catalog and isinstance(catalog["services"], list):
            return {s.get("name") or s.get("service_name") for s in catalog["services"]}
        # Format 2: {"ServiceName": {"service_name": "X", ...}, ...}
        return set(catalog.keys())

    def validate(self) -> CatalogValidationResult:
        discovered = self.discover_services()
        catalog = self.load_catalog()

        discovered_names = {s.name for s in discovered}
        catalog_names = self._get_catalog_names(catalog)

        missing = discovered_names - catalog_names
        orphaned = catalog_names - discovered_names

        return CatalogValidationResult(
            valid=len(missing) == 0,
            registered_services=len(catalog_names),
            discovered_services=len(discovered_names),
            missing_entries=sorted(list(missing)),
            orphaned_entries=sorted(list(orphaned))
        )

    def generate_entry(self, service: DiscoveredService) -> Dict:
        category = "general"
        name_lower = service.name.lower()
        if 'cache' in name_lower: category = "caching"
        elif 'monitor' in name_lower: category = "monitoring"
        elif 'validator' in name_lower: category = "validation"
        elif 'store' in name_lower: category = "persistence"

        return {
            "name": service.name,
            "layer": service.layer,
            "category": category,
            "description": service.docstring or f"{service.name} service",
            "methods": service.methods[:10],
        }

    def fix_catalog(self, dry_run: bool = True) -> List[Dict]:
        discovered = self.discover_services()
        catalog = self.load_catalog()
        catalog_names = self._get_catalog_names(catalog)

        new_entries = []
        for service in discovered:
            if service.name not in catalog_names:
                new_entries.append(self.generate_entry(service))

        if not dry_run and new_entries:
            # Use Format 2: {"ServiceName": {...}, ...} to match existing catalog
            for entry in new_entries:
                catalog[entry["name"]] = {
                    "service_name": entry["name"],
                    "layer": entry["layer"],
                    "module_path": f"src.{entry['layer']}_*.services.*",
                    "class_name": entry["name"],
                    "description": entry["description"],
                    "keywords": [],
                    "dependencies": [],
                    "requires_async_init": False,
                    "methods": []
                }
            with open(self.catalog_path, 'w') as f:
                json.dump(catalog, f, indent=2)

        return new_entries


def main():
    parser = argparse.ArgumentParser(description="Validate service catalog")
    parser.add_argument("--fix", action="store_true", help="Auto-fix missing entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview fixes")
    parser.add_argument("--root", type=Path, default=Path.cwd() / "platform")
    args = parser.parse_args()

    validator = CatalogValidator(args.root)

    if args.fix:
        entries = validator.fix_catalog(dry_run=args.dry_run)
        action = "Would add" if args.dry_run else "Added"
        print(f"{action} {len(entries)} entries:")
        for e in entries:
            print(f"  - {e['name']} ({e['layer']})")
        return 0

    result = validator.validate()
    print(f"Discovered: {result.discovered_services}")
    print(f"Registered: {result.registered_services}")

    if result.missing_entries:
        print(f"\nMissing ({len(result.missing_entries)}):")
        for name in result.missing_entries:
            print(f"  - {name}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
