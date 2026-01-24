"""
Test Configuration and Fixtures for L13 Role Management Tests.
"""

import pytest
from ..models import (
    TaskRequirements,
    RoleType,
    Role,
    RoleStatus,
    Skill,
    SkillLevel,
)


@pytest.fixture
def simple_task_requirements():
    """Simple task requirements for testing."""
    return TaskRequirements(
        task_description="Analyze the sales data and create a summary report",
        required_skills=["data analysis", "reporting"],
        keywords=["analyze", "report", "data"],
        complexity="medium",
        urgency="normal",
    )


@pytest.fixture
def human_task_requirements():
    """Task requirements that should favor human classification."""
    return TaskRequirements(
        task_description="Make a strategic decision about the company budget and negotiate with stakeholders",
        required_skills=["leadership", "negotiation", "strategy"],
        keywords=["decision", "budget", "strategic", "negotiate"],
        complexity="high",
        urgency="normal",
        department_hint="Executive",
    )


@pytest.fixture
def ai_task_requirements():
    """Task requirements that should favor AI classification."""
    return TaskRequirements(
        task_description="Process and transform the data batch, calculate statistics and generate automated reports",
        required_skills=["data processing", "automation", "calculation"],
        keywords=["process", "transform", "automate", "calculate", "batch"],
        complexity="low",
        urgency="high",
    )


@pytest.fixture
def hybrid_task_requirements():
    """Task requirements for hybrid classification."""
    return TaskRequirements(
        task_description="Analyze customer feedback to evaluate product design and propose improvements",
        required_skills=["analysis", "design", "communication"],
        keywords=["analyze", "evaluate", "design", "feedback"],
        complexity="medium",
        urgency="normal",
    )


@pytest.fixture
def sample_role():
    """Sample role for testing."""
    return Role(
        name="Senior Data Analyst",
        department="Analytics",
        description="Analyzes data and creates insights",
        role_type=RoleType.HYBRID,
        status=RoleStatus.ACTIVE,
        skills=[
            Skill(name="Python", level=SkillLevel.EXPERT),
            Skill(name="Data Analysis", level=SkillLevel.EXPERT),
            Skill(name="Reporting", level=SkillLevel.ADVANCED),
        ],
        responsibilities=["Analyze data", "Create reports", "Build dashboards"],
        token_budget=4000,
        priority=7,
    )
