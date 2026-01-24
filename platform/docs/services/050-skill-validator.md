# Service 50/52: SkillValidator

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L14 (Skill Library Layer) |
| **Module** | `L14_skill_library.services.skill_validator` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PyYAML |
| **Category** | Skill Library / Validation |

## Role in Development Environment

The **SkillValidator** performs comprehensive validation of skill definitions including schema and content quality. It provides:
- YAML syntax validation
- Schema validation (required sections, field types)
- Content quality checks
- Severity-based issue reporting
- Validation summary with pass/fail status
- Quick validation for drafts

This is **the quality gate for skills** - before skills are stored or used, SkillValidator ensures they meet format and quality standards.

## Data Model

### ValidationResult
- `valid: bool` - Overall validation result
- `issues: List[ValidationIssue]` - List of issues found
- `errors: int` - Count of ERROR severity issues
- `warnings: int` - Count of WARNING severity issues
- `info: int` - Count of INFO severity issues
- `summary: str` - Human-readable summary

### ValidationIssue
- `severity: ValidationSeverity` - Issue severity
- `code: str` - Issue code (e.g., "V001")
- `message: str` - Issue description
- `location: str` - Location in skill (e.g., "metadata.name")
- `suggestion: str` - Fix suggestion

### ValidationSeverity Enum
- `ERROR` - Must be fixed, blocks storage
- `WARNING` - Should be fixed, doesn't block
- `INFO` - Optional improvement

### Skill Schema Sections
- `metadata` - Name, description, version (required)
- `role` - Role name/identity (required)
- `responsibilities` - List of responsibilities (required)
- `tools` - Available tools (optional)
- `procedures` - Step-by-step procedures (optional)
- `examples` - Usage examples (optional)
- `constraints` - Behavioral constraints (optional)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `strict_mode` | False | Treat warnings as errors |
| `require_examples` | False | Require examples section |
| `min_responsibilities` | 1 | Minimum responsibilities |
| `max_content_size` | 50000 | Maximum content size (chars) |

## API Methods

| Method | Description |
|--------|-------------|
| `validate(skill)` | Full validation of skill |
| `validate_yaml(content)` | Validate YAML syntax only |
| `validate_schema(parsed)` | Validate against schema |
| `validate_content(parsed)` | Validate content quality |
| `quick_validate(skill)` | Fast validation (syntax only) |
| `get_stats()` | Get validation statistics |

## Use Cases in Your Workflow

### 1. Initialize Skill Validator
```python
from L14_skill_library.services.skill_validator import SkillValidator

# Default initialization
validator = SkillValidator()

# Strict mode (warnings become errors)
validator = SkillValidator(strict_mode=True)

# With custom requirements
validator = SkillValidator(
    require_examples=True,
    min_responsibilities=3
)
```

### 2. Validate a Skill
```python
from L14_skill_library.models import Skill

skill = Skill(
    name="python-developer",
    content="""
metadata:
  name: python-developer
  description: Python development expertise
  version: 1.0.0

role: Python Developer

responsibilities:
  - Write clean, maintainable Python code
  - Create comprehensive unit tests
  - Follow PEP 8 guidelines

tools:
  - pytest
  - black
  - mypy
"""
)

result = validator.validate(skill)

if result.valid:
    print("Skill is valid!")
else:
    print(f"Validation failed with {result.errors} errors")
    for issue in result.issues:
        print(f"  [{issue.severity.value}] {issue.code}: {issue.message}")
        if issue.suggestion:
            print(f"    Suggestion: {issue.suggestion}")
```

### 3. Validate YAML Syntax Only
```python
yaml_content = """
role: Developer
responsibilities:
  - Write code
  - This line has bad indentation
    - Nested incorrectly
"""

result = validator.validate_yaml(yaml_content)

if not result.valid:
    print("YAML syntax errors:")
    for issue in result.issues:
        print(f"  Line {issue.location}: {issue.message}")
```

### 4. Quick Validation for Drafts
```python
# Fast validation without content quality checks
result = validator.quick_validate(skill)

if result.valid:
    print("Draft skill syntax is valid")
else:
    print("Fix syntax errors before proceeding")
```

### 5. Check Specific Validation Issues
```python
result = validator.validate(skill)

# Filter by severity
errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]

print(f"Errors ({len(errors)}):")
for error in errors:
    print(f"  {error.code}: {error.message}")
    print(f"    Location: {error.location}")

print(f"\nWarnings ({len(warnings)}):")
for warning in warnings:
    print(f"  {warning.code}: {warning.message}")
```

### 6. Validate Content Quality
```python
# Specific content checks
parsed_content = yaml.safe_load(skill.content)
result = validator.validate_content(parsed_content)

# Content quality checks include:
# - Responsibility descriptions are meaningful
# - Tool names are valid
# - Examples are properly formatted
# - Constraints are actionable

for issue in result.issues:
    if "content" in issue.location:
        print(f"Content issue: {issue.message}")
```

