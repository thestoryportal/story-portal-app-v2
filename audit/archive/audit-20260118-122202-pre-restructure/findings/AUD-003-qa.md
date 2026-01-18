# QA/Test Coverage Audit
## Test Files
./platform/src/L02_runtime/tests/test_document_bridge.py
./platform/src/L02_runtime/tests/test_executor.py
./platform/src/L02_runtime/tests/test_fleet.py
./platform/src/L02_runtime/tests/test_health.py
./platform/src/L02_runtime/tests/test_integration_local.py
./platform/src/L02_runtime/tests/test_lifecycle_manager.py
./platform/src/L02_runtime/tests/test_models.py
./platform/src/L02_runtime/tests/test_resource_manager.py
./platform/src/L02_runtime/tests/test_sandbox_manager.py
./platform/src/L02_runtime/tests/test_state.py
./platform/src/L02_runtime/tests/test_workflow.py
./platform/src/L03_tool_execution/tests/test_cache.py
./platform/src/L03_tool_execution/tests/test_models.py
./platform/src/L03_tool_execution/tests/test_registry.py
./platform/src/L04_model_gateway/tests/test_models.py
./platform/src/L04_model_gateway/tests/test_registry.py
./platform/src/L04_model_gateway/tests/test_router.py
./platform/src/L04_model_gateway/tests/test_providers.py
./platform/src/L05_planning/tests/test_models.py
./platform/src/L05_planning/tests/test_integration.py
./platform/src/L06_evaluation/tests/test_models.py
./platform/src/L06_evaluation/tests/test_integration.py
./platform/src/L07_learning/tests/test_integration.py
./platform/src/L09_api_gateway/tests/test_errors.py
./platform/src/L09_api_gateway/tests/test_router.py
./platform/src/L09_api_gateway/tests/test_validator.py
./platform/src/L11_integration/tests/test_integration.py
./platform/src/L10_human_interface/tests/test_models.py
./platform/src/L10_human_interface/tests/test_control_service.py
./platform/src/L10_human_interface/tests/test_dashboard_service.py
./platform/src/L10_human_interface/tests/test_websocket_gateway.py
./platform/src/L10_human_interface/tests/test_integration.py
./platform/tests/e2e/test_layer_initialization.py
./platform/tests/e2e/test_l02_runtime.py
./platform/tests/e2e/test_l03_tools.py
./platform/tests/e2e/test_l04_gateway.py
./platform/tests/e2e/test_l05_planning.py
./platform/tests/e2e/test_l06_evaluation.py
./platform/tests/e2e/test_cross_layer_integration.py
./platform/tests/e2e/test_full_pipeline.py
./platform/tests/e2e/test_error_handling.py
./platform/tests/e2e/test_performance.py
./platform/tests/e2e/test_simple_workflow.py
./platform/tests/e2e/test_l07_learning.py
./platform/tests/e2e/test_l03_l01_bridge.py
./platform/tests/e2e/test_l04_l01_bridge.py
./platform/tests/e2e/test_l05_l01_bridge.py
./platform/tests/e2e/test_l06_l01_bridge.py
./platform/tests/e2e/test_l09_l01_bridge.py
./platform/tests/e2e/test_l10_l01_bridge.py
## Test Function Count
Found 45472 test functions
## pytest Configuration
# pytest configuration for Story Portal Platform V2

[pytest]
# Test discovery
testpaths = tests platform/src
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Output and reporting
addopts =
    # Verbose output
    --verbose
    --strict-markers
    --tb=short

    # Coverage reporting
    --cov=platform/src
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-report=xml:coverage.xml
    --cov-branch

    # Warnings
    --strict-config
    -W error::DeprecationWarning
    -W error::PendingDeprecationWarning

    # Performance
    --durations=10

    # Output formatting
    --color=yes
    --code-highlight=yes

# Markers for test categorization
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (require services)
    slow: Slow running tests (skip in CI unless specified)
    smoke: Smoke tests (quick validation of critical paths)
    e2e: End-to-end tests (full platform testing)

    # Layer-specific markers
    l01: Tests for L01 Data Layer
    l02: Tests for L02 Runtime Layer
    l03: Tests for L03 Tool Execution Layer
    l04: Tests for L04 Model Gateway Layer
    l05: Tests for L05 Planning Layer
    l06: Tests for L06 Evaluation Layer
    l07: Tests for L07 Learning Layer
    l09: Tests for L09 API Gateway
    l10: Tests for L10 Human Interface
    l11: Tests for L11 Integration Layer
    l12: Tests for L12 NL Interface

    # Component markers
    database: Database-related tests
    redis: Redis-related tests
    api: API endpoint tests
    auth: Authentication/authorization tests
    security: Security-related tests
    performance: Performance tests

    # Environment markers
    dev: Development environment only
    staging: Staging environment only
    prod: Production-safe tests

# Test collection
norecursedirs =
    .git
    .tox
    dist
    build
    *.egg
    __pycache__
    .pytest_cache
    .mypy_cache
    .venv
    venv
    node_modules
    htmlcov
    backups
    logs

# Coverage configuration
[coverage:run]
source = platform/src
omit =
    */tests/*
    */test_*.py
    */__init__.py
    */venv/*
    */.venv/*
    */migrations/*
    */alembic/*
branch = True
parallel = True

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
exclude_lines =
    # Standard exclusions
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod
    # Defensive programming
    pass
    # Debug code
    if DEBUG:
    if debug:

[coverage:html]
directory = htmlcov

[coverage:xml]
output = coverage.xml

# Tool-specific settings
[tool:pytest]
# Timeout for tests (prevent hanging)
timeout = 300
timeout_method = thread

# Asyncio configuration
asyncio_mode = auto

# Log configuration
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(name)s - %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

log_file = logs/pytest.log
log_file_level = DEBUG
log_file_format = %(asctime)s [%(levelname)8s] %(name)s - %(message)s
log_file_date_format = %Y-%m-%d %H:%M:%S

# Ignore warnings
filterwarnings =
    error
    ignore::UserWarning
    ignore::DeprecationWarning:pkg_resources
    ignore::PendingDeprecationWarning
    # Ignore specific warnings
    ignore:.*U.*mode is deprecated:DeprecationWarning
    ignore::pytest.PytestUnhandledCoroutineWarning

# Minimum coverage percentage (fail if below)
[coverage:report]
fail_under = 80

# xdist configuration (parallel testing)
# Uncomment to enable parallel execution
# addopts = -n auto

# Example test run commands:
#
# Run all tests:
#   pytest
#
# Run unit tests only:
#   pytest -m unit
#
# Run specific layer tests:
#   pytest -m l01
#
# Run with coverage:
#   pytest --cov
#
# Run excluding slow tests:
#   pytest -m "not slow"
#
# Run integration tests:
#   pytest -m integration
#
# Run tests in parallel (requires pytest-xdist):
#   pytest -n auto
#
# Run with verbose output:
#   pytest -vv
#
# Run specific test file:
#   pytest tests/test_l01_data_layer.py
#
# Run specific test function:
#   pytest tests/test_l01_data_layer.py::test_create_agent
#
# Run tests matching pattern:
#   pytest -k "test_api"
#
# Generate HTML coverage report:
#   pytest --cov --cov-report=html
#   open htmlcov/index.html
#
# Run smoke tests only:
#   pytest -m smoke
#
# Run all except e2e tests:
#   pytest -m "not e2e"
