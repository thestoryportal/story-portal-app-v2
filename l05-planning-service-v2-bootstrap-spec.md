# L05 Planning Service V2 - Bootstrap Implementation Specification

**Version:** 2.0.0  
**Created:** 2025-01-25  
**Status:** Ready for Implementation  
**Bootstrap Protocol:** Manual Validation-First Execution

---

## 1. Bootstrap Strategy

### 1.1 The Chicken-and-Egg Problem

The L05 Planning Service automates validation-first implementation with checkpoint/rollback. However, implementing L05 itself cannot use L05 (it doesn't work yet). This specification solves the bootstrap problem by having Claude CLI **manually execute the same protocol** that L05 will later automate.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BOOTSTRAP EQUIVALENCE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   AUTOMATED L05 PIPELINE              MANUAL BOOTSTRAP PROTOCOL             │
│   ══════════════════════              ═════════════════════════             │
│                                                                             │
│   SpecDecomposer                  ──▶ This spec (Section 4: Atomic Units)   │
│   CheckpointManager.begin_unit() ──▶ git add -A && git commit              │
│   Implementation                  ──▶ Claude writes code                    │
│   UnitValidator                   ──▶ Run acceptance criteria checks        │
│   RegressionGuardian              ──▶ pytest for affected layer             │
│   IntegrationSentinel             ──▶ catalog_validator + import check      │
│   RollbackCoordinator             ──▶ git checkout on failure               │
│   EventBus.publish()              ──▶ Echo status to conversation           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Protocol Rules

Claude CLI MUST follow this protocol for every atomic unit:

| Step | Automated (Future) | Manual (Bootstrap) | Failure Action |
|------|-------------------|-------------------|----------------|
| 1. Checkpoint | `SagaOrchestrator.begin()` | `git add -A && git commit -m "checkpoint: unit X.Y"` | — |
| 2. Implement | Agent execution | Claude writes code | — |
| 3. Validate | `UnitValidator.validate()` | Run each acceptance criterion command | GOTO Step 6 |
| 4. Regression | `RegressionGuardian.check()` | `pytest platform/tests/L05_planning/ -x` | GOTO Step 6 |
| 5. Integration | `IntegrationSentinel.validate()` | Import check + catalog check | GOTO Step 6 |
| 6. Rollback | `RollbackCoordinator.rollback()` | `git checkout -- platform/src/L05_planning/` | Retry or escalate |
| 7. Commit | `CheckpointManager.commit()` | `git add -A && git commit -m "complete: unit X.Y"` | — |

### 1.3 Critical Constraint

**Claude MUST NOT proceed to Unit N+1 until Unit N passes all validation steps.** This mirrors the automated pipeline's blocking behavior.

---

## 2. Problem Statement

### 2.1 Root Cause

Gate 2 shows `"Plan has only 0 steps"` because `CLIPlanAdapter.parse_plan_markdown()` expects:

```markdown
1. **Step Title**
   Description
   Files: file.py
   Depends: step-1
```

But Claude outputs:

```markdown
# PART A: SECTION NAME
### Step 1: Title
Description with **Focus:** bullets and code blocks
```

### 2.2 Evidence

```
[2026-01-24T18:14:30.883Z] L05 adapter completed
{
  "code": 0,           // Python runs successfully
  "stdoutLength": 980,
  "stderrLength": 0
}
"Plan has only 0 steps - using traditional execution."
```

### 2.3 Fix Scope

| Component | Action | Priority |
|-----------|--------|----------|
| Multi-format parser | Create new | P0 |
| 6 missing catalog entries | Add | P0 |
| Validation agents | Create new | P0 |
| Checkpoint system | Create new | P0 |
| Platform integration | Create new | P1 |
| Developer tools | Create new | P1 |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              L05 PLANNING SERVICE V2                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         PARSER SUBSYSTEM                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │FormatDetector│─▶│Format-Specific│─▶│   MultiFormatParser      │  │   │
│  │  │              │  │Parsers (5)   │  │   (unified interface)    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VALIDATION SUBSYSTEM                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │SpecDecomposer│─▶│UnitValidator │─▶│Regression   │              │   │
│  │  │              │  │  (L06)       │  │Guardian (L03)│              │   │
│  │  └──────────────┘  └──────────────┘  └──────┬───────┘              │   │
│  │                                             │                       │   │
│  │                    ┌──────────────┐  ┌──────▼───────┐              │   │
│  │                    │  Rollback    │◀─│ Integration  │              │   │
│  │                    │  Coordinator │  │ Sentinel     │              │   │
│  │                    │    (L11)     │  │   (L11/L12)  │              │   │
│  │                    └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      CHECKPOINT SUBSYSTEM                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │Checkpoint    │─▶│  GitState    │  │  FileState   │              │   │
│  │  │Manager       │  │  Capture     │  │  Capture     │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  PLATFORM DEPENDENCIES (use, don't recreate):                               │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                               │
│  │L01 Data│ │L04 Cache│ │L06 Eval│ │L11 Infra│                              │
│  └────────┘ └────────┘ └────────┘ └────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 File Structure

```
platform/src/L05_planning/
├── parsers/
│   ├── __init__.py
│   ├── format_detector.py           # Detects 6 format types
│   ├── base_parser.py               # Abstract base class
│   ├── numbered_list_parser.py      # Format: 1. **Title**
│   ├── phase_based_parser.py        # Format: ## Phase N:
│   ├── part_based_parser.py         # Format: # PART A:
│   ├── table_based_parser.py        # Format: | Step | ... |
│   └── multi_format_parser.py       # Unified entry point
├── agents/
│   ├── __init__.py
│   ├── spec_decomposer.py
│   ├── unit_validator.py
│   ├── regression_guardian.py
│   ├── integration_sentinel.py
│   └── rollback_coordinator.py
├── checkpoint/
│   ├── __init__.py
│   ├── manager.py
│   ├── git_state.py
│   └── file_state.py
├── integration/
│   ├── __init__.py
│   ├── l01_data.py
│   ├── l04_cache.py
│   ├── l06_eval.py
│   └── l11_infra.py
└── adapters/
    └── cli_plan_adapter.py          # MODIFY: use MultiFormatParser
```

---

## 4. Atomic Implementation Units

### 4.1 Unit Index

| ID | Name | Files | Est. Min | Dependencies |
|----|------|-------|----------|--------------|
| 1.1 | Format Detector | `parsers/format_detector.py` | 20 | — |
| 1.2 | Base Parser | `parsers/base_parser.py` | 10 | — |
| 1.3 | Numbered List Parser | `parsers/numbered_list_parser.py` | 15 | 1.2 |
| 1.4 | Phase-Based Parser | `parsers/phase_based_parser.py` | 15 | 1.2 |
| 1.5 | Part-Based Parser | `parsers/part_based_parser.py` | 15 | 1.2 |
| 1.6 | Table-Based Parser | `parsers/table_based_parser.py` | 20 | 1.2 |
| 1.7 | Multi-Format Parser | `parsers/multi_format_parser.py` | 15 | 1.1-1.6 |
| 1.8 | CLI Adapter Integration | `adapters/cli_plan_adapter.py` | 15 | 1.7 |
| 2.1 | Catalog Validator Tool | `tools/catalog_validator.py` | 25 | — |
| 2.2 | Add 6 Missing Entries | `L12.../service_catalog.json` | 10 | 2.1 |
| 2.3 | Dependency Analyzer Tool | `tools/dependency_analyzer.py` | 25 | — |
| 3.1 | Spec Decomposer Agent | `agents/spec_decomposer.py` | 30 | 1.7 |
| 3.2 | Unit Validator Agent | `agents/unit_validator.py` | 25 | 3.1 |
| 3.3 | Regression Guardian Agent | `agents/regression_guardian.py` | 25 | 3.1 |
| 3.4 | Integration Sentinel Agent | `agents/integration_sentinel.py` | 25 | 2.1, 3.1 |
| 3.5 | Rollback Coordinator Agent | `agents/rollback_coordinator.py` | 20 | 3.1 |
| 4.1 | Checkpoint Manager | `checkpoint/manager.py` | 25 | 3.5 |
| 4.2 | Git State Capture | `checkpoint/git_state.py` | 15 | 4.1 |
| 4.3 | File State Capture | `checkpoint/file_state.py` | 15 | 4.1 |
| 5.1 | L01 Integration | `integration/l01_data.py` | 20 | 4.1 |
| 5.2 | L04 Integration | `integration/l04_cache.py` | 15 | — |
| 5.3 | L06 Integration | `integration/l06_eval.py` | 15 | 3.2 |
| 5.4 | L11 Integration | `integration/l11_infra.py` | 20 | 4.1 |

**Total: 23 units, ~7-8 hours with AI-assisted implementation**

### 4.2 Unit Specifications

---

#### Unit 1.1: Format Detector

**Path:** `platform/src/L05_planning/parsers/format_detector.py`

**Description:** Analyzes plan markdown and identifies which of 6 formats Claude used.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/format_detector.py` |
| 2 | Detects NUMBERED_LIST format | `python -c "from platform.src.L05_planning.parsers.format_detector import FormatDetector, FormatType; r=FormatDetector().detect('1. **Step**\n   Desc'); assert r.format_type==FormatType.NUMBERED_LIST"` |
| 3 | Detects PART_BASED format | `python -c "from platform.src.L05_planning.parsers.format_detector import FormatDetector, FormatType; r=FormatDetector().detect('# PART A:\n### Step 1:'); assert r.format_type==FormatType.PART_BASED"` |
| 4 | Returns confidence 0.0-1.0 | `python -c "from platform.src.L05_planning.parsers.format_detector import FormatDetector; r=FormatDetector().detect('test'); assert 0<=r.confidence<=1"` |

**Compensation:** `rm platform/src/L05_planning/parsers/format_detector.py`

**Implementation:**

```python
"""
Format Detector - Identifies Claude plan output format
Path: platform/src/L05_planning/parsers/format_detector.py
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class FormatType(Enum):
    NUMBERED_LIST = "numbered_list"
    PHASE_BASED = "phase_based"
    PART_BASED = "part_based"
    SUBPLAN = "subplan"
    TABLE_BASED = "table_based"
    HIERARCHICAL = "hierarchical"
    UNKNOWN = "unknown"


@dataclass
class FormatDetectionResult:
    format_type: FormatType
    confidence: float
    indicators: List[str]
    fallback_format: Optional[FormatType] = None


class FormatDetector:
    """Detects the format type of Claude plan markdown."""
    
    PATTERNS = {
        FormatType.NUMBERED_LIST: [
            (r'^\d+\.\s+\*\*[^*]+\*\*', 0.4),
            (r'^Files:\s*.+', 0.2),
            (r'^Depends:\s*.+', 0.2),
        ],
        FormatType.PHASE_BASED: [
            (r'^##\s+Phase\s+\d+:', 0.5),
            (r'^###\s+Step\s+\d+\.\d+:', 0.3),
        ],
        FormatType.PART_BASED: [
            (r'^#\s+PART\s+[A-Z]+:', 0.5),
            (r'^###\s+Step\s+\d+:', 0.3),
        ],
        FormatType.SUBPLAN: [
            (r'^##\s+Implementation\s+Phases', 0.4),
            (r'^###\s+Phase\s+\d+:', 0.3),
            (r'\*\*Focus:\*\*', 0.2),
        ],
        FormatType.TABLE_BASED: [
            (r'\|\s*Step\s*\|', 0.5),
            (r'\|[-:]+\|', 0.3),
        ],
        FormatType.HIERARCHICAL: [
            (r'^###\s+Step\s+\d+(\.\d+)+:', 0.6),
        ],
    }
    
    def detect(self, markdown: str) -> FormatDetectionResult:
        """Analyzes markdown and returns detected format with confidence."""
        scores = {fmt: 0.0 for fmt in FormatType if fmt != FormatType.UNKNOWN}
        indicators = {fmt: [] for fmt in FormatType}
        
        lines = markdown.split('\n')
        
        for fmt, patterns in self.PATTERNS.items():
            for pattern, weight in patterns:
                for line in lines:
                    if re.match(pattern, line, re.MULTILINE):
                        scores[fmt] += weight
                        indicators[fmt].append(f"Matched: {pattern[:30]}...")
                        break
        
        max_score = max(scores.values()) if scores.values() else 0
        if max_score > 0:
            for fmt in scores:
                scores[fmt] = min(scores[fmt] / max(max_score, 1.0), 1.0)
        
        best_fmt = max(scores, key=scores.get)
        best_score = scores[best_fmt]
        
        fallback = None
        if best_score < 0.7:
            sorted_fmts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_fmts) > 1 and sorted_fmts[1][1] > 0:
                fallback = sorted_fmts[1][0]
        
        if best_score < 0.3:
            best_fmt = FormatType.UNKNOWN
        
        return FormatDetectionResult(
            format_type=best_fmt,
            confidence=best_score,
            indicators=indicators.get(best_fmt, []),
            fallback_format=fallback
        )
```

---

#### Unit 1.2: Base Parser

**Path:** `platform/src/L05_planning/parsers/base_parser.py`

**Description:** Abstract base class and shared data structures for all format parsers.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/base_parser.py` |
| 2 | PlanStep dataclass importable | `python -c "from platform.src.L05_planning.parsers.base_parser import PlanStep; s=PlanStep(id='1',title='T',description='D'); assert s.id=='1'"` |
| 3 | ParsedPlan dataclass importable | `python -c "from platform.src.L05_planning.parsers.base_parser import ParsedPlan; p=ParsedPlan(plan_id='1',title='T',steps=[]); assert p.plan_id=='1'"` |
| 4 | BaseParser abstract class defined | `python -c "from platform.src.L05_planning.parsers.base_parser import BaseParser; import inspect; assert inspect.isabstract(BaseParser)"` |

**Compensation:** `rm platform/src/L05_planning/parsers/base_parser.py`

**Implementation:**

```python
"""
Base Parser - Abstract base and shared structures
Path: platform/src/L05_planning/parsers/base_parser.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .format_detector import FormatType


@dataclass
class PlanStep:
    id: str
    title: str
    description: str
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    phase: Optional[str] = None
    estimated_complexity: str = "medium"
    acceptance_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedPlan:
    plan_id: str
    title: str
    steps: List[PlanStep]
    format_type: FormatType = FormatType.UNKNOWN
    overview: str = ""
    phases: List[str] = field(default_factory=list)
    total_estimated_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for format-specific parsers."""
    
    @abstractmethod
    def can_parse(self, markdown: str) -> bool:
        """Returns True if this parser can handle the given markdown."""
        pass
    
    @abstractmethod
    def parse(self, markdown: str) -> ParsedPlan:
        """Parses markdown into a ParsedPlan."""
        pass
    
    def _generate_step_id(self, index: int, phase: Optional[str] = None) -> str:
        """Generates a unique step ID."""
        if phase:
            return f"{phase}-{index}"
        return f"step-{index}"
    
    def _extract_title(self, markdown: str) -> str:
        """Extracts plan title from first heading."""
        import re
        match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        return match.group(1).strip() if match else "Untitled Plan"
    
    def _generate_acceptance_criteria(self, step: PlanStep) -> List[str]:
        """Generates default acceptance criteria if none provided."""
        criteria = []
        
        if step.files:
            for f in step.files[:3]:
                criteria.append(f"File {f} exists and passes linting")
        
        if "test" in step.description.lower():
            criteria.append("All related tests pass")
        
        if not criteria:
            criteria.append("Implementation matches step description")
        
        return criteria
```

---

#### Unit 1.3: Numbered List Parser

**Path:** `platform/src/L05_planning/parsers/numbered_list_parser.py`

**Description:** Parses plans with `1. **Title**` format.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/numbered_list_parser.py` |
| 2 | Extracts steps from numbered list | `python -c "from platform.src.L05_planning.parsers.numbered_list_parser import NumberedListParser; p=NumberedListParser().parse('# Plan\n1. **Step One**\n   Desc\n2. **Step Two**\n   More'); assert len(p.steps)==2"` |
| 3 | Extracts Files metadata | `python -c "from platform.src.L05_planning.parsers.numbered_list_parser import NumberedListParser; p=NumberedListParser().parse('# P\n1. **S**\n   D\n   Files: a.py, b.py'); assert 'a.py' in p.steps[0].files"` |
| 4 | Extracts Depends metadata | `python -c "from platform.src.L05_planning.parsers.numbered_list_parser import NumberedListParser; p=NumberedListParser().parse('# P\n1. **A**\n   D\n2. **B**\n   D\n   Depends: step-1'); assert 'step-1' in p.steps[1].dependencies"` |

**Compensation:** `rm platform/src/L05_planning/parsers/numbered_list_parser.py`

**Implementation:**

```python
"""
Numbered List Parser - Parses 1. **Title** format
Path: platform/src/L05_planning/parsers/numbered_list_parser.py
"""

import re
from typing import List
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class NumberedListParser(BaseParser):
    """Parses plans with numbered list format: 1. **Step Title**"""
    
    STEP_PATTERN = re.compile(r'^(\d+)\.\s+\*\*([^*]+)\*\*', re.MULTILINE)
    FILES_PATTERN = re.compile(r'^Files:\s*(.+)$', re.MULTILINE)
    DEPENDS_PATTERN = re.compile(r'^Depends:\s*(.+)$', re.MULTILINE)
    
    def can_parse(self, markdown: str) -> bool:
        return bool(self.STEP_PATTERN.search(markdown))
    
    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        steps = self._extract_steps(markdown)
        
        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            format_type=FormatType.NUMBERED_LIST
        )
    
    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        steps = []
        matches = list(self.STEP_PATTERN.finditer(markdown))
        
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            content = markdown[start:end].strip()
            
            step_num = match.group(1)
            step_title = match.group(2).strip()
            
            description, files, depends = self._parse_content(content)
            
            step = PlanStep(
                id=f"step-{step_num}",
                title=step_title,
                description=description,
                files=files,
                dependencies=depends
            )
            
            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)
            
            steps.append(step)
        
        return steps
    
    def _parse_content(self, content: str):
        files = []
        depends = []
        
        files_match = self.FILES_PATTERN.search(content)
        if files_match:
            files = [f.strip() for f in files_match.group(1).split(',')]
            content = self.FILES_PATTERN.sub('', content)
        
        depends_match = self.DEPENDS_PATTERN.search(content)
        if depends_match:
            depends = [d.strip() for d in depends_match.group(1).split(',')]
            content = self.DEPENDS_PATTERN.sub('', content)
        
        description = content.strip()
        
        return description, files, depends
```

---

#### Unit 1.4: Phase-Based Parser

**Path:** `platform/src/L05_planning/parsers/phase_based_parser.py`

**Description:** Parses plans with `## Phase N:` and `### Step N.N:` format.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/phase_based_parser.py` |
| 2 | Extracts phases | `python -c "from platform.src.L05_planning.parsers.phase_based_parser import PhaseBasedParser; p=PhaseBasedParser().parse('# Plan\n## Phase 1: Setup\n### Step 1.1: Init\nDesc'); assert 'Phase 1' in p.phases[0]"` |
| 3 | Extracts steps with phase prefix | `python -c "from platform.src.L05_planning.parsers.phase_based_parser import PhaseBasedParser; p=PhaseBasedParser().parse('# Plan\n## Phase 1: Setup\n### Step 1.1: Init\nDesc'); assert p.steps[0].id.startswith('1')"` |
| 4 | Infers dependencies from numbering | `python -c "from platform.src.L05_planning.parsers.phase_based_parser import PhaseBasedParser; p=PhaseBasedParser().parse('# P\n## Phase 1: S\n### Step 1.1: A\nD\n### Step 1.2: B\nD'); assert '1.1' in str(p.steps[1].dependencies)"` |

**Compensation:** `rm platform/src/L05_planning/parsers/phase_based_parser.py`

**Implementation:**

```python
"""
Phase-Based Parser - Parses ## Phase N: format
Path: platform/src/L05_planning/parsers/phase_based_parser.py
"""

import re
from typing import List, Optional, Tuple
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class PhaseBasedParser(BaseParser):
    """Parses plans with phase-based format: ## Phase N: Title"""
    
    PHASE_PATTERN = re.compile(r'^##\s+Phase\s+(\d+):\s*(.+)$', re.MULTILINE)
    STEP_PATTERN = re.compile(r'^###\s+Step\s+(\d+)\.(\d+):\s*(.+)$', re.MULTILINE)
    
    def can_parse(self, markdown: str) -> bool:
        return bool(self.PHASE_PATTERN.search(markdown))
    
    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        phases = self._extract_phases(markdown)
        steps = self._extract_steps(markdown)
        
        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            phases=phases,
            format_type=FormatType.PHASE_BASED
        )
    
    def _extract_phases(self, markdown: str) -> List[str]:
        phases = []
        for match in self.PHASE_PATTERN.finditer(markdown):
            phase_num = match.group(1)
            phase_title = match.group(2).strip()
            phases.append(f"Phase {phase_num}: {phase_title}")
        return phases
    
    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        steps = []
        matches = list(self.STEP_PATTERN.finditer(markdown))
        
        for i, match in enumerate(matches):
            phase_num = match.group(1)
            step_num = match.group(2)
            step_title = match.group(3).strip()
            
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            
            next_phase = self.PHASE_PATTERN.search(markdown[start:end])
            if next_phase:
                end = start + next_phase.start()
            
            description = markdown[start:end].strip()
            
            step_id = f"{phase_num}.{step_num}"
            dependencies = []
            if int(step_num) > 1:
                dependencies.append(f"{phase_num}.{int(step_num)-1}")
            
            step = PlanStep(
                id=step_id,
                title=step_title,
                description=description,
                phase=f"Phase {phase_num}",
                dependencies=dependencies
            )
            
            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)
            
            steps.append(step)
        
        return steps
