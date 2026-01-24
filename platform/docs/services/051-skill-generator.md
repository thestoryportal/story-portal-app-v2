# Service 51/52: SkillGenerator

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L14 (Skill Library Layer) |
| **Module** | `L14_skill_library.services.skill_generator` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | L04 Model Gateway |
| **Category** | Skill Library / Generation |

## Role in Development Environment

The **SkillGenerator** uses LLM capabilities to generate skill definitions from high-level descriptions. It provides:
- LLM-based skill generation via L04 Model Gateway
- Template-based generation for common roles
- Structured JSON output parsing
- Skill validation integration
- Generation from partial specifications
- Iterative refinement support

This is **the skill creation engine** - when new skills are needed, SkillGenerator creates comprehensive skill definitions from descriptions or templates.

## Data Model

### GenerationRequest
- `name: str` - Desired skill name
- `description: str` - High-level skill description
- `category: str` - Skill category
- `requirements: List[str]` - Specific requirements
- `base_template: str` - Optional template to start from
- `constraints: Dict` - Generation constraints

### GenerationResult
- `skill: Skill` - Generated skill
- `validation: ValidationResult` - Validation result
- `tokens_used: int` - LLM tokens consumed
- `generation_time_ms: int` - Generation latency
- `model_used: str` - LLM model used
- `iterations: int` - Refinement iterations

### SkillTemplate
- `developer` - Software developer template
- `reviewer` - Code reviewer template
- `analyst` - Data analyst template
- `architect` - System architect template
- `tester` - QA tester template

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gateway_client` | None | L04 Model Gateway client |
| `default_model` | "claude-3-sonnet" | Default LLM model |
| `max_tokens` | 4000 | Maximum output tokens |
| `temperature` | 0.7 | Generation temperature |
| `auto_validate` | True | Validate after generation |
| `max_retries` | 3 | Max retry attempts |

## API Methods

| Method | Description |
|--------|-------------|
| `generate(request)` | Generate skill from description |
| `generate_from_template(template, params)` | Generate from template |
| `refine(skill, feedback)` | Refine existing skill |
| `expand(skill, section)` | Expand specific section |
| `get_templates()` | List available templates |
| `get_stats()` | Get generation statistics |

## Use Cases in Your Workflow

### 1. Initialize Skill Generator
```python
from L14_skill_library.services.skill_generator import SkillGenerator
from L04_model_gateway.services.model_gateway import ModelGateway

# Default initialization
generator = SkillGenerator()

# With custom gateway
gateway = ModelGateway()
generator = SkillGenerator(
    gateway_client=gateway,
    default_model="claude-3-opus",
    temperature=0.5
)
```

### 2. Generate Skill from Description
```python
from L14_skill_library.models import GenerationRequest

request = GenerationRequest(
    name="security-auditor",
    description="""
    A security expert who audits code and systems for vulnerabilities.
    Should be able to identify OWASP Top 10 issues, review authentication
    flows, and recommend security improvements.
    """,
    category="security",
    requirements=[
        "Knowledge of OWASP Top 10",
        "Experience with penetration testing",
        "Understanding of authentication protocols"
    ]
)

result = await generator.generate(request)

print(f"Skill generated: {result.skill.name}")
print(f"Validation: {'PASS' if result.validation.valid else 'FAIL'}")
print(f"Tokens used: {result.tokens_used}")
print(f"Time: {result.generation_time_ms}ms")

# View generated content
print(f"\nGenerated content:\n{result.skill.content}")
```

### 3. Generate from Template
```python
# Use predefined template
result = await generator.generate_from_template(
    template="developer",
    params={
        "name": "python-backend-developer",
        "language": "Python",
        "framework": "FastAPI",
        "specialty": "REST API development",
        "tools": ["pytest", "black", "mypy", "sqlalchemy"]
    }
)

print(f"Generated from template: {result.skill.name}")
```

### 4. List Available Templates
```python
templates = generator.get_templates()

print("Available templates:")
for name, info in templates.items():
    print(f"  {name}:")
    print(f"    Description: {info['description']}")
    print(f"    Parameters: {info['parameters']}")
```

### 5. Refine Existing Skill
```python
# Refine based on feedback
refined = await generator.refine(
    skill=existing_skill,
    feedback="""
    - Add more specific security responsibilities
    - Include authentication testing procedures
    - Add examples for common vulnerability patterns
    """
)

print(f"Skill refined: v{refined.skill.version}")
print(f"Iterations: {refined.iterations}")
```

### 6. Expand Specific Section
```python
# Expand the examples section
expanded = await generator.expand(
    skill=skill,
    section="examples"
)

# Expand the procedures section
expanded = await generator.expand(
    skill=skill,
    section="procedures"
)

print("Section expanded with additional content")
```

### 7. Generate with Constraints
```python
request = GenerationRequest(
    name="constrained-skill",
    description="A developer skill with specific constraints",
    category="development",
    constraints={
        "max_responsibilities": 5,
        "require_examples": True,
        "max_tools": 10,
        "include_constraints": True,
        "target_tokens": 2000
    }
)

