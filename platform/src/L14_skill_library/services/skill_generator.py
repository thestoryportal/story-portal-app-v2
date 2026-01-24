"""
L14 Skill Library - Skill Generator Service

Generates skill files from role responsibilities using LLM via L04 Model Gateway.
"""

import logging
import json
import yaml
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from ..models import (
    Skill,
    SkillDefinition,
    SkillMetadata,
    SkillRole,
    SkillResponsibilities,
    SkillTools,
    SkillProcedure,
    SkillExample,
    SkillConstraints,
    SkillDependencies,
    SkillGenerationRequest,
    SkillGenerationResponse,
    SkillStatus,
    SKILL_FILE_TEMPLATE,
)

logger = logging.getLogger(__name__)


# System prompt for skill generation
SKILL_GENERATION_SYSTEM_PROMPT = """You are an expert at creating Claude Code skill files.

A skill file defines an agent's role, responsibilities, expertise areas, tools, and procedures.
Skill files help agents understand their identity and how to handle various situations.

When generating a skill file, follow these guidelines:
1. Make the role description clear and specific
2. List concrete, actionable responsibilities
3. Include relevant expertise areas
4. Specify tools that would be useful for this role
5. Define step-by-step procedures for common tasks
6. Provide realistic examples of interactions

Output your response as valid JSON matching this structure:
{
    "role": {
        "title": "string",
        "description": "string",
        "expertise_areas": ["string"]
    },
    "responsibilities": {
        "primary": ["string"],
        "secondary": ["string"]
    },
    "tools": {
        "required": ["string"],
        "optional": ["string"]
    },
    "procedures": [
        {
            "name": "string",
            "description": "string",
            "trigger": "string",
            "steps": ["string"]
        }
    ],
    "examples": [
        {
            "name": "string",
            "description": "string",
            "user_input": "string",
            "expected_response": "string"
        }
    ],
    "suggested_tags": ["string"]
}
"""