```

---

#### Unit 1.5: Part-Based Parser

**Path:** `platform/src/L05_planning/parsers/part_based_parser.py`

**Description:** Parses plans with `# PART A:` and `### Step N:` format.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/part_based_parser.py` |
| 2 | Extracts parts | `python -c "from platform.src.L05_planning.parsers.part_based_parser import PartBasedParser; p=PartBasedParser().parse('# Plan\n# PART A: Setup\n### Step 1: Init\nDesc'); assert 'PART A' in p.phases[0]"` |
| 3 | Prefixes step IDs with part letter | `python -c "from platform.src.L05_planning.parsers.part_based_parser import PartBasedParser; p=PartBasedParser().parse('# Plan\n# PART A: S\n### Step 1: I\nD'); assert p.steps[0].id.startswith('A')"` |
| 4 | Handles multiple parts | `python -c "from platform.src.L05_planning.parsers.part_based_parser import PartBasedParser; p=PartBasedParser().parse('# P\n# PART A: X\n### Step 1: Y\nD\n# PART B: Z\n### Step 1: W\nD'); assert len(p.steps)==2"` |

**Compensation:** `rm platform/src/L05_planning/parsers/part_based_parser.py`

**Implementation:**

```python
"""
Part-Based Parser - Parses # PART A: format
Path: platform/src/L05_planning/parsers/part_based_parser.py
"""

import re
from typing import List
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class PartBasedParser(BaseParser):
    """Parses plans with part-based format: # PART A: Title"""
    
    PART_PATTERN = re.compile(r'^#\s+PART\s+([A-Z]+):\s*(.+)$', re.MULTILINE)
    STEP_PATTERN = re.compile(r'^###\s+Step\s+(\d+):\s*(.+)$', re.MULTILINE)
    
    def can_parse(self, markdown: str) -> bool:
        return bool(self.PART_PATTERN.search(markdown))
    
    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        parts = self._extract_parts(markdown)
        steps = self._extract_steps(markdown)
        
        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            phases=parts,
            format_type=FormatType.PART_BASED
        )
    
    def _extract_parts(self, markdown: str) -> List[str]:
        parts = []
        for match in self.PART_PATTERN.finditer(markdown):
            part_letter = match.group(1)
            part_title = match.group(2).strip()
            parts.append(f"PART {part_letter}: {part_title}")
        return parts
    
    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        steps = []
        
        part_matches = list(self.PART_PATTERN.finditer(markdown))
        
        for pi, part_match in enumerate(part_matches):
            part_letter = part_match.group(1)
            part_start = part_match.end()
            part_end = part_matches[pi + 1].start() if pi + 1 < len(part_matches) else len(markdown)
            
            part_content = markdown[part_start:part_end]
            step_matches = list(self.STEP_PATTERN.finditer(part_content))
            
            for si, step_match in enumerate(step_matches):
                step_num = step_match.group(1)
                step_title = step_match.group(2).strip()
                
                start = step_match.end()
                end = step_matches[si + 1].start() if si + 1 < len(step_matches) else len(part_content)
                description = part_content[start:end].strip()
                
                step_id = f"{part_letter}-{step_num}"
                dependencies = []
                if int(step_num) > 1:
                    dependencies.append(f"{part_letter}-{int(step_num)-1}")
                
                step = PlanStep(
                    id=step_id,
                    title=step_title,
                    description=description,
                    phase=f"PART {part_letter}",
                    dependencies=dependencies
                )
                
                if not step.acceptance_criteria:
                    step.acceptance_criteria = self._generate_acceptance_criteria(step)
                
                steps.append(step)
        
        return steps
```