### 7. Validate Before Storage
```python
from L14_skill_library.services.skill_store import SkillStore

store = SkillStore()
validator = SkillValidator()

async def create_skill_safe(skill):
    # Validate first
    result = validator.validate(skill)

    if not result.valid:
        raise ValueError(f"Skill validation failed: {result.summary}")

    # Store if valid
    return await store.create(skill)

try:
    created = await create_skill_safe(skill)
    print(f"Created: {created.skill_id}")
except ValueError as e:
    print(f"Failed: {e}")
```

### 8. Batch Validation
```python
skills = [skill1, skill2, skill3, skill4, skill5]

results = []
for skill in skills:
    result = validator.validate(skill)
    results.append({
        "name": skill.name,
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings
    })

# Summary
valid_count = sum(1 for r in results if r["valid"])
print(f"Valid: {valid_count}/{len(skills)}")

# Show failures
for r in results:
    if not r["valid"]:
        print(f"  Failed: {r['name']} ({r['errors']} errors)")
```

### 9. Custom Validation Rules
```python
# Extend with custom validation
class CustomValidator(SkillValidator):
    def validate_content(self, parsed):
        result = super().validate_content(parsed)

        # Add custom rule: require at least one tool
        if "tools" not in parsed or len(parsed.get("tools", [])) == 0:
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="C001",
                message="Skills should define at least one tool",
                location="tools",
                suggestion="Add a tools section with available tools"
            ))

        return result

custom_validator = CustomValidator()
```

### 10. Get Validation Statistics
```python
stats = validator.get_stats()

print(f"Validation Statistics:")
print(f"  Total validations: {stats['total_validations']}")
print(f"  Passed: {stats['passed']} ({stats['pass_rate']:.1%})")
print(f"  Failed: {stats['failed']}")
print(f"  Common issues:")
for code, count in stats['issue_frequency'].items():
    print(f"    {code}: {count} occurrences")
```

## Service Interactions

```
+-------------------+
|  SkillValidator   | <--- L14 Skill Library Layer
|       (L14)       |
+--------+----------+
         |
   Validates:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
YAML     Schema   Content  Quality
Syntax   Fields   Quality  Checks
```

**Integration Points:**
- **SkillStore (L14)**: Validates before storing
- **SkillGenerator (L14)**: Validates generated skills
- **SkillOptimizer (L14)**: Validates after optimization

## Validation Pipeline

```
Validation Flow:

1. YAML SYNTAX VALIDATION
   ├─ Parse YAML content
   ├─ Check for syntax errors
   └─ If failed → Return with ERROR

2. SCHEMA VALIDATION
   ├─ Check required sections exist:
   │   ├─ metadata (name, description, version)
   │   ├─ role
   │   └─ responsibilities
   ├─ Validate field types
   └─ Check optional sections format

3. CONTENT QUALITY VALIDATION
   ├─ Responsibilities:
   │   ├─ At least min_responsibilities
   │   └─ Each has meaningful description
   ├─ Tools:
   │   └─ Valid tool names
   ├─ Examples:
   │   └─ Properly formatted
   └─ Constraints:
       └─ Actionable statements

4. AGGREGATE RESULTS
   ├─ Collect all issues
   ├─ Count by severity
   └─ Determine valid status:
       └─ valid = (errors == 0)

5. RETURN VALIDATION RESULT
   └─ ValidationResult with all issues
```

## Validation Codes

| Code | Description | Severity |
|------|-------------|----------|
| V001 | Invalid YAML syntax | ERROR |
| V002 | Missing required section | ERROR |
| V003 | Invalid field type | ERROR |
| V004 | Content too large | ERROR |
| V005 | Missing metadata field | ERROR |
| V101 | Missing optional section | WARNING |
| V102 | Short description | WARNING |
| V103 | No examples provided | WARNING |
| V104 | Empty responsibilities | WARNING |
| V201 | Could improve description | INFO |
| V202 | Consider adding constraints | INFO |

## Execution Examples