result = await generator.generate(request)
```

### 8. Batch Generation
```python
requests = [
    GenerationRequest(name="frontend-dev", description="React frontend expert", category="development"),
    GenerationRequest(name="backend-dev", description="Python backend expert", category="development"),
    GenerationRequest(name="devops-eng", description="Kubernetes DevOps", category="operations"),
]

results = []
for request in requests:
    result = await generator.generate(request)
    results.append({
        "name": result.skill.name,
        "valid": result.validation.valid,
        "tokens": result.tokens_used
    })

print(f"Generated {len(results)} skills")
total_tokens = sum(r["tokens"] for r in results)
print(f"Total tokens: {total_tokens}")
```

### 9. Handle Generation Errors
```python
try:
    result = await generator.generate(request)

    if not result.validation.valid:
        print("Generated skill has validation issues:")
        for issue in result.validation.issues:
            print(f"  {issue.message}")

        # Try refinement
        refined = await generator.refine(result.skill, "Fix validation issues")
        if refined.validation.valid:
            print("Refinement fixed the issues")

except GenerationError as e:
    print(f"Generation failed: {e.message}")
    print(f"Retries attempted: {e.retries}")
```

### 10. Get Generation Statistics
```python
stats = generator.get_stats()

print(f"Generation Statistics:")
print(f"  Total generations: {stats['total_generations']}")
print(f"  Successful: {stats['successful']}")
print(f"  Failed: {stats['failed']}")
print(f"  Total tokens: {stats['total_tokens']}")
print(f"  Avg tokens/skill: {stats['avg_tokens']:.0f}")
print(f"  Avg time: {stats['avg_time_ms']:.0f}ms")
print(f"  Template usage:")
for template, count in stats['template_usage'].items():
    print(f"    {template}: {count}")
```

## Service Interactions

```
+------------------+
|  SkillGenerator  | <--- L14 Skill Library Layer
|      (L14)       |
+--------+---------+
         |
   Uses:
         |
+--------+--------+
|        |        |
v        v        v
L04      Skill    Templates
Gateway  Validator
(LLM)    (L14)
```

**Integration Points:**
- **ModelGateway (L04)**: LLM inference for generation
- **SkillValidator (L14)**: Validates generated skills
- **SkillStore (L14)**: Stores generated skills

## LLM Prompt Structure

```
System Prompt:
You are a skill definition generator. Create comprehensive skill
definitions in YAML format that include:

1. metadata: name, description, version
2. role: clear role identity
3. responsibilities: specific, actionable responsibilities
4. tools: relevant tools for the role
5. procedures: step-by-step procedures (optional)
6. examples: input/output examples (optional)
7. constraints: behavioral constraints (optional)

Output valid YAML that can be parsed. Be specific and actionable.

User Prompt:
Generate a skill definition for: {description}

Name: {name}
Category: {category}
Requirements:
- {requirement_1}
- {requirement_2}
...

Constraints:
{constraints}

Output the skill definition in YAML format.
```

## Templates

### Developer Template
```yaml
metadata:
  name: {name}
  description: {specialty} developer using {language}
  version: 1.0.0

role: {language} Developer

responsibilities:
  - Write clean, maintainable {language} code
  - Implement features using {framework}
  - Write comprehensive tests
  - Follow coding standards and best practices
  - Document code and APIs

tools: {tools}

procedures:
  - name: Implement Feature
    steps:
      - Understand requirements
      - Design solution
      - Write implementation
      - Add tests
      - Submit for review

constraints:
  - Follow {language} best practices
  - Maintain test coverage above 80%
```

### Reviewer Template
```yaml
metadata:
  name: {name}
  description: Code review specialist
  version: 1.0.0

role: Code Reviewer

responsibilities:
  - Review code changes for quality
  - Identify bugs and issues
  - Suggest improvements
  - Ensure standards compliance

tools:
  - {vcs_platform}
  - code analysis tools

constraints:
  - Be constructive in feedback
  - Focus on code, not author
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E14101 | Generation failed | Yes |
| E14102 | Invalid request | No |
| E14103 | Template not found | No |
| E14104 | LLM error | Yes |
| E14105 | Parse error | Yes |
| E14106 | Validation failed | Yes |

## Execution Examples