---

#### Unit 1.6: Table-Based Parser

**Path:** `platform/src/L05_planning/parsers/table_based_parser.py`

**Description:** Parses plans with markdown table format.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/table_based_parser.py` |
| 2 | Extracts steps from table rows | `python -c "from platform.src.L05_planning.parsers.table_based_parser import TableBasedParser; p=TableBasedParser().parse('# Plan\n| Step | Desc |\n|---|---|\n| 1 | Do X |'); assert len(p.steps)>=1"` |
| 3 | Maps columns to step fields | `python -c "from platform.src.L05_planning.parsers.table_based_parser import TableBasedParser; p=TableBasedParser().parse('# P\n| Step | Description |\n|---|---|\n| Init | Set up |'); assert p.steps[0].description"` |

**Compensation:** `rm platform/src/L05_planning/parsers/table_based_parser.py`

**Implementation:**

```python
"""
Table-Based Parser - Parses markdown table format
Path: platform/src/L05_planning/parsers/table_based_parser.py
"""

import re
from typing import Dict, List, Optional
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class TableBasedParser(BaseParser):
    """Parses plans with table format: | Step | Description | ... |"""
    
    TABLE_ROW_PATTERN = re.compile(r'^\|(.+)\|$', re.MULTILINE)
    SEPARATOR_PATTERN = re.compile(r'^[\|\s\-:]+$')
    
    COLUMN_MAPPINGS = {
        'step': 'title',
        'title': 'title',
        'name': 'title',
        'description': 'description',
        'desc': 'description',
        'details': 'description',
        'files': 'files',
        'file': 'files',
        'depends': 'dependencies',
        'dependencies': 'dependencies',
        'requires': 'dependencies',
    }
    
    def can_parse(self, markdown: str) -> bool:
        rows = self.TABLE_ROW_PATTERN.findall(markdown)
        return len(rows) >= 2 and any(self.SEPARATOR_PATTERN.match(r.strip()) for r in rows)
    
    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        steps = self._extract_steps(markdown)
        
        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            format_type=FormatType.TABLE_BASED
        )
    
    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        rows = self.TABLE_ROW_PATTERN.findall(markdown)
        if len(rows) < 2:
            return []
        
        headers = [h.strip().lower() for h in rows[0].split('|') if h.strip()]
        
        column_map = {}
        for i, header in enumerate(headers):
            for key, field in self.COLUMN_MAPPINGS.items():
                if key in header:
                    column_map[i] = field
                    break
        
        steps = []
        for row_idx, row in enumerate(rows[1:], 1):
            if self.SEPARATOR_PATTERN.match(row.strip()):
                continue
            
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if not cells:
                continue
            
            step_data = {'title': '', 'description': '', 'files': [], 'dependencies': []}
            
            for i, cell in enumerate(cells):
                if i in column_map:
                    field = column_map[i]
                    if field in ('files', 'dependencies'):
                        step_data[field] = [x.strip() for x in cell.split(',') if x.strip()]
                    else:
                        step_data[field] = cell
            
            if not step_data['title']:
                step_data['title'] = cells[0] if cells else f"Step {row_idx}"
            
            step = PlanStep(
                id=f"step-{row_idx}",
                title=step_data['title'],
                description=step_data['description'],
                files=step_data['files'],
                dependencies=step_data['dependencies']
            )
            
            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)
            
            steps.append(step)
        
        return steps
