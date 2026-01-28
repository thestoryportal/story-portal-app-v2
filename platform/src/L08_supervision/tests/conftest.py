"""
L08 Supervision Layer - Test Fixtures

Shared fixtures for all L08 tests.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from ..models.config import SupervisionConfiguration
from ..models.domain import (
    PolicyDefinition,
    PolicyRule,
    PolicyVerdict,
    Constraint,
    ConstraintType,
    AuditEntry,
    EscalationWorkflow,
    EscalationStatus,
)
from ..services.policy_engine import PolicyEngine, PolicyExpressionEvaluator
from ..services.constraint_enforcer import ConstraintEnforcer
from ..services.anomaly_detector import AnomalyDetector
from ..services.escalation_orchestrator import EscalationOrchestrator
from ..services.audit_manager import AuditManager
from ..services.access_control import AccessControlManager
from ..services.compliance_monitor import ComplianceMonitor
from ..services.supervision_service import SupervisionService
from ..integration.vault_client import VaultClient
from ..integration.redis_client import RedisRateLimiter
from ..integration.l01_bridge import L08Bridge
from ..integration.l10_bridge import L10Bridge


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config() -> SupervisionConfiguration:
    """Test configuration for unit tests"""
    return SupervisionConfiguration(
        policy_cache_ttl_seconds=60,
        escalation_timeout_seconds=5,  # Short timeout for tests
        max_escalation_level=2,
        z_score_threshold=3.0,
        iqr_multiplier=1.5,
        min_baseline_samples=5,  # Lower for tests
        baseline_sample_size=50,
        require_mfa_for_admin=False,  # Disabled for tests
        require_mfa_for_approval=False,  # Disabled for tests
        allow_on_consensus_fail=True,
        vault_url=None,  # Use HMAC fallback
    )


@pytest.fixture
def mock_vault_client() -> VaultClient:
    """Mock vault client for testing"""
    client = VaultClient(dev_mode=True)
    return client


@pytest.fixture
def mock_redis_limiter() -> RedisRateLimiter:
    """Mock redis limiter for testing"""
    limiter = RedisRateLimiter(dev_mode=True)
    return limiter


@pytest.fixture
def mock_l01_bridge() -> L08Bridge:
    """Mock L01 bridge for testing"""
    bridge = L08Bridge(l01_base_url="http://localhost:8001")
    return bridge


@pytest.fixture
def mock_l10_bridge() -> L10Bridge:
    """Mock L10 bridge for testing"""
    bridge = L10Bridge(l10_base_url="http://localhost:8010")
    return bridge


@pytest.fixture
def expression_evaluator() -> PolicyExpressionEvaluator:
    """Expression evaluator for testing"""
    return PolicyExpressionEvaluator()


@pytest_asyncio.fixture
async def audit_manager(
    mock_vault_client: VaultClient,
    mock_l01_bridge: L08Bridge,
    test_config: SupervisionConfiguration
) -> AuditManager:
    """Audit manager for testing"""
    manager = AuditManager(
        vault_client=mock_vault_client,
        l01_bridge=mock_l01_bridge,
        config=test_config,
    )
    await manager.initialize()
    return manager


@pytest_asyncio.fixture
async def policy_engine(
    audit_manager: AuditManager,
    mock_l01_bridge: L08Bridge,
    test_config: SupervisionConfiguration
) -> PolicyEngine:
    """Policy engine for testing"""
    return PolicyEngine(
        audit_manager=audit_manager,
        l01_bridge=mock_l01_bridge,
        config=test_config,
    )


@pytest_asyncio.fixture
async def constraint_enforcer(
    mock_redis_limiter: RedisRateLimiter,
    mock_l01_bridge: L08Bridge,
    audit_manager: AuditManager,
    test_config: SupervisionConfiguration
) -> ConstraintEnforcer:
    """Constraint enforcer for testing"""
    return ConstraintEnforcer(
        redis_limiter=mock_redis_limiter,
        l01_bridge=mock_l01_bridge,
        audit_manager=audit_manager,
        config=test_config,
    )


@pytest_asyncio.fixture
async def anomaly_detector(
    mock_l01_bridge: L08Bridge,
    audit_manager: AuditManager,
    test_config: SupervisionConfiguration
) -> AnomalyDetector:
    """Anomaly detector for testing"""
    detector = AnomalyDetector(
        l01_bridge=mock_l01_bridge,
        audit_manager=audit_manager,
        config=test_config,
    )
    await detector.initialize()
    return detector


@pytest_asyncio.fixture
async def escalation_orchestrator(
    mock_l01_bridge: L08Bridge,
    mock_l10_bridge: L10Bridge,
    audit_manager: AuditManager,
    test_config: SupervisionConfiguration
) -> EscalationOrchestrator:
    """Escalation orchestrator for testing"""
    orchestrator = EscalationOrchestrator(
        l01_bridge=mock_l01_bridge,
        l10_bridge=mock_l10_bridge,
        audit_manager=audit_manager,
        config=test_config,
    )
    await orchestrator.initialize()
    return orchestrator


@pytest.fixture
def access_control(test_config: SupervisionConfiguration) -> AccessControlManager:
    """Access control manager for testing"""
    return AccessControlManager(config=test_config)


@pytest.fixture
def compliance_monitor(test_config: SupervisionConfiguration) -> ComplianceMonitor:
    """Compliance monitor for testing"""
    return ComplianceMonitor(config=test_config)


@pytest_asyncio.fixture
async def supervision_service(test_config: SupervisionConfiguration) -> AsyncGenerator[SupervisionService, None]:
    """Full supervision service for testing"""
    service = SupervisionService(config=test_config)
    await service.initialize()
    yield service
    await service.cleanup()


@pytest.fixture
def client():
    """Synchronous test client with lifespan support"""
    from fastapi.testclient import TestClient
    from ..main import app
    # Use context manager to trigger lifespan events (startup/shutdown)
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator:
    """Asynchronous test client"""
    from httpx import AsyncClient, ASGITransport
    from ..main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# Sample data fixtures

@pytest.fixture
def sample_policy() -> PolicyDefinition:
    """Sample policy for testing"""
    return PolicyDefinition(
        name="test_policy",
        description="Test policy for unit tests",
        rules=[
            PolicyRule(
                name="allow_read",
                condition="operation == 'read'",
                action=PolicyVerdict.ALLOW,
                priority=10,
            ),
            PolicyRule(
                name="deny_delete_sensitive",
                condition="operation == 'delete' and resource.sensitive == True",
                action=PolicyVerdict.DENY,
                priority=100,
            ),
            PolicyRule(
                name="escalate_write_pii",
                condition="operation == 'write' and resource.type == 'pii'",
                action=PolicyVerdict.ESCALATE,
                priority=50,
            ),
        ],
        active=True,
        metadata={"tags": ["test", "unit"]},
    )


@pytest.fixture
def sample_constraint() -> Constraint:
    """Sample rate limit constraint"""
    return Constraint(
        name="test_rate_limit",
        constraint_type=ConstraintType.RATE_LIMIT,
        limit=10,
        window_seconds=60,
        enabled=True,
    )


@pytest.fixture
def sample_audit_entry() -> AuditEntry:
    """Sample audit entry"""
    return AuditEntry(
        action="policy_evaluated",
        actor_id="agent_001",
        actor_type="agent",
        resource_type="policy_decision",
        resource_id="dec_001",
        details={"verdict": "ALLOW", "outcome": "success"},
    )


@pytest.fixture
def sample_escalation() -> EscalationWorkflow:
    """Sample escalation workflow"""
    return EscalationWorkflow(
        decision_id="dec_001",
        reason="High risk operation requires approval",
        context={"operation": "delete_user_data"},
        status=EscalationStatus.PENDING,
        escalation_level=1,
        approvers=["admin_001", "admin_002"],
    )


# Markers for test organization

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "l08: L08 Supervision Layer tests")
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (requires services)")
    config.addinivalue_line("markers", "slow: Slow tests (>30s)")
    config.addinivalue_line("markers", "performance: Performance tests")