```python
# Complete validation workflow
from L14_skill_library.services.skill_validator import SkillValidator
from L14_skill_library.models import Skill, ValidationSeverity

# Initialize
validator = SkillValidator(
    strict_mode=False,
    require_examples=False,
    min_responsibilities=2
)

# 1. Valid skill
valid_skill = Skill(
    name="code-reviewer",
    content="""
metadata:
  name: code-reviewer
  description: Expert code review capabilities for maintaining code quality
  version: 1.0.0

role: Code Reviewer

responsibilities:
  - Review code changes for bugs and issues
  - Ensure code follows style guidelines
  - Suggest improvements for maintainability
  - Check for security vulnerabilities

tools:
  - github
  - gitlab
  - reviewbot

examples:
  - input: "Review this pull request"
    output: "I'll analyze the changes for issues..."

constraints:
  - Always be constructive in feedback
  - Focus on code, not the author
"""
)

print("Validating valid skill...")
result = validator.validate(valid_skill)
print(f"Valid: {result.valid}")
print(f"Summary: {result.summary}")

# 2. Skill with errors
invalid_skill = Skill(
    name="broken-skill",
    content="""
# Missing metadata section!

role: Some Role

# responsibilities is empty
responsibilities: []
"""
)

print("\nValidating invalid skill...")
result = validator.validate(invalid_skill)
print(f"Valid: {result.valid}")
print(f"Errors: {result.errors}, Warnings: {result.warnings}")

print("\nIssues found:")
for issue in result.issues:
    severity = issue.severity.value
    print(f"  [{severity}] {issue.code}: {issue.message}")
    print(f"    Location: {issue.location}")
    if issue.suggestion:
        print(f"    Suggestion: {issue.suggestion}")

# 3. Skill with warnings only
warning_skill = Skill(
    name="minimal-skill",
    content="""
metadata:
  name: minimal-skill
  description: A minimal skill
  version: 1.0.0

role: Minimal Role

responsibilities:
  - Do something
  - Do something else
"""
)

print("\nValidating minimal skill...")
result = validator.validate(warning_skill)
print(f"Valid: {result.valid}")  # True (warnings don't fail)
print(f"Warnings: {result.warnings}")

for issue in result.issues:
    if issue.severity == ValidationSeverity.WARNING:
        print(f"  Warning: {issue.message}")

# 4. YAML syntax check
print("\nChecking YAML syntax...")
bad_yaml = """
role: Test
  responsibilities:  # Bad indentation
  - item
"""

result = validator.validate_yaml(bad_yaml)
if not result.valid:
    print("YAML syntax error detected")
    print(f"  {result.issues[0].message}")

# 5. Quick validation
print("\nQuick validation (syntax only)...")
result = validator.quick_validate(valid_skill)
print(f"Syntax valid: {result.valid}")

# 6. Statistics
print("\nValidation Statistics:")
stats = validator.get_stats()
print(f"  Total: {stats['total_validations']}")
print(f"  Pass rate: {stats['pass_rate']:.1%}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| SkillValidator class | Complete |
| validate() | Complete |
| validate_yaml() | Complete |
| validate_schema() | Complete |
| validate_content() | Complete |
| quick_validate() | Complete |
| Severity levels | Complete |
| Issue codes | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Custom rules engine | Medium | User-defined validation rules |
| Async validation | Medium | Non-blocking validation |
| Schema registry | Low | External schema definitions |
| Validation profiles | Low | Predefined validation configs |
| Auto-fix suggestions | Low | Automatic issue fixes |

## Strengths

- **Comprehensive** - YAML, schema, and content validation
- **Severity levels** - Errors vs warnings vs info
- **Detailed issues** - Location, code, suggestion
- **Configurable** - Strict mode, requirements
- **Fast quick mode** - Syntax-only validation
- **Statistics** - Track validation trends

## Weaknesses

- **No custom rules** - Fixed validation logic
- **Synchronous** - Blocking validation
- **No auto-fix** - Manual fixes required
- **English-centric** - Content checks assume English
- **Limited schema** - Basic YAML schema only
- **No validation caching** - Re-validates each time

## Best Practices

### Validate Early
Validate during development:
```python
# Good: Validate before storing
result = validator.validate(skill)
if result.valid:
    await store.create(skill)

# Also validate after generation
generated = await generator.generate(request)
result = validator.validate(generated)
```

### Handle Warnings
Don't ignore warnings:
```python
result = validator.validate(skill)

if result.valid:
    if result.warnings > 0:
        # Log warnings even if valid
        for issue in result.issues:
            if issue.severity == ValidationSeverity.WARNING:
                logger.warning(f"Skill warning: {issue.message}")
```

### Use Strict Mode for Production
Enable strict mode for production skills:
```python
# Development: Lenient
dev_validator = SkillValidator(strict_mode=False)

# Production: Strict
prod_validator = SkillValidator(
    strict_mode=True,
    require_examples=True,
    min_responsibilities=3
)
```

## Source Files

- Service: `platform/src/L14_skill_library/services/skill_validator.py`
- Models: `platform/src/L14_skill_library/models/`
- Spec: L14 Skill Library Layer specification

## Related Services

- SkillStore (L14) - Stores validated skills
- SkillGenerator (L14) - Generates skills to validate
- SkillOptimizer (L14) - Optimizes validated skills

---
*Generated: 2026-01-24 | Platform Services Documentation*