```

---

#### Unit 1.7: Multi-Format Parser

**Path:** `platform/src/L05_planning/parsers/multi_format_parser.py`

**Description:** Unified parser that detects format and routes to appropriate parser.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/parsers/multi_format_parser.py` |
| 2 | Routes to correct parser based on format | `python -c "from platform.src.L05_planning.parsers.multi_format_parser import MultiFormatParser; p=MultiFormatParser().parse('# PART A: X\n### Step 1: Y\nD'); assert p.format_type.value=='part_based'"` |
| 3 | Returns non-empty steps for valid plan | `python -c "from platform.src.L05_planning.parsers.multi_format_parser import MultiFormatParser; p=MultiFormatParser().parse('# Plan\n1. **Step**\n   Desc'); assert len(p.steps)>0"` |
| 4 | Raises ParseError for unparseable content | `python -c "from platform.src.L05_planning.parsers.multi_format_parser import MultiFormatParser, ParseError; import sys; p=MultiFormatParser(); exec('try:\\n p.parse(\"no valid format\")\\nexcept ParseError:\\n sys.exit(0)'); sys.exit(1)"` |

**Compensation:** `rm platform/src/L05_planning/parsers/multi_format_parser.py`

**Implementation:**

```python
"""
Multi-Format Parser - Unified entry point
Path: platform/src/L05_planning/parsers/multi_format_parser.py
"""

from typing import Dict, Type

from .base_parser import BaseParser, ParsedPlan
from .format_detector import FormatDetector, FormatType
from .numbered_list_parser import NumberedListParser
from .phase_based_parser import PhaseBasedParser
from .part_based_parser import PartBasedParser
from .table_based_parser import TableBasedParser


class ParseError(Exception):
    """Raised when plan markdown cannot be parsed."""
    pass


class MultiFormatParser:
    """Unified parser that detects format and routes to appropriate parser."""
    
    def __init__(self):
        self.detector = FormatDetector()
        self._parsers: Dict[FormatType, BaseParser] = {
            FormatType.NUMBERED_LIST: NumberedListParser(),
            FormatType.PHASE_BASED: PhaseBasedParser(),
            FormatType.PART_BASED: PartBasedParser(),
            FormatType.TABLE_BASED: TableBasedParser(),
            FormatType.SUBPLAN: PhaseBasedParser(),
            FormatType.HIERARCHICAL: PhaseBasedParser(),
        }
    
    def parse(self, markdown: str) -> ParsedPlan:
        """
        Parses plan markdown into structured ParsedPlan.
        
        1. Detects format type
        2. Routes to appropriate parser
        3. Returns ParsedPlan with steps
        
        Raises:
            ParseError: If format cannot be determined or parsing fails
        """
        detection = self.detector.detect(markdown)
        
        if detection.format_type == FormatType.UNKNOWN:
            if detection.fallback_format and detection.fallback_format in self._parsers:
                parser = self._parsers[detection.fallback_format]
            else:
                raise ParseError(
                    f"Could not determine plan format. "
                    f"Confidence: {detection.confidence:.2f}"
                )
        else:
            parser = self._parsers.get(detection.format_type)
            if not parser:
                raise ParseError(f"No parser available for format: {detection.format_type}")
        
        try:
            result = parser.parse(markdown)
            result.format_type = detection.format_type
            
            if not result.steps:
                raise ParseError("Parser returned no steps")
            
            return result
            
        except Exception as e:
            if isinstance(e, ParseError):
                raise
            raise ParseError(f"Parse failed: {e}") from e
```

