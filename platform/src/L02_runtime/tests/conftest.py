"""
Pytest configuration and fixtures for L02 runtime tests.

Provides:
- Timeout protection for all async tests
- Automatic cleanup of async resources
- Proper event loop management
"""

import pytest
import asyncio
import warnings
import signal


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring Docker"
    )
    config.addinivalue_line(
        "markers", "timeout: mark test with timeout"
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Add 30 second timeout per test using signal-based timeout."""
    # Default 30 second timeout per test
    def handler(signum, frame):
        raise TimeoutError(f"Test {item.name} exceeded timeout")

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(30)  # 30 second timeout

    yield

    signal.alarm(0)
    signal.signal(signal.SIGALRM, old_handler)


@pytest.fixture(scope="function")
def event_loop():
    """
    Create an event loop for each test.

    This ensures proper cleanup between tests and prevents
    event loop reuse issues.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Cleanup: Cancel all pending tasks
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Give tasks a moment to cancel
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass  # Ignore cleanup errors
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


@pytest.fixture(autouse=True)
def suppress_warnings():
    """Suppress common async cleanup warnings during tests."""
    warnings.filterwarnings("ignore", message=".*Task was destroyed but it is pending.*")
    warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")
    yield


@pytest.fixture(autouse=True)
def cleanup_timeout():
    """Force test cleanup to complete within timeout."""
    yield
    # Test cleanup will be handled by event_loop fixture


@pytest.fixture
def anyio_backend():
    return 'asyncio'


# Fixtures with proper cleanup for common test objects
@pytest.fixture
def state_manager(event_loop):
    """Create StateManager with automatic cleanup."""
    from ..services.state_manager import StateManager

    manager = StateManager(config={
        "checkpoint_backend": "postgresql",
        "hot_state_backend": "redis",
        "auto_checkpoint_interval_seconds": 60,
        "max_checkpoint_size_mb": 100,
        "checkpoint_compression": "gzip",
        "retention_days": 30,
        "postgresql_dsn": "postgresql://postgres:postgres@localhost:5432/agentic_platform",
        "redis_url": "redis://localhost:6379/0",
    })

    yield manager

    # Cleanup with timeout protection
    try:
        event_loop.run_until_complete(
            asyncio.wait_for(manager.cleanup(), timeout=2.0)
        )
    except (asyncio.TimeoutError, Exception):
        pass  # Ignore cleanup errors


@pytest.fixture
def session_bridge(event_loop):
    """Create SessionBridge with automatic cleanup."""
    from ..services.session_bridge import SessionBridge

    bridge = SessionBridge(config={
        "heartbeat_interval_seconds": 5,
        "enable_recovery_check": True,
        "mcp_timeout_seconds": 2,  # Short timeout for tests
    })

    yield bridge

    # Cleanup with timeout protection
    try:
        event_loop.run_until_complete(
            asyncio.wait_for(bridge.cleanup(), timeout=2.0)
        )
    except (asyncio.TimeoutError, Exception):
        pass  # Ignore cleanup errors


@pytest.fixture
def workflow_engine(event_loop):
    """Create WorkflowEngine with automatic cleanup."""
    from ..services.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(config={
        "max_graph_depth": 10,
        "max_parallel_branches": 5,
        "cycle_detection": True,
        "checkpoint_on_node_complete": False,
        "timeout_seconds": 30,
    })

    yield engine

    # Cleanup with timeout protection
    try:
        event_loop.run_until_complete(
            asyncio.wait_for(engine.cleanup(), timeout=2.0)
        )
    except (asyncio.TimeoutError, Exception):
        pass  # Ignore cleanup errors


@pytest.fixture
def document_bridge(event_loop):
    """Create DocumentBridge with automatic cleanup."""
    from ..services.document_bridge import DocumentBridge

    bridge = DocumentBridge(config={
        "default_confidence_threshold": 0.7,
        "max_sources": 5,
        "cache_ttl_seconds": 60,
        "verify_claims": True,
        "mcp_timeout_seconds": 2,  # Short timeout for tests
    })

    yield bridge

    # Cleanup with timeout protection
    try:
        event_loop.run_until_complete(
            asyncio.wait_for(bridge.cleanup(), timeout=2.0)
        )
    except (asyncio.TimeoutError, Exception):
        pass  # Ignore cleanup errors
