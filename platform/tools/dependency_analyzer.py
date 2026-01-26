#!/usr/bin/env python3
"""
Dependency Chain Analyzer
Path: platform/tools/dependency_analyzer.py

Usage:
    python dependency_analyzer.py           # Analyze and show issues
    python dependency_analyzer.py --json    # Output JSON format
"""

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class DependencyIssue:
    issue_type: str
    severity: str
    source: str
    target: str
    message: str
    fix_suggestion: str


class DependencyAnalyzer:
    LAYER_ORDER = ['L01', 'L02', 'L03', 'L04', 'L05', 'L06', 'L07',
                   'L09', 'L10', 'L11', 'L12', 'L13', 'L14']

    def __init__(self, platform_root: Path):
        self.root = platform_root
        self._graph: Dict[str, Set[str]] = defaultdict(set)

    def _layer_index(self, layer: str) -> int:
        try:
            return self.LAYER_ORDER.index(layer)
        except ValueError:
            return -1

    def _extract_layer(self, path: Path) -> str:
        for part in path.parts:
            if part.startswith('L') and '_' in part:
                return part.split('_')[0]
        return ""

    def _parse_imports(self, path: Path) -> List[str]:
        imports = []
        try:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
        except Exception:
            pass
        return imports

    def analyze(self) -> Dict:
        issues = []
        src_path = self.root / "src"

        for py_file in src_path.rglob("*.py"):
            if '__pycache__' in str(py_file) or 'test' in str(py_file).lower():
                continue

            file_layer = self._extract_layer(py_file)
            if not file_layer:
                continue

            for imp in self._parse_imports(py_file):
                for layer in self.LAYER_ORDER:
                    if f'{layer}_' in imp:
                        self._graph[file_layer].add(layer)

                        if self._layer_index(file_layer) < self._layer_index(layer):
                            issues.append(DependencyIssue(
                                issue_type="layer_violation",
                                severity="warning",
                                source=str(py_file.relative_to(self.root)),
                                target=layer,
                                message=f"{file_layer} imports from {layer}",
                                fix_suggestion=f"Invert: {layer} should import from {file_layer}"
                            ))

        return {
            "issues": [asdict(i) for i in issues],
            "dependency_graph": {k: sorted(v) for k, v in self._graph.items()},
            "issue_count": len(issues)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze import dependencies and detect layer violations"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--root", type=Path, default=Path.cwd() / "platform",
                        help="Platform root directory")
    args = parser.parse_args()

    result = DependencyAnalyzer(args.root).analyze()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Issues found: {result['issue_count']}")
        if result['issues']:
            print("\nLayer violations:")
            for issue in result['issues']:
                print(f"  [{issue['severity']}] {issue['message']}")
                print(f"           Source: {issue['source']}")
                print(f"           Fix: {issue['fix_suggestion']}")

        if result['dependency_graph']:
            print("\nDependency graph:")
            for layer, deps in sorted(result['dependency_graph'].items()):
                print(f"  {layer} -> {', '.join(deps)}")

    return 0 if result['issue_count'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