---

#### Unit 1.8: CLI Adapter Integration

**Path:** `platform/src/L05_planning/adapters/cli_plan_adapter.py`

**Description:** Modify existing CLI adapter to use MultiFormatParser.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is valid Python | `python -m py_compile platform/src/L05_planning/adapters/cli_plan_adapter.py` |
| 2 | parse_plan_markdown returns steps for part-based format | See validation script below |
| 3 | parse_plan_markdown returns steps for phase-based format | See validation script below |
| 4 | Gate 2 no longer shows "0 steps" | Manual test with real plan file |

**Validation Script (save as test_adapter.py):**

```python
#!/usr/bin/env python3
"""Validation script for Unit 1.8"""
import sys
sys.path.insert(0, 'platform/src')

from L05_planning.adapters.cli_plan_adapter import CLIPlanAdapter

# Test 1: Part-based format
part_plan = """
# Test Plan
# PART A: Setup
### Step 1: Initialize
Set up the environment.
### Step 2: Configure
Configure settings.
"""

adapter = CLIPlanAdapter()
result = adapter.parse_plan_markdown(part_plan)
assert len(result.get('steps', [])) >= 2, f"Expected >=2 steps, got {len(result.get('steps', []))}"
print(f"✓ Part-based: {len(result['steps'])} steps")

# Test 2: Phase-based format
phase_plan = """
# Test Plan
## Phase 1: Foundation
### Step 1.1: Database
Set up database.
### Step 1.2: API
Create API endpoints.
"""

result = adapter.parse_plan_markdown(phase_plan)
assert len(result.get('steps', [])) >= 2, f"Expected >=2 steps, got {len(result.get('steps', []))}"
print(f"✓ Phase-based: {len(result['steps'])} steps")

print("\n✓ All adapter tests passed")
```

