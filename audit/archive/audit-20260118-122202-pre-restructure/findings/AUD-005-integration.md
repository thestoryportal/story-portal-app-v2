# Integration Audit
## Cross-Layer Imports
### L01 imports:
./platform/shared/clients/__init__.py:8:from .l01_client import L01Client
./platform/output/L02_runtime/runtime_context_bridge.py:30:            context_service: ContextService instance from L01_data
./platform/output/L05_planning/planning_context_retriever.py:31:            context_service: ContextService instance from L01_data
./platform/output/L05_planning/planning_context_retriever.py:32:            document_service: DocumentService instance from L01_data
./platform/src/L02_runtime/runtime.py:15:from .services import SandboxManager, LifecycleManager, L01Bridge
### L02 imports:
./platform/src/L03_tool_execution/models/execution_context.py:164:    Implements BC-1 nested sandbox context from L02.
./platform/src/L03_tool_execution/services/mcp_tool_bridge.py:29:# TODO: Replace direct imports with HTTP client for L02
./platform/src/L03_tool_execution/services/mcp_tool_bridge.py:31:# from ...L02_runtime.services.document_bridge import DocumentBridge
./platform/src/L03_tool_execution/services/mcp_tool_bridge.py:32:# from ...L02_runtime.services.session_bridge import SessionBridge
./platform/src/L04_model_gateway/models/error_codes.py:5:Following pattern from L02 (E2xxx) and L03 (E3xxx)
### L03 imports:
./platform/src/L04_model_gateway/models/error_codes.py:5:Following pattern from L02 (E2xxx) and L03 (E3xxx)
./platform/src/L05_planning/services/planning_service.py:38:from src.L03_tool_execution.services.tool_executor import ToolExecutor
./platform/examples/layer_integration_demo.py:135:    from src.L03_tool_execution.services import ToolModelBridge
./platform/tests/e2e/test_layer_initialization.py:30:        from src.L03_tool_execution import __init__
./platform/tests/e2e/test_layer_initialization.py:31:        from src.L03_tool_execution.services.tool_executor import ToolExecutor
### L04 imports:
./platform/src/L02_runtime/services/model_gateway_bridge.py:38:                from src.L04_model_gateway.services import ModelGateway
./platform/src/L02_runtime/services/model_gateway_bridge.py:43:                logger.error(f"Failed to import L04 Model Gateway: {e}")
./platform/src/L02_runtime/services/model_gateway_bridge.py:78:            from src.L04_model_gateway.models import (
./platform/src/L03_tool_execution/services/model_gateway_bridge.py:37:                from src.L04_model_gateway.services import ModelGateway
./platform/src/L03_tool_execution/services/model_gateway_bridge.py:42:                logger.error(f"Failed to import L04 Model Gateway: {e}")
### L05 imports:
./platform/src/L07_learning/services/training_data_extractor.py:24:    This service parses execution events from L02, planning traces from L05,
./platform/tests/e2e/test_layer_initialization.py:70:        from src.L05_planning import __init__
./platform/tests/e2e/test_layer_initialization.py:71:        from src.L05_planning.services.planning_service import PlanningService
./platform/tests/e2e/test_layer_initialization.py:72:        from src.L05_planning.services.goal_decomposer import GoalDecomposer
./platform/tests/e2e/test_layer_initialization.py:73:        from src.L05_planning.services.task_orchestrator import TaskOrchestrator
### L06 imports:
./platform/src/L07_learning/models/training_example.py:46:    quality scores from L06, metadata for tracking, and structured content
./platform/src/L07_learning/models/training_example.py:69:    # Quality signals from L06
./platform/src/L07_learning/models/training_example.py:120:            quality_score: Quality score from L06 (0-100)
./platform/src/L07_learning/models/training_example.py:205:            quality_score: Quality score from L06
./platform/src/L07_learning/models/reward_signal.py:64:        """Create reward signal from L06 quality score.
### L07 imports:
./platform/tests/e2e/test_l07_learning.py:13:        from src.L07_learning.services.learning_service import LearningService
./platform/tests/e2e/test_l07_learning.py:28:        from src.L07_learning.services.l01_bridge import L07Bridge
./platform/tests/e2e/test_l07_learning.py:38:        from src.L07_learning.models.training_example import (
./platform/tests/e2e/test_l07_learning.py:317:        from src.L07_learning.models.dataset import Dataset
./platform/tests/e2e/test_l07_learning.py:369:        from src.L07_learning.services.learning_service import LearningService
### L09 imports:
./platform/tests/e2e/test_l09_l01_bridge.py:16:from src.L09_api_gateway.services.l01_bridge import L09Bridge
./platform/tests/integration/test_agent_lifecycle.py:3:Tests the flow from L09 API Gateway through L02 Runtime and L01 Data Layer.
./platform/tests/integration/test_agent_lifecycle.py:33:        from src.L09_api_gateway.services.agent_service import AgentService
./platform/test_l09_imports.py:13:    from src.L09_api_gateway.errors import ErrorCode, GatewayError
./platform/test_l09_imports.py:17:    from src.L09_api_gateway.models import (
### L10 imports:
./platform/tests/e2e/test_l10_l01_bridge.py:15:from src.L10_human_interface.services.l01_bridge import L10Bridge
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/torch/_dynamo/symbolic_convert.py:997:        https://github.com/python/cpython/blob/5a094f0255eea1db58fb2cf14c200971e64ec36e/Lib/importlib/_bootstrap.py#L1090
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/models/deprecated/deta/modeling_deta.py:2493:# from https://github.com/facebookresearch/detectron2/blob/cbbc1ce26473cb2a5cc8f58e8ada9ae14cb41052/detectron2/layers/wrappers.py#L100
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/models/pix2struct/image_processing_pix2struct.py:78:# Adapted from https://github.com/google-research/pix2struct/blob/0e1779af0f4db4b652c1d92b3bbd2550a7399123/pix2struct/preprocessing/preprocessing_utils.py#L106
### L11 imports:
./platform/src/L03_tool_execution/models/tool_result.py:148:    Tool invocation request (BC-2 interface from L11).
./platform/tests/e2e/test_l11_l01_bridge.py:17:from src.L11_integration.services.l01_bridge import L11Bridge
./platform/tests/integration/test_event_flow.py:3:Tests event propagation from L02 through L01 and L11.
./platform/tests/integration/test_event_flow.py:60:        from src.L11_integration.services.event_bus import EventBus
./platform/tests/integration/test_event_flow.py:96:        from src.L11_integration.services.event_bus import EventBus
### L12 imports:
./platform/archive/l12-pre-v2/config/__init__.py:9:from .settings import L12Settings, get_settings, reset_settings
./platform/archive/l12-pre-v2/config/settings.py:27:    >>> from L12_nl_interface.config.settings import get_settings
./platform/archive/l12-pre-v2/config/settings.py:427:        >>> from L12_nl_interface.config.settings import get_settings
./platform/archive/l12-pre-v2/core/service_registry.py:412:        >>> from L12_nl_interface.core.service_registry import get_registry
./platform/archive/l12-pre-v2/interfaces/http_api.py:13:    >>> from L12_nl_interface.interfaces.http_api import create_app
## HTTP Client Patterns
Found 3153 HTTP client usages
## gRPC Patterns
Found 87 gRPC references