```python
# Complete generation workflow
from L14_skill_library.services.skill_generator import SkillGenerator
from L14_skill_library.services.skill_store import SkillStore
from L14_skill_library.services.skill_validator import SkillValidator
from L14_skill_library.models import GenerationRequest
from L04_model_gateway.services.model_gateway import ModelGateway

# Initialize
gateway = ModelGateway()
validator = SkillValidator()
store = SkillStore()
generator = SkillGenerator(
    gateway_client=gateway,
    auto_validate=True
)

# 1. Generate from description
print("Generating skill from description...")
request = GenerationRequest(
    name="api-developer",
    description="""
    An API developer who specializes in designing and implementing
    RESTful APIs. Should understand REST principles, OpenAPI specs,
    authentication, rate limiting, and API versioning.
    """,
    category="development",
    requirements=[
        "REST API design principles",
        "OpenAPI/Swagger specification",
        "OAuth2 authentication",
        "Rate limiting strategies",
        "API versioning patterns"
    ]
)

result = await generator.generate(request)

print(f"\nGeneration result:")
print(f"  Name: {result.skill.name}")
print(f"  Valid: {result.validation.valid}")
print(f"  Tokens: {result.tokens_used}")
print(f"  Time: {result.generation_time_ms}ms")

if result.validation.valid:
    # Store the skill
    created = await store.create(result.skill)
    print(f"  Stored: {created.skill_id}")
else:
    print(f"  Validation issues: {result.validation.errors}")

# 2. Generate from template
print("\n\nGenerating from template...")
template_result = await generator.generate_from_template(
    template="developer",
    params={
        "name": "typescript-frontend-dev",
        "language": "TypeScript",
        "framework": "React",
        "specialty": "Frontend UI",
        "tools": ["jest", "eslint", "prettier", "storybook"]
    }
)

print(f"Template result:")
print(f"  Name: {template_result.skill.name}")
print(f"  Valid: {template_result.validation.valid}")

# 3. Refine a skill
print("\n\nRefining skill...")
refined = await generator.refine(
    skill=result.skill,
    feedback="""
    - Add GraphQL API support
    - Include error handling procedures
    - Add more examples for pagination
    """
)

print(f"Refinement result:")
print(f"  Iterations: {refined.iterations}")
print(f"  Valid: {refined.validation.valid}")

# 4. Expand examples
print("\n\nExpanding examples section...")
expanded = await generator.expand(
    skill=result.skill,
    section="examples"
)

print(f"Expansion added more examples")

# 5. List templates
print("\n\nAvailable templates:")
templates = generator.get_templates()
for name, info in templates.items():
    print(f"  {name}: {info['description']}")

# 6. Statistics
print("\n\nGeneration Statistics:")
stats = generator.get_stats()
print(f"  Total: {stats['total_generations']}")
print(f"  Success rate: {stats['successful'] / max(1, stats['total_generations']):.1%}")
print(f"  Avg tokens: {stats['avg_tokens']:.0f}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| SkillGenerator class | Complete |
| generate() | Complete |
| generate_from_template() | Complete |
| refine() | Complete |
| expand() | Complete |
| get_templates() | Complete |
| L04 integration | Complete |
| Validation integration | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Streaming generation | Medium | Stream skill as it generates |
| Template CRUD | Medium | User-defined templates |
| Fine-tuning | Low | Train on existing skills |
| Multi-language | Low | Non-English skill generation |
| Cost estimation | Low | Estimate tokens before generating |

## Strengths

- **LLM-powered** - Intelligent skill creation
- **Template support** - Quick generation from templates
- **Validation integration** - Automatic validation
- **Refinement** - Iterative improvement
- **Section expansion** - Targeted content expansion
- **Statistics** - Track generation metrics

## Weaknesses

- **LLM dependency** - Requires L04 gateway
- **Token costs** - Each generation uses tokens
- **No streaming** - Full generation only
- **Fixed templates** - Can't add custom templates
- **English-only** - Generates English content
- **Latency** - LLM calls add latency

## Best Practices

### Detailed Descriptions
Provide detailed descriptions for better results:
```python
# Good: Detailed with requirements
GenerationRequest(
    name="security-expert",
    description="Security specialist for code auditing with OWASP expertise",
    requirements=[
        "OWASP Top 10 knowledge",
        "Secure coding practices",
        "Authentication review",
        "SQL injection detection"
    ]
)

# Avoid: Vague description
GenerationRequest(
    name="security-expert",
    description="Security person"  # Too vague
)
```

### Use Templates When Possible
Templates are faster and more consistent:
```python
# Good: Use template for common roles
await generator.generate_from_template("developer", params)

# Reserve generate() for unique roles
await generator.generate(unique_request)
```

### Validate and Refine
Always validate and refine if needed:
```python
result = await generator.generate(request)

if not result.validation.valid:
    # Refine with validation feedback
    feedback = "\n".join([i.message for i in result.validation.issues])
    refined = await generator.refine(result.skill, f"Fix: {feedback}")
```

## Source Files

- Service: `platform/src/L14_skill_library/services/skill_generator.py`
- Templates: `platform/src/L14_skill_library/templates/`
- Models: `platform/src/L14_skill_library/models/`
- Spec: L14 Skill Library Layer specification

## Related Services

- ModelGateway (L04) - LLM inference
- SkillValidator (L14) - Validates generated skills
- SkillStore (L14) - Stores skills
- SkillOptimizer (L14) - Optimizes skills

---
*Generated: 2026-01-24 | Platform Services Documentation*