**Compensation:** `git checkout -- platform/src/L05_planning/adapters/cli_plan_adapter.py`

**Implementation Note:** This unit MODIFIES an existing file. The key change is replacing the old regex-based parsing with MultiFormatParser:

```python
# In CLIPlanAdapter.parse_plan_markdown():
# OLD CODE:
#   steps = self._parse_numbered_list(markdown)  # Only handles one format
#
# NEW CODE:
from ..parsers.multi_format_parser import MultiFormatParser, ParseError

def parse_plan_markdown(self, markdown: str) -> dict:
    """Parse plan markdown using multi-format parser."""
    try:
        parser = MultiFormatParser()
        plan = parser.parse(markdown)
        
        return {
            'plan_id': plan.plan_id,
            'title': plan.title,
            'format': plan.format_type.value,
            'steps': [
                {
                    'id': s.id,
                    'title': s.title,
                    'description': s.description,
                    'files': s.files,
                    'dependencies': s.dependencies,
                    'acceptance_criteria': s.acceptance_criteria,
                }
                for s in plan.steps
            ],
            'phases': plan.phases,
        }
    except ParseError as e:
        return {'error': str(e), 'steps': []}
```

---

#### Unit 2.1: Catalog Validator Tool

**Path:** `platform/tools/catalog_validator.py`

**Description:** Validates service_catalog.json completeness against discovered services.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is executable | `python platform/tools/catalog_validator.py --help` |
| 2 | Discovers service classes in platform | `python platform/tools/catalog_validator.py 2>&1 \| grep -i "discovered"` |
| 3 | Reports missing catalog entries | `python platform/tools/catalog_validator.py 2>&1 \| grep -i "missing"` |
| 4 | --fix --dry-run shows what would be added | `python platform/tools/catalog_validator.py --fix --dry-run` |

**Compensation:** `rm platform/tools/catalog_validator.py`

**Implementation:**

```python
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
            return {"services": []}
        with open(self.catalog_path) as f:
            return json.load(f)
    
    def validate(self) -> CatalogValidationResult:
        discovered = self.discover_services()
        catalog = self.load_catalog()
        
        discovered_names = {s.name for s in discovered}
        catalog_names = {s["name"] for s in catalog.get("services", [])}
        
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
        catalog_names = {s["name"] for s in catalog.get("services", [])}
        
        new_entries = []
        for service in discovered:
            if service.name not in catalog_names:
                new_entries.append(self.generate_entry(service))
        
        if not dry_run and new_entries:
            catalog.setdefault("services", []).extend(new_entries)
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
```

