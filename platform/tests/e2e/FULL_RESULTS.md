============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 120.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 66 items

tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l04_l05_integration FAILED [  1%]
tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l02_l03_integration FAILED [  3%]
tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l05_l06_integration FAILED [  4%]
tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l02_mcp_integration PASSED [  6%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_l05_invalid_goal_handling FAILED [  7%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_l04_invalid_request_handling PASSED [  9%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_l06_malformed_event_handling PASSED [ 10%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_layer_cleanup_idempotent FAILED [ 12%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_layer_double_initialization FAILED [ 13%]
tests/e2e/test_full_pipeline.py::TestFullPipeline::test_goal_to_evaluation_pipeline FAILED [ 15%]
tests/e2e/test_full_pipeline.py::TestFullPipeline::test_multi_task_plan_execution FAILED [ 16%]
tests/e2e/test_full_pipeline.py::TestFullPipeline::test_all_layers_concurrent FAILED [ 18%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_executor_initialization PASSED [ 19%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_bridge_connection PASSED [ 21%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_bridge_connection PASSED [ 22%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_save_snapshot PASSED [ 24%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_get_context PASSED [ 25%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_query PASSED [ 27%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_find_source PASSED [ 28%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_registry_initialization ERROR [ 30%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_executor_initialization ERROR [ 31%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_list_available_tools ERROR [ 33%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_get_tool_by_name ERROR [ 34%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_execute_mock_tool ERROR [ 36%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_gateway_initialization PASSED [ 37%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_registry_initialization PASSED [ 39%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_router_initialization PASSED [ 40%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_list_available_models PASSED [ 42%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_ollama_provider_health PASSED [ 43%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_simple_completion PASSED [ 45%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_semantic_cache PASSED [ 46%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_rate_limiter PASSED [ 48%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_planning_service_initialization ERROR [ 50%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_goal_decomposer_initialization ERROR [ 51%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_create_simple_plan ERROR [ 53%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_plan_has_tasks ERROR [ 54%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_dependency_cycle_detection FAILED [ 56%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_topological_sort FAILED [ 57%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_plan_validation ERROR [ 59%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_goal_decomposition_with_llm ERROR [ 60%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_evaluation_service_initialization PASSED [ 62%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_scorer_initialization PASSED [ 63%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_engine_initialization PASSED [ 65%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_engine_initialization ERROR [ 65%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_process_cloud_event PASSED [ 66%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_score_computation PASSED [ 68%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_dimensions PASSED [ 69%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_dimension_weights_sum_to_one PASSED [ 71%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_ingestion PASSED [ 72%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_ingestion ERROR [ 72%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_query PASSED [ 74%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_query ERROR [ 74%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_anomaly_detection PASSED [ 75%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l02_runtime_imports PASSED [ 77%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l02_runtime_initializes PASSED [ 78%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l03_tools_imports FAILED [ 80%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l03_tools_initializes FAILED [ 81%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l04_gateway_imports PASSED [ 83%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l04_gateway_initializes PASSED [ 84%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l05_planning_imports FAILED [ 86%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l05_planning_initializes FAILED [ 87%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l06_evaluation_imports PASSED [ 89%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l06_evaluation_initializes PASSED [ 90%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_all_layers_initialize_together FAILED [ 92%]
tests/e2e/test_performance.py::TestPerformance::test_layer_initialization_time FAILED [ 93%]
tests/e2e/test_performance.py::TestPerformance::test_plan_creation_latency FAILED [ 95%]
tests/e2e/test_performance.py::TestPerformance::test_concurrent_plan_creation FAILED [ 96%]
tests/e2e/test_performance.py::TestPerformance::test_event_processing_throughput PASSED [ 98%]
tests/e2e/test_performance.py::TestPerformance::test_llm_completion_latency PASSED [100%]

==================================== ERRORS ====================================
_____ ERROR at setup of TestL03ToolExecution.test_registry_initialization ______

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l03_tools.TestL03ToolExecution object at 0x10fc3fc50>

    @pytest.fixture
    async def tool_registry(self):
        """Initialize tool registry."""
>       from src.L03_tool_execution.services.tool_registry import ToolRegistry

tests/e2e/test_l03_tools.py:22: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_____ ERROR at setup of TestL03ToolExecution.test_executor_initialization ______

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l03_tools.TestL03ToolExecution object at 0x10fc3fd90>

    @pytest.fixture
    async def tool_executor(self):
        """Initialize tool executor."""
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_l03_tools.py:10: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_______ ERROR at setup of TestL03ToolExecution.test_list_available_tools _______

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l03_tools.TestL03ToolExecution object at 0x10fcd8770>

    @pytest.fixture
    async def tool_registry(self):
        """Initialize tool registry."""
>       from src.L03_tool_execution.services.tool_registry import ToolRegistry

tests/e2e/test_l03_tools.py:22: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_________ ERROR at setup of TestL03ToolExecution.test_get_tool_by_name _________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l03_tools.TestL03ToolExecution object at 0x10fcd88a0>

    @pytest.fixture
    async def tool_registry(self):
        """Initialize tool registry."""
>       from src.L03_tool_execution.services.tool_registry import ToolRegistry

tests/e2e/test_l03_tools.py:22: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
________ ERROR at setup of TestL03ToolExecution.test_execute_mock_tool _________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l03_tools.TestL03ToolExecution object at 0x10fc228d0>

    @pytest.fixture
    async def tool_executor(self):
        """Initialize tool executor."""
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_l03_tools.py:10: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
____ ERROR at setup of TestL05Planning.test_planning_service_initialization ____

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fd04190>

    @pytest.fixture
    async def planning_service(self):
        """Initialize planning service."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_l05_planning.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
____ ERROR at setup of TestL05Planning.test_goal_decomposer_initialization _____

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fd042d0>

    @pytest.fixture
    async def goal_decomposer(self):
        """Initialize goal decomposer."""
        from src.L05_planning.services.goal_decomposer import GoalDecomposer
        decomposer = GoalDecomposer()
>       await decomposer.initialize()
              ^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: 'GoalDecomposer' object has no attribute 'initialize'

tests/e2e/test_l05_planning.py:22: AttributeError
__________ ERROR at setup of TestL05Planning.test_create_simple_plan ___________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fcd8c30>

    @pytest.fixture
    async def planning_service(self):
        """Initialize planning service."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_l05_planning.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
____________ ERROR at setup of TestL05Planning.test_plan_has_tasks _____________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fcd8d60>

    @pytest.fixture
    async def planning_service(self):
        """Initialize planning service."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_l05_planning.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
____________ ERROR at setup of TestL05Planning.test_plan_validation ____________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fcfc7c0>

    @pytest.fixture
    async def planning_service(self):
        """Initialize planning service."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_l05_planning.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______ ERROR at setup of TestL05Planning.test_goal_decomposition_with_llm ______

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fc83d50>

    @pytest.fixture
    async def planning_service(self):
        """Initialize planning service."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_l05_planning.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
__ ERROR at teardown of TestL06Evaluation.test_metrics_engine_initialization ___

self = <e2e.test_l06_evaluation.TestL06Evaluation object at 0x10fcd8e90>

    @pytest.fixture
    async def metrics_engine(self):
        """Initialize metrics engine."""
        from src.L06_evaluation.services.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        await engine.initialize()
        yield engine
>       await engine.cleanup()

tests/e2e/test_l06_evaluation.py:34: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.L06_evaluation.services.metrics_engine.MetricsEngine object at 0x11212dcd0>

    async def cleanup(self):
        """Cleanup metrics engine resources."""
        # Flush remaining metrics
>       await self._flush()
              ^^^^^^^^^^^
E       AttributeError: 'MetricsEngine' object has no attribute '_flush'

src/L06_evaluation/services/metrics_engine.py:106: AttributeError
________ ERROR at teardown of TestL06Evaluation.test_metrics_ingestion _________

self = <e2e.test_l06_evaluation.TestL06Evaluation object at 0x110320650>

    @pytest.fixture
    async def metrics_engine(self):
        """Initialize metrics engine."""
        from src.L06_evaluation.services.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        await engine.initialize()
        yield engine
>       await engine.cleanup()

tests/e2e/test_l06_evaluation.py:34: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.L06_evaluation.services.metrics_engine.MetricsEngine object at 0x11212c9d0>

    async def cleanup(self):
        """Cleanup metrics engine resources."""
        # Flush remaining metrics
>       await self._flush()
              ^^^^^^^^^^^
E       AttributeError: 'MetricsEngine' object has no attribute '_flush'

src/L06_evaluation/services/metrics_engine.py:106: AttributeError
------------------------------ Captured log call -------------------------------
WARNING  src.L06_evaluation.services.storage_manager:storage_manager.py:100 Redis client not available, skipping hot storage
ERROR    src.L06_evaluation.services.storage_manager:storage_manager.py:83 Metric write failed: Hot storage write failed
__________ ERROR at teardown of TestL06Evaluation.test_metrics_query ___________

self = <e2e.test_l06_evaluation.TestL06Evaluation object at 0x110320850>

    @pytest.fixture
    async def metrics_engine(self):
        """Initialize metrics engine."""
        from src.L06_evaluation.services.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        await engine.initialize()
        yield engine
>       await engine.cleanup()

tests/e2e/test_l06_evaluation.py:34: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.L06_evaluation.services.metrics_engine.MetricsEngine object at 0x11212e3f0>

    async def cleanup(self):
        """Cleanup metrics engine resources."""
        # Flush remaining metrics
>       await self._flush()
              ^^^^^^^^^^^
E       AttributeError: 'MetricsEngine' object has no attribute '_flush'

src/L06_evaluation/services/metrics_engine.py:106: AttributeError
------------------------------ Captured log call -------------------------------
ERROR    src.L06_evaluation.services.metrics_engine:metrics_engine.py:307 Metric query failed: can't compare offset-naive and offset-aware datetimes
=================================== FAILURES ===================================
______________ TestCrossLayerIntegration.test_l04_l05_integration ______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_cross_layer_integration.TestCrossLayerIntegration object at 0x10fc3e850>

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l04_l05_integration(self):
        """L05 Planning uses L04 Model Gateway for decomposition."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_cross_layer_integration.py:14: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______________ TestCrossLayerIntegration.test_l02_l03_integration ______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_cross_layer_integration.TestCrossLayerIntegration object at 0x10fc3ed50>

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l02_l03_integration(self):
        """L02 Agent Runtime uses L03 Tool Execution."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_cross_layer_integration.py:43: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______________ TestCrossLayerIntegration.test_l05_l06_integration ______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_cross_layer_integration.TestCrossLayerIntegration object at 0x10fbfb490>

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l05_l06_integration(self):
        """L06 Evaluation can evaluate L05 plans."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_cross_layer_integration.py:66: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_______________ TestErrorHandling.test_l05_invalid_goal_handling _______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_error_handling.TestErrorHandling object at 0x10fc3ec10>

    @pytest.mark.asyncio
    async def test_l05_invalid_goal_handling(self):
        """L05 handles invalid goal gracefully."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_error_handling.py:11: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_______________ TestErrorHandling.test_layer_cleanup_idempotent ________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_error_handling.TestErrorHandling object at 0x10fbfba80>

    @pytest.mark.asyncio
    async def test_layer_cleanup_idempotent(self):
        """Layer cleanup can be called multiple times safely."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_error_handling.py:104: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______________ TestErrorHandling.test_layer_double_initialization ______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_error_handling.TestErrorHandling object at 0x10fc22570>

    @pytest.mark.asyncio
    async def test_layer_double_initialization(self):
        """Layer handles double initialization gracefully."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_error_handling.py:117: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______________ TestFullPipeline.test_goal_to_evaluation_pipeline _______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_full_pipeline.TestFullPipeline object at 0x10fc3f750>

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_goal_to_evaluation_pipeline(self):
        """Test complete flow: Goal -> Plan -> Execute -> Evaluate."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_full_pipeline.py:15: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_______________ TestFullPipeline.test_multi_task_plan_execution ________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_full_pipeline.TestFullPipeline object at 0x10fc3f890>

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_task_plan_execution(self):
        """Test plan with multiple dependent tasks."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_full_pipeline.py:101: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_________________ TestFullPipeline.test_all_layers_concurrent __________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_full_pipeline.TestFullPipeline object at 0x10fcd83e0>

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_all_layers_concurrent(self):
        """Test all layers running concurrently."""
        import asyncio
        from src.L02_runtime.services.agent_executor import AgentExecutor
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_full_pipeline.py:134: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_______________ TestL05Planning.test_dependency_cycle_detection ________________

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fc23650>
dependency_resolver = <src.L05_planning.services.dependency_resolver.DependencyResolver object at 0x111b08ec0>

    @pytest.mark.asyncio
    async def test_dependency_cycle_detection(self, dependency_resolver):
        """Dependency resolver detects cycles."""
        from src.L05_planning.models.task import Task, TaskDependency
    
        # Create tasks with circular dependency
>       task_a = Task(task_id="a", name="Task A", dependencies=[
            TaskDependency(task_id="b", dependency_type="blocking")
        ])
E       TypeError: Task.__init__() missing 2 required positional arguments: 'plan_id' and 'description'

tests/e2e/test_l05_planning.py:80: TypeError
____________________ TestL05Planning.test_topological_sort _____________________

self = <e2e.test_l05_planning.TestL05Planning object at 0x10fcfc6b0>
dependency_resolver = <src.L05_planning.services.dependency_resolver.DependencyResolver object at 0x111ad79d0>

    @pytest.mark.asyncio
    async def test_topological_sort(self, dependency_resolver):
        """Dependency resolver produces valid topological order."""
        from src.L05_planning.models.task import Task, TaskDependency
    
        # Create tasks with valid dependencies: A -> B -> C
>       task_a = Task(task_id="a", name="Task A", dependencies=[])
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: Task.__init__() missing 2 required positional arguments: 'plan_id' and 'description'

tests/e2e/test_l05_planning.py:96: TypeError
________________ TestLayerInitialization.test_l03_tools_imports ________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_layer_initialization.TestLayerInitialization object at 0x10fcd90f0>

    @pytest.mark.asyncio
    async def test_l03_tools_imports(self):
        """L03 Tool Execution imports successfully."""
>       from src.L03_tool_execution import __init__

tests/e2e/test_layer_initialization.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______________ TestLayerInitialization.test_l03_tools_initializes ______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_layer_initialization.TestLayerInitialization object at 0x10fcd9220>

    @pytest.mark.asyncio
    async def test_l03_tools_initializes(self):
        """L03 Tool Execution initializes without error."""
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_layer_initialization.py:39: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
______________ TestLayerInitialization.test_l05_planning_imports _______________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_layer_initialization.TestLayerInitialization object at 0x10fcfcd10>

    @pytest.mark.asyncio
    async def test_l05_planning_imports(self):
        """L05 Planning imports successfully."""
        from src.L05_planning import __init__
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_layer_initialization.py:71: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
____________ TestLayerInitialization.test_l05_planning_initializes _____________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_layer_initialization.TestLayerInitialization object at 0x110321250>

    @pytest.mark.asyncio
    async def test_l05_planning_initializes(self):
        """L05 Planning initializes without error."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_layer_initialization.py:81: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
_________ TestLayerInitialization.test_all_layers_initialize_together __________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_layer_initialization.TestLayerInitialization object at 0x110331130>

    @pytest.mark.asyncio
    async def test_all_layers_initialize_together(self):
        """All layers can be initialized simultaneously."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_layer_initialization.py:111: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
________________ TestPerformance.test_layer_initialization_time ________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_performance.TestPerformance object at 0x10fd04b90>

    @pytest.mark.asyncio
    async def test_layer_initialization_time(self):
        """All layers initialize within acceptable time."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
>       from src.L03_tool_execution.services.tool_executor import ToolExecutor

tests/e2e/test_performance.py:14: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
__________________ TestPerformance.test_plan_creation_latency __________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_performance.TestPerformance object at 0x10fd04f50>

    @pytest.mark.asyncio
    async def test_plan_creation_latency(self):
        """Plan creation completes within acceptable time."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_performance.py:66: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
________________ TestPerformance.test_concurrent_plan_creation _________________

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
>       from psycopg_pool import AsyncConnectionPool
E       ModuleNotFoundError: No module named 'psycopg_pool'

src/L03_tool_execution/services/tool_registry.py:21: ModuleNotFoundError

During handling of the above exception, another exception occurred:

self = <e2e.test_performance.TestPerformance object at 0x10fcd95b0>

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_plan_creation(self):
        """Multiple plans can be created concurrently."""
>       from src.L05_planning.services.planning_service import PlanningService

tests/e2e/test_performance.py:97: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """L05 Planning Layer - Services."""
    
    from .goal_decomposer import GoalDecomposer
    from .plan_cache import PlanCache
    from .dependency_resolver import DependencyResolver, DependencyGraph
    from .task_orchestrator import TaskOrchestrator, TaskResult
    from .context_injector import ContextInjector
    from .resource_estimator import ResourceEstimator
    from .plan_validator import PlanValidator, ValidationResult, ValidationError
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor, ExecutionEvent
>   from .planning_service import PlanningService

src/L05_planning/services/__init__.py:12: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L05 Planning Layer - Main Planning Service.
    
    Main orchestrator that coordinates all planning components:
    - Goal decomposition
    - Dependency resolution
    - Plan validation
    - Task orchestration
    - Execution monitoring
    """
    
    import logging
    from typing import Optional, Dict, Any
    from uuid import uuid4
    
    from ..models import (
        Goal,
        GoalStatus,
        ExecutionPlan,
        PlanStatus,
        PlanningError,
        ErrorCode,
    )
    from .goal_decomposer import GoalDecomposer
    from .dependency_resolver import DependencyResolver
    from .plan_validator import PlanValidator
    from .resource_estimator import ResourceEstimator
    from .context_injector import ContextInjector
    from .task_orchestrator import TaskOrchestrator
    from .agent_assigner import AgentAssigner
    from .execution_monitor import ExecutionMonitor
    from .plan_cache import PlanCache
    
    # Cross-layer imports
    from src.L04_model_gateway.services.model_gateway import ModelGateway
    from src.L02_runtime.services.agent_executor import AgentExecutor
>   from src.L03_tool_execution.services.tool_executor import ToolExecutor

src/L05_planning/services/planning_service.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Layer
    
    This module provides secure, isolated execution of tools invoked by AI agents.
    Based on tool-execution-layer-specification-v1.2-ASCII.md
    
    Key Features:
    - Tool registry with semantic search (pgvector)
    - Nested sandbox execution (BC-1)
    - Permission enforcement (JWT + OPA)
    - External API management with circuit breakers
    - MCP integration for documents (Phase 15) and checkpoints (Phase 16)
    - Comprehensive observability and audit logging
    """
    
    from .models import (
        ToolDefinition,
        ToolVersion,
        ToolManifest,
        ToolResult,
        ToolInvokeRequest,
        ToolInvokeResponse,
        ExecutionContext,
        ResourceLimits,
        SandboxConfig,
        Checkpoint,
        CheckpointConfig,
    )
    
>   from .services import (
        ToolRegistry,
        ToolExecutor,
        ToolSandbox,
        ResultCache,
        MCPToolBridge,
        ToolComposer,
    )

src/L03_tool_execution/__init__.py:30: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    L03 Tool Execution Services
    
    This module provides services for tool execution, registry, caching, and MCP integration.
    """
    
>   from .tool_registry import ToolRegistry

src/L03_tool_execution/services/__init__.py:7: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """
    Tool Registry Service
    
    Maintains catalog of available tools with semantic search capabilities.
    Based on Section 3.3.1 of tool-execution-layer-specification-v1.2-ASCII.md
    
    Features:
    - Tool registration and versioning (Gap G-001, G-002)
    - Semantic search via pgvector + Ollama embeddings
    - Tool deprecation workflow (Gap G-003)
    - Protocol-agnostic interface (MCP, OpenAPI, LangChain, native)
    """
    
    import asyncio
    import logging
    from typing import List, Optional, Dict, Any, Tuple
    from datetime import datetime, timedelta
    import psycopg
    from psycopg.rows import dict_row
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        # Fallback for older psycopg versions
>       from psycopg import AsyncConnectionPool
E       ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?

src/L03_tool_execution/services/tool_registry.py:24: ImportError
=========================== short test summary info ============================
FAILED tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l04_l05_integration - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l02_l03_integration - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l05_l06_integration - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_error_handling.py::TestErrorHandling::test_l05_invalid_goal_handling - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_error_handling.py::TestErrorHandling::test_layer_cleanup_idempotent - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_error_handling.py::TestErrorHandling::test_layer_double_initialization - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_full_pipeline.py::TestFullPipeline::test_goal_to_evaluation_pipeline - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_full_pipeline.py::TestFullPipeline::test_multi_task_plan_execution - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_full_pipeline.py::TestFullPipeline::test_all_layers_concurrent - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_l05_planning.py::TestL05Planning::test_dependency_cycle_detection - TypeError: Task.__init__() missing 2 required positional arguments: 'plan_id' and 'description'
FAILED tests/e2e/test_l05_planning.py::TestL05Planning::test_topological_sort - TypeError: Task.__init__() missing 2 required positional arguments: 'plan_id' and 'description'
FAILED tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l03_tools_imports - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l03_tools_initializes - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l05_planning_imports - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l05_planning_initializes - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_all_layers_initialize_together - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_performance.py::TestPerformance::test_layer_initialization_time - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_performance.py::TestPerformance::test_plan_creation_latency - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
FAILED tests/e2e/test_performance.py::TestPerformance::test_concurrent_plan_creation - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_registry_initialization - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_executor_initialization - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_list_available_tools - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_get_tool_by_name - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_execute_mock_tool - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l05_planning.py::TestL05Planning::test_planning_service_initialization - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l05_planning.py::TestL05Planning::test_goal_decomposer_initialization - AttributeError: 'GoalDecomposer' object has no attribute 'initialize'
ERROR tests/e2e/test_l05_planning.py::TestL05Planning::test_create_simple_plan - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l05_planning.py::TestL05Planning::test_plan_has_tasks - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l05_planning.py::TestL05Planning::test_plan_validation - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l05_planning.py::TestL05Planning::test_goal_decomposition_with_llm - ImportError: cannot import name 'AsyncConnectionPool' from 'psycopg' (/usr/local/lib/python3.14/site-packages/psycopg/__init__.py). Did you mean: 'AsyncConnection'?
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_engine_initialization - AttributeError: 'MetricsEngine' object has no attribute '_flush'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_ingestion - AttributeError: 'MetricsEngine' object has no attribute '_flush'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_query - AttributeError: 'MetricsEngine' object has no attribute '_flush'
============= 19 failed, 36 passed, 14 errors in 94.32s (0:01:34) ==============
