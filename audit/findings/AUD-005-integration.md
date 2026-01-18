# Integration Audit
## Cross-Layer Imports

### L01 imports:
./platform/output/L02_runtime/runtime_context_bridge.py:30:            context_service: ContextService instance from L01_data
./platform/output/L05_planning/planning_context_retriever.py:31:            context_service: ContextService instance from L01_data
./platform/output/L05_planning/planning_context_retriever.py:32:            document_service: DocumentService instance from L01_data
./platform/src/L02_runtime/runtime.py:15:from .services import SandboxManager, LifecycleManager, L01Bridge
./platform/src/L02_runtime/services/__init__.py:10:from .l01_bridge import L01Bridge
./platform/src/L02_runtime/services/lifecycle_manager.py:24:from .l01_bridge import L01Bridge
./platform/src/L02_runtime/services/l01_bridge.py:12:from L01_data_layer.client import L01Client
./platform/src/L03_tool_execution/services/l01_bridge.py:15:from ...L01_data_layer.client import L01Client
./platform/src/L03_tool_execution/services/l01_bridge.py:248:        """Get tool execution history from L01.
./platform/src/L03_tool_execution/services/l01_bridge.py:261:            logger.debug(f"Retrieved execution history for {invocation_id} from L01")

### L02 imports:
./platform/src/L03_tool_execution/models/execution_context.py:164:    Implements BC-1 nested sandbox context from L02.
./platform/src/L03_tool_execution/services/mcp_tool_bridge.py:30:from ...L02_runtime.services.document_bridge import DocumentBridge
./platform/src/L03_tool_execution/services/mcp_tool_bridge.py:31:from ...L02_runtime.services.session_bridge import SessionBridge
./platform/src/L04_model_gateway/models/error_codes.py:5:Following pattern from L02 (E2xxx) and L03 (E3xxx)
./platform/src/L05_planning/services/planning_service.py:37:from src.L02_runtime.services.agent_executor import AgentExecutor
./platform/src/L07_learning/models/training_example.py:118:            trace: Execution trace from L02
./platform/src/L07_learning/services/training_data_extractor.py:24:    This service parses execution events from L02, planning traces from L05,
./platform/src/L10_human_interface/services/dashboard_service.py:4:Aggregates dashboard data from L02 (agent state) and L06 (metrics).
./platform/src/L10_human_interface/services/dashboard_service.py:35:    - Aggregate agent state from L02 StateManager
./platform/src/L10_human_interface/services/dashboard_service.py:168:        """Get agents summary from L02 StateManager with caching."""

### L03 imports:
./platform/src/L04_model_gateway/models/error_codes.py:5:Following pattern from L02 (E2xxx) and L03 (E3xxx)
./platform/src/L05_planning/services/planning_service.py:38:from src.L03_tool_execution.services.tool_executor import ToolExecutor
./platform/examples/layer_integration_demo.py:135:    from src.L03_tool_execution.services import ToolModelBridge
./platform/tests/e2e/test_layer_initialization.py:30:        from src.L03_tool_execution import __init__
./platform/tests/e2e/test_layer_initialization.py:31:        from src.L03_tool_execution.services.tool_executor import ToolExecutor
./platform/tests/e2e/test_layer_initialization.py:32:        from src.L03_tool_execution.services.tool_registry import ToolRegistry
./platform/tests/e2e/test_layer_initialization.py:39:        from src.L03_tool_execution.services.tool_executor import ToolExecutor
./platform/tests/e2e/test_layer_initialization.py:40:        from src.L03_tool_execution.services.tool_registry import ToolRegistry
./platform/tests/e2e/test_layer_initialization.py:41:        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox
./platform/tests/e2e/test_layer_initialization.py:111:        from src.L03_tool_execution.services.tool_executor import ToolExecutor

### L04 imports:
./platform/src/L02_runtime/services/model_gateway_bridge.py:38:                from src.L04_model_gateway.services import ModelGateway
./platform/src/L02_runtime/services/model_gateway_bridge.py:43:                logger.error(f"Failed to import L04 Model Gateway: {e}")
./platform/src/L02_runtime/services/model_gateway_bridge.py:78:            from src.L04_model_gateway.models import (
./platform/src/L03_tool_execution/services/model_gateway_bridge.py:37:                from src.L04_model_gateway.services import ModelGateway
./platform/src/L03_tool_execution/services/model_gateway_bridge.py:42:                logger.error(f"Failed to import L04 Model Gateway: {e}")
./platform/src/L03_tool_execution/services/model_gateway_bridge.py:75:            from src.L04_model_gateway.models import (
./platform/src/L05_planning/services/goal_decomposer.py:288:            from src.L04_model_gateway.models import (
./platform/src/L05_planning/services/planning_service.py:36:from src.L04_model_gateway.services.model_gateway import ModelGateway
./platform/examples/layer_integration_demo.py:27:    from src.L04_model_gateway.services import ModelGateway
./platform/examples/layer_integration_demo.py:28:    from src.L04_model_gateway.models import Message, MessageRole

### L05 imports:
./platform/src/L07_learning/services/training_data_extractor.py:24:    This service parses execution events from L02, planning traces from L05,
./platform/tests/e2e/test_layer_initialization.py:70:        from src.L05_planning import __init__
./platform/tests/e2e/test_layer_initialization.py:71:        from src.L05_planning.services.planning_service import PlanningService
./platform/tests/e2e/test_layer_initialization.py:72:        from src.L05_planning.services.goal_decomposer import GoalDecomposer
./platform/tests/e2e/test_layer_initialization.py:73:        from src.L05_planning.services.task_orchestrator import TaskOrchestrator
./platform/tests/e2e/test_layer_initialization.py:81:        from src.L05_planning.services.planning_service import PlanningService
./platform/tests/e2e/test_layer_initialization.py:115:        from src.L05_planning.services.planning_service import PlanningService
./platform/tests/e2e/test_l05_planning.py:11:        from src.L05_planning.services.planning_service import PlanningService
./platform/tests/e2e/test_l05_planning.py:20:        from src.L05_planning.services.goal_decomposer import GoalDecomposer
./platform/tests/e2e/test_l05_planning.py:29:        from src.L05_planning.services.dependency_resolver import DependencyResolver

### L06 imports:
./platform/src/L07_learning/models/training_example.py:46:    quality scores from L06, metadata for tracking, and structured content
./platform/src/L07_learning/models/training_example.py:69:    # Quality signals from L06
./platform/src/L07_learning/models/training_example.py:120:            quality_score: Quality score from L06 (0-100)
./platform/src/L07_learning/models/training_example.py:205:            quality_score: Quality score from L06
./platform/src/L07_learning/models/reward_signal.py:64:        """Create reward signal from L06 quality score.
./platform/src/L07_learning/models/reward_signal.py:69:            quality_score: Quality score from L06 (0-100)
./platform/src/L07_learning/services/rlhf_engine.py:191:        """Create preference pairs from L06 quality scores.
./platform/src/L07_learning/services/training_data_extractor.py:25:    and quality scores from L06 to create structured training examples suitable
./platform/src/L07_learning/services/training_data_extractor.py:116:        # Get quality score (would normally fetch from L06)
./platform/src/L07_learning/__init__.py:5:to improve autonomously based on quality signals from L06.

### L07 imports:
./platform/tests/e2e/test_l07_learning.py:13:        from src.L07_learning.services.learning_service import LearningService
./platform/tests/e2e/test_l07_learning.py:28:        from src.L07_learning.services.l01_bridge import L07Bridge
./platform/tests/e2e/test_l07_learning.py:38:        from src.L07_learning.models.training_example import (
./platform/tests/e2e/test_l07_learning.py:317:        from src.L07_learning.models.dataset import Dataset
./platform/tests/e2e/test_l07_learning.py:369:        from src.L07_learning.services.learning_service import LearningService
./platform/tests/e2e/test_l07_learning.py:384:        from src.L07_learning.models.training_example import (

### L09 imports:
./platform/tests/e2e/test_l09_l01_bridge.py:16:from src.L09_api_gateway.services.l01_bridge import L09Bridge
./platform/tests/integration/test_agent_lifecycle.py:3:Tests the flow from L09 API Gateway through L02 Runtime and L01 Data Layer.
./platform/tests/integration/test_agent_lifecycle.py:33:        from src.L09_api_gateway.services.agent_service import AgentService
./platform/test_l09_imports.py:13:    from src.L09_api_gateway.errors import ErrorCode, GatewayError
./platform/test_l09_imports.py:17:    from src.L09_api_gateway.models import (
./platform/test_l09_imports.py:31:    from src.L09_api_gateway.models import RequestMetadata

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
./platform/tests/integration/test_event_flow.py:129:        from src.L11_integration.services.event_bus import EventBus
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/huggingface_hub/serialization/_torch.py:802:    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L11.
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/modeling_gguf_pytorch_utils.py:280:# modified from https://github.com/vllm-project/vllm/blob/v0.6.4.post1/vllm/model_executor/model_loader/loader.py#L1115-L1147

### L12 imports:
./platform/tests/l12_nl_interface/test_service_registry.py:5:from src.L12_nl_interface.core.service_registry import ServiceRegistry, get_registry
./platform/tests/l12_nl_interface/test_command_router.py:7:from src.L12_nl_interface.core.service_factory import ServiceFactory
./platform/tests/l12_nl_interface/test_command_router.py:8:from src.L12_nl_interface.core.service_registry import get_registry
./platform/tests/l12_nl_interface/test_command_router.py:9:from src.L12_nl_interface.core.session_manager import SessionManager
./platform/tests/l12_nl_interface/test_command_router.py:10:from src.L12_nl_interface.models.command_models import (
./platform/tests/l12_nl_interface/test_command_router.py:15:from src.L12_nl_interface.routing.command_router import CommandRouter
./platform/tests/l12_nl_interface/test_command_router.py:16:from src.L12_nl_interface.routing.exact_matcher import ExactMatcher
./platform/tests/l12_nl_interface/test_command_router.py:17:from src.L12_nl_interface.routing.fuzzy_matcher import FuzzyMatcher
./platform/tests/l12_nl_interface/test_command_router.py:18:from src.L12_nl_interface.services.memory_monitor import MemoryMonitor
./platform/tests/l12_nl_interface/test_matchers.py:5:from src.L12_nl_interface.core.service_registry import get_registry

## HTTP Client Patterns
Found 3135 HTTP client usages

## gRPC Patterns
Found 87 gRPC references