---

#### Unit 2.2: Add 6 Missing Catalog Entries

**Path:** `platform/src/L12_nl_interface/data/service_catalog.json`

**Description:** Add missing L05 service entries to catalog.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | PlanCache entry exists | `cat platform/src/L12_nl_interface/data/service_catalog.json \| grep -i "PlanCache"` |
| 2 | ExecutionMonitor entry exists | `cat platform/src/L12_nl_interface/data/service_catalog.json \| grep -i "ExecutionMonitor"` |
| 3 | All 6 L05 services present | `python -c "import json; d=json.load(open('platform/src/L12_nl_interface/data/service_catalog.json')); l5=[s for s in d['services'] if s.get('layer')=='L05']; assert len(l5)>=6, f'Only {len(l5)} L05 services'"` |
| 4 | catalog_validator passes | `python platform/tools/catalog_validator.py` |

**Compensation:** `git checkout -- platform/src/L12_nl_interface/data/service_catalog.json`

**Entries to Add:**

```json
{
  "name": "PlanCache",
  "layer": "L05",
  "category": "caching",
  "description": "Two-level cache (LRU + Redis) for plan decomposition results",
  "methods": ["get", "set", "invalidate", "clear"]
},
{
  "name": "ExecutionMonitor",
  "layer": "L05",
  "category": "monitoring",
  "description": "Monitors plan execution progress and status",
  "methods": ["start", "stop", "get_status", "get_metrics"]
},
{
  "name": "DependencyResolver",
  "layer": "L05",
  "category": "planning",
  "description": "Resolves task dependencies with cycle detection and topological sort",
  "methods": ["resolve", "get_order", "check_cycles", "get_dependency_graph"]
},
{
  "name": "PlanValidator",
  "layer": "L05",
  "category": "validation",
  "description": "Validates plan syntax, semantics, feasibility, and security",
  "methods": ["validate", "get_errors", "check_feasibility"]
},
{
  "name": "ResourceEstimator",
  "layer": "L05",
  "category": "planning",
  "description": "Estimates token, cost, and time requirements for plans",
  "methods": ["estimate", "get_breakdown", "check_budget"]
},
{
  "name": "ContextInjector",
  "layer": "L05",
  "category": "context",
  "description": "Assembles token-budgeted context for plan execution",
  "methods": ["inject", "get_context", "set_budget"]
}
```

---

#### Unit 2.3: Dependency Analyzer Tool

**Path:** `platform/tools/dependency_analyzer.py`

**Description:** Analyzes import dependencies, detects circular deps and layer violations.

**Acceptance Criteria:**

| # | Criterion | Validation Command |
|---|-----------|-------------------|
| 1 | File exists and is executable | `python platform/tools/dependency_analyzer.py --help` |
| 2 | Detects layer violations | `python platform/tools/dependency_analyzer.py 2>&1 \| grep -i "violation\|layer"` |
| 3 | Outputs JSON with --json flag | `python platform/tools/dependency_analyzer.py --json \| python -m json.tool` |

**Compensation:** `rm platform/tools/dependency_analyzer.py`

**Implementation:**

```python
#!/usr/bin/env python3
"""
Dependency Chain Analyzer
Path: platform/tools/dependency_analyzer.py
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd() / "platform")
    args = parser.parse_args()
    
    result = DependencyAnalyzer(args.root).analyze()
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Issues found: {result['issue_count']}")
        for issue in result['issues']:
            print(f"  [{issue['severity']}] {issue['message']}")
    
    return 0 if result['issue_count'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

### 4.3 Remaining Units (Summary)

Units 3.1-5.4 follow the same pattern. For brevity, here are the key specifications:

| Unit | Key Implementation | Critical Acceptance Criterion |
|------|-------------------|------------------------------|
| 3.1 SpecDecomposer | Takes ParsedPlan → List[AtomicUnit] | `assert len(decomposer.decompose(plan)) > 0` |
| 3.2 UnitValidator | Calls L06 QualityScorer | `assert validator.validate(unit).passed in [True, False]` |
| 3.3 RegressionGuardian | Runs pytest via subprocess | `assert guardian.check(unit).tests_run >= 0` |
| 3.4 IntegrationSentinel | Uses CatalogValidator | `assert sentinel.validate(unit).passed in [True, False]` |
| 3.5 RollbackCoordinator | Git operations | `assert coordinator.rollback(checkpoint_id).success` |
| 4.1 CheckpointManager | Git commit + file state | `assert manager.begin_unit(unit) is not None` |
| 4.2 GitState | `git rev-parse HEAD` | `assert git_state.capture() is not None` |
| 4.3 FileState | Read/write file contents | `assert file_state.capture(paths) == file_state.restore(state)` |
| 5.1-5.4 Integration | HTTP clients to L01/L04/L06/L11 | Connection test or mock validation |

---

## 5. Sprint Execution Protocol

### 5.1 Pre-Sprint Setup

```bash
# 1. Ensure clean working directory
cd /path/to/project
git status  # Should be clean

# 2. Create feature branch
git checkout -b feature/l05-planning-v2

# 3. Create directory structure
mkdir -p platform/src/L05_planning/parsers
mkdir -p platform/src/L05_planning/agents
mkdir -p platform/src/L05_planning/checkpoint
mkdir -p platform/src/L05_planning/integration
mkdir -p platform/tools
touch platform/src/L05_planning/parsers/__init__.py
touch platform/src/L05_planning/agents/__init__.py
touch platform/src/L05_planning/checkpoint/__init__.py
touch platform/src/L05_planning/integration/__init__.py