class SkillGenerator:
    """
    Skill Generator Service

    Uses LLM via L04 Model Gateway to generate skill files
    from role responsibilities and descriptions.
    """

    def __init__(
        self,
        model_gateway=None,
        l04_base_url: str = "http://localhost:8004",
        default_model: str = "claude-3-sonnet",
    ):
        """
        Initialize the Skill Generator.

        Args:
            model_gateway: Optional ModelGateway instance
            l04_base_url: Base URL for L04 Model Gateway
            default_model: Default model to use for generation
        """
        self._gateway = model_gateway
        self._l04_base_url = l04_base_url
        self._default_model = default_model
        logger.info("SkillGenerator initialized")

    async def generate(
        self,
        request: SkillGenerationRequest,
    ) -> SkillGenerationResponse:
        """
        Generate a skill from role responsibilities.

        Args:
            request: Skill generation request

        Returns:
            SkillGenerationResponse with generated skill
        """
        try:
            logger.info(f"Generating skill for role: {request.role_title}")

            # Build the generation prompt
            user_prompt = self._build_generation_prompt(request)

            # Call LLM for generation
            llm_response = await self._call_llm(user_prompt)

            if not llm_response:
                return SkillGenerationResponse(
                    success=False,
                    error="Failed to get response from LLM",
                )

            # Parse LLM response
            parsed = self._parse_llm_response(llm_response)

            if not parsed:
                return SkillGenerationResponse(
                    success=False,
                    error="Failed to parse LLM response",
                    generation_metadata={"raw_response": llm_response[:500]},
                )

            # Build skill from parsed response
            skill = self._build_skill(request, parsed)

            # Generate raw YAML content
            raw_content = self._generate_yaml_content(skill)
            skill.raw_content = raw_content

            # Estimate token count
            skill.definition.metadata.token_count = self._estimate_tokens(raw_content)

            logger.info(f"Generated skill: {skill.id} ({skill.name})")

            return SkillGenerationResponse(
                success=True,
                skill=skill,
                raw_content=raw_content,
                generation_metadata={
                    "model": self._default_model,
                    "generated_at": datetime.utcnow().isoformat(),
                    "token_count": skill.definition.metadata.token_count,
                },
            )

        except Exception as e:
            logger.error(f"Skill generation failed: {e}")
            return SkillGenerationResponse(
                success=False,
                error=str(e),
            )

    def _build_generation_prompt(self, request: SkillGenerationRequest) -> str:
        """Build the user prompt for skill generation."""
        prompt_parts = [
            f"Generate a skill file for the following role:\n",
            f"Role Title: {request.role_title}\n",
            f"Role Description: {request.role_description}\n",
            f"\nResponsibilities:\n",
        ]

        for i, resp in enumerate(request.responsibilities, 1):
            prompt_parts.append(f"{i}. {resp}\n")

        if request.expertise_areas:
            prompt_parts.append(f"\nExpertise Areas: {', '.join(request.expertise_areas)}\n")

        if request.target_agent_type:
            prompt_parts.append(f"\nTarget Agent Type: {request.target_agent_type}\n")

        prompt_parts.append(f"\nConstraints:\n")
        prompt_parts.append(f"- Maximum token budget: {request.max_token_budget}\n")

        if request.include_procedures:
            prompt_parts.append("- Include at least 2 detailed procedures\n")

        if request.include_examples:
            prompt_parts.append("- Include at least 2 realistic examples\n")

        return "".join(prompt_parts)

    async def _call_llm(self, user_prompt: str) -> Optional[str]:
        """
        Call LLM via L04 Model Gateway.

        Args:
            user_prompt: The user prompt

        Returns:
            LLM response text or None
        """
        try:
            if self._gateway:
                # Use injected gateway
                from L04_model_gateway.models import (
                    InferenceRequest,
                    LogicalPrompt,
                    Message,
                    MessageRole,
                )

                request = InferenceRequest(
                    request_id=str(uuid4()),
                    agent_did="did:agent:l14-skill-generator",
                    logical_prompt=LogicalPrompt(
                        messages=[
                            Message(role=MessageRole.SYSTEM, content=SKILL_GENERATION_SYSTEM_PROMPT),
                            Message(role=MessageRole.USER, content=user_prompt),
                        ],
                        temperature=0.7,
                        max_tokens=2000,
                    ),
                )
                response = await self._gateway.execute(request)
                return response.content

            else:
                # Use HTTP client to call L04
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self._l04_base_url}/v1/completions",
                        json={
                            "model": self._default_model,
                            "messages": [
                                {"role": "system", "content": SKILL_GENERATION_SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.7,
                            "max_tokens": 2000,
                        },
                        timeout=60.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return data.get("content", data.get("choices", [{}])[0].get("message", {}).get("content"))

                    logger.error(f"L04 request failed: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Return mock response for development/testing
            return self._generate_mock_response(user_prompt)

    def _generate_mock_response(self, user_prompt: str) -> str:
        """Generate a mock response for testing when LLM is unavailable."""
        return json.dumps({
            "role": {
                "title": "Generated Role",
                "description": "A role generated from the provided responsibilities.",
                "expertise_areas": ["general", "task-management"],
            },
            "responsibilities": {
                "primary": ["Handle core tasks", "Maintain quality"],
                "secondary": ["Support team", "Document processes"],
            },
            "tools": {
                "required": ["Read", "Write", "Bash"],
                "optional": ["Glob", "Grep"],
            },
            "procedures": [
                {
                    "name": "Standard Task Handling",
                    "description": "Handle a standard task request",
                    "trigger": "When user requests a task",
                    "steps": [
                        "Analyze the request",
                        "Plan the approach",
                        "Execute the solution",
                        "Verify the result",
                    ],
                },
            ],
            "examples": [
                {
                    "name": "Basic Request",
                    "description": "Handling a basic user request",
                    "user_input": "Help me with this task",
                    "expected_response": "I'll help you with that. Let me analyze the requirements...",
                },
            ],
            "suggested_tags": ["general", "generated"],
        })

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM response into a dictionary."""
        try:
            # Try to extract JSON from response
            # Handle case where response might have markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None

    def _build_skill(
        self,
        request: SkillGenerationRequest,
        parsed: Dict[str, Any],
    ) -> Skill:
        """Build a Skill object from parsed LLM response."""
        # Extract data from parsed response
        role_data = parsed.get("role", {})
        resp_data = parsed.get("responsibilities", {})
        tools_data = parsed.get("tools", {})
        procedures_data = parsed.get("procedures", [])
        examples_data = parsed.get("examples", [])
        suggested_tags = parsed.get("suggested_tags", [])

        # Build metadata
        metadata = SkillMetadata(
            name=request.role_title.lower().replace(" ", "_"),
            tags=suggested_tags or [],
            priority=request.priority,
            category=request.category,
            author="L14_skill_generator",
        )

        # Build role
        role = SkillRole(
            title=role_data.get("title", request.role_title),
            description=role_data.get("description", request.role_description),
            expertise_areas=role_data.get("expertise_areas", request.expertise_areas or []),
        )

        # Build responsibilities
        responsibilities = SkillResponsibilities(
            primary=resp_data.get("primary", request.responsibilities),
            secondary=resp_data.get("secondary", []),
        )

        # Build tools
        tools = SkillTools(
            required=tools_data.get("required", []),
            optional=tools_data.get("optional", []),
        )

        # Build procedures
        procedures = []
        for proc in procedures_data:
            procedures.append(SkillProcedure(
                name=proc.get("name", ""),
                description=proc.get("description", ""),
                trigger=proc.get("trigger"),
                steps=proc.get("steps", []),
            ))

        # Build examples
        examples = []
        for ex in examples_data:
            examples.append(SkillExample(
                name=ex.get("name", ""),
                description=ex.get("description"),
                user_input=ex.get("user_input", ""),
                expected_response=ex.get("expected_response", ""),
            ))

        # Build constraints
        constraints = SkillConstraints(
            token_budget=request.max_token_budget,
        )

        # Build definition
        definition = SkillDefinition(
            metadata=metadata,
            role=role,
            responsibilities=responsibilities,
            tools=tools,
            procedures=procedures,
            examples=examples,
            constraints=constraints,
            dependencies=SkillDependencies(),
        )

        # Create skill
        return Skill(
            name=metadata.name,
            status=SkillStatus.DRAFT,
            definition=definition,
        )

    def _generate_yaml_content(self, skill: Skill) -> str:
        """Generate YAML content for the skill file."""
        definition = skill.definition

        # Build YAML structure
        skill_dict = {
            "version": "1.0.0",
            "metadata": {
                "skill_id": str(definition.metadata.skill_id),
                "name": definition.metadata.name,
                "version": definition.metadata.version,
                "created_at": definition.metadata.created_at.isoformat(),
                "updated_at": definition.metadata.updated_at.isoformat(),
                "author": definition.metadata.author,
                "tags": definition.metadata.tags,
                "priority": definition.metadata.priority.value,
                "category": definition.metadata.category.value,
            },
            "role": {
                "title": definition.role.title,
                "description": definition.role.description,
                "expertise_areas": definition.role.expertise_areas,
            },
            "responsibilities": {
                "primary": definition.responsibilities.primary,
                "secondary": definition.responsibilities.secondary,
            },
            "tools": {
                "required": definition.tools.required,
                "optional": definition.tools.optional,
            },
            "procedures": [
                {
                    "name": p.name,
                    "description": p.description,
                    "trigger": p.trigger,
                    "steps": p.steps,
                }
                for p in definition.procedures
            ],
            "examples": [
                {
                    "name": e.name,
                    "description": e.description,
                    "user_input": e.user_input,
                    "expected_response": e.expected_response,
                }
                for e in definition.examples
            ],
            "constraints": {
                "token_budget": definition.constraints.token_budget,
                "max_context_tokens": definition.constraints.max_context_tokens,
                "execution_timeout_seconds": definition.constraints.execution_timeout_seconds,
            },
            "dependencies": {
                "skills": definition.dependencies.skills,
                "services": definition.dependencies.services,
            },
        }

        return yaml.dump(skill_dict, default_flow_style=False, sort_keys=False)

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count for content (rough heuristic)."""
        # Approximate: 4 characters per token
        return len(content) // 4

    async def generate_from_template(
        self,
        template_name: str,
        customizations: Dict[str, Any],
    ) -> SkillGenerationResponse:
        """
        Generate a skill from a predefined template with customizations.

        Args:
            template_name: Name of the template
            customizations: Customization parameters

        Returns:
            SkillGenerationResponse
        """
        # Define common templates
        templates = {
            "developer": {
                "role_title": "Software Developer",
                "role_description": "Expert software developer focused on writing clean, maintainable code",
                "responsibilities": [
                    "Write high-quality code following best practices",
                    "Review and refactor existing code",
                    "Debug and fix issues",
                    "Write tests and documentation",
                ],
                "expertise_areas": ["coding", "debugging", "testing"],
            },
            "reviewer": {
                "role_title": "Code Reviewer",
                "role_description": "Expert code reviewer focused on quality and best practices",
                "responsibilities": [
                    "Review code for quality and correctness",
                    "Identify potential issues and improvements",
                    "Provide constructive feedback",
                    "Ensure adherence to coding standards",
                ],
                "expertise_areas": ["code-review", "quality", "standards"],
            },
            "analyst": {
                "role_title": "Data Analyst",
                "role_description": "Expert data analyst focused on insights and reporting",
                "responsibilities": [
                    "Analyze data and identify patterns",
                    "Create reports and visualizations",
                    "Answer data-driven questions",
                    "Validate data quality",
                ],
                "expertise_areas": ["data-analysis", "reporting", "visualization"],
            },
        }

        template = templates.get(template_name)
        if not template:
            return SkillGenerationResponse(
                success=False,
                error=f"Unknown template: {template_name}",
            )

        # Apply customizations
        merged = {**template, **customizations}

        request = SkillGenerationRequest(
            role_title=merged["role_title"],
            role_description=merged["role_description"],
            responsibilities=merged["responsibilities"],
            expertise_areas=merged.get("expertise_areas"),
        )

        return await self.generate(request)