# 4. Initial commit
git add -A && git commit -m "chore: create L05 v2 directory structure"
```

### 5.2 Per-Unit Execution (THE PROTOCOL)

For each unit, Claude CLI MUST execute this exact sequence:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      UNIT EXECUTION PROTOCOL                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  STEP 1: CHECKPOINT                                                           ║
║  ───────────────────                                                          ║
║  $ git add -A && git commit -m "checkpoint: before unit {X.Y}"               ║
║                                                                               ║
║  STEP 2: IMPLEMENT                                                            ║
║  ─────────────────                                                            ║
║  Create/modify file(s) per unit specification                                 ║
║  Use implementation code provided in spec                                     ║
║                                                                               ║
║  STEP 3: VALIDATE (run EVERY acceptance criterion)                            ║
║  ────────────────                                                             ║
║  For each criterion in unit's Acceptance Criteria table:                      ║
║    $ {validation_command}                                                     ║
║    If fails → GOTO STEP 6                                                     ║
║                                                                               ║
║  STEP 4: REGRESSION                                                           ║
║  ───────────────────                                                          ║
║  $ pytest platform/tests/L05_planning/ -x --tb=short                         ║
║  If fails → GOTO STEP 6                                                       ║
║                                                                               ║
║  STEP 5: INTEGRATION                                                          ║
║  ────────────────────                                                         ║
║  $ python -c "from platform.src.L05_planning.parsers import *"               ║
║  $ python platform/tools/catalog_validator.py  (if Unit >= 2.1)              ║
║  If fails → GOTO STEP 6                                                       ║
║                                                                               ║
║  STEP 6: ROLLBACK (only if validation failed)                                 ║
║  ────────────────                                                             ║
║  $ git checkout -- platform/src/L05_planning/                                ║
║  Analyze failure, fix issue, GOTO STEP 2                                      ║
║                                                                               ║
║  STEP 7: COMMIT                                                               ║
║  ─────────────                                                                ║
║  $ git add -A && git commit -m "feat(L05): complete unit {X.Y} - {title}"    ║
║                                                                               ║
║  STEP 8: REPORT                                                               ║
║  ─────────────                                                                ║
║  Echo: "✓ Unit {X.Y} complete. Proceeding to Unit {X.Y+1}"                   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 5.3 Sprint Prompt

Copy this prompt to start implementation:

```markdown
# L05 Planning Service V2 - Bootstrap Implementation

You are implementing the L05 Planning Service V2. This implementation uses a 
MANUAL VALIDATION-FIRST PROTOCOL that mirrors the automated system being built.

## CRITICAL RULES

1. **DO NOT SKIP VALIDATION STEPS** - Every acceptance criterion must pass
2. **DO NOT PROCEED ON FAILURE** - Rollback and fix before continuing
3. **COMMIT AFTER EACH UNIT** - Creates recovery points
4. **REPORT STATUS** - Echo completion after each unit

## PROTOCOL

For EVERY unit, execute this exact sequence:

1. CHECKPOINT: `git add -A && git commit -m "checkpoint: before unit X.Y"`
2. IMPLEMENT: Create/modify files per specification
3. VALIDATE: Run EACH acceptance criterion command from the spec
4. REGRESSION: `pytest platform/tests/L05_planning/ -x --tb=short`
5. INTEGRATION: Import check + catalog_validator (if applicable)
6. ON FAILURE: `git checkout -- platform/src/L05_planning/` → fix → retry
7. COMMIT: `git add -A && git commit -m "feat(L05): complete unit X.Y"`
8. REPORT: "✓ Unit X.Y complete"

## IMPLEMENTATION ORDER

Execute units in this exact order:
1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8 → 2.1 → 2.2 → 2.3

## START

Begin with Unit 1.1: Format Detector

Read the specification for Unit 1.1, then:
1. Create checkpoint
2. Create `platform/src/L05_planning/parsers/format_detector.py`
3. Run all 4 acceptance criteria commands
4. If all pass, commit and proceed to Unit 1.2
5. If any fail, rollback and fix

GO.
```

---

## 6. Success Criteria

### 6.1 Phase 1 Complete (Parser Fixed)

| Criterion | Validation |
|-----------|------------|
| Gate 2 shows step count > 0 | Create test plan, run hook, check output |
| All 6 format types detected | Run FormatDetector on sample plans |
| Steps extracted from real Claude plans | Test with cuddly-wobbling-sphinx.md |

### 6.2 Phase 2 Complete (Catalog Fixed)

| Criterion | Validation |
|-----------|------------|
| 6 L05 services in catalog | `catalog_validator.py` passes |
| No missing entries | `catalog_validator.py` reports 0 missing |
| Import paths work | `from platform.src.L05_planning.services import PlanCache` |

### 6.3 Full Implementation Complete

| Criterion | Validation |
|-----------|------------|
| All 23 units committed | `git log --oneline \| grep "feat(L05)" \| wc -l` ≥ 23 |
| All tests pass | `pytest platform/tests/L05_planning/ -v` |
| Parser handles all formats | See Phase 1 |
| Catalog complete | See Phase 2 |
| Gate 2 fully functional | Manual E2E test |

---

## 7. Appendix: Test Fixtures

### 7.1 Sample Part-Based Plan

```markdown
# Platform Services Enhancement Plan

## Overview
This plan covers two enhancements.

# PART A: SERVICE DISCOVERY

### Step 1: Intent Recognition
Implement intent detection using semantic embeddings.

### Step 2: Service Matching
Match user intent to services with confidence scores.

# PART B: ERROR RECOVERY

### Step 1: Auto-Debug
Add automatic error analysis and retry logic.

### Step 2: Alternative Routing
Route to alternative services when primary fails.
```

### 7.2 Sample Phase-Based Plan

```markdown
# Database Migration Plan

## Phase 1: Preparation

### Step 1.1: Backup
Create full database backup.

### Step 1.2: Schema Analysis
Analyze current schema for migration requirements.

## Phase 2: Migration

### Step 2.1: Schema Changes
Apply schema migrations.

### Step 2.2: Data Migration
Migrate data to new schema.
```

### 7.3 Sample Numbered List Plan

```markdown
# API Enhancement Plan

1. **Add Authentication**
   Implement JWT-based authentication.
   Files: auth.py, middleware.py
   Depends: -

2. **Add Rate Limiting**
   Implement token bucket rate limiting.
   Files: rate_limit.py
   Depends: step-1

3. **Add Caching**
   Add Redis-based response caching.
   Files: cache.py
   Depends: step-1
```

---

*End of L05 Planning Service V2 Bootstrap Specification*
