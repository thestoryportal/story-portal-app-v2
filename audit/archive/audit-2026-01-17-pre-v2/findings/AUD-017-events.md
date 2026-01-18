# Event Flow Audit
## Event Sourcing Code
./platform/src/L02_runtime/services/l01_bridge.py:25:    - Publish lifecycle events to L01 EventStore via Redis
./platform/src/L05_planning/services/execution_monitor.py:53:        event_store_client=None,  # L01 Event Store client
./platform/src/L05_planning/services/execution_monitor.py:60:            event_store_client: Client for L01 Event Store
./platform/src/L05_planning/services/execution_monitor.py:63:        self.event_store_client = event_store_client
./platform/src/L05_planning/services/execution_monitor.py:308:        if self.event_store_client:
./platform/src/L05_planning/services/execution_monitor.py:310:                await self._publish_to_event_store(event_data)
./platform/src/L05_planning/services/execution_monitor.py:325:    async def _publish_to_event_store(self, event_data: Dict[str, Any]) -> None:
./platform/src/L09_api_gateway/services/event_publisher.py:24:        event_store,
./platform/src/L09_api_gateway/services/event_publisher.py:30:            event_store: L01 Event Store client
./platform/src/L09_api_gateway/services/event_publisher.py:34:        self.event_store = event_store
./platform/src/L09_api_gateway/services/event_publisher.py:91:            await self.event_store.publish_event(event)
./platform/src/L09_api_gateway/services/event_publisher.py:122:        await self.event_store.publish_audit_event(event)
./platform/src/L09_api_gateway/services/event_publisher.py:207:        await self.event_store.publish_event(event)
./platform/src/L09_api_gateway/services/event_publisher.py:226:        await self.event_store.publish_event(event)
./platform/src/L09_api_gateway/gateway.py:114:            event_store=None,  # Mock
./platform/src/L01_data_layer/services/__init__.py:3:from .event_store import EventStore
./platform/src/L01_data_layer/services/__init__.py:17:    "EventStore",
./platform/src/L01_data_layer/services/event_store.py:14:class EventStore:
./platform/src/L01_data_layer/routers/events.py:8:from ..services import EventStore
./platform/src/L01_data_layer/routers/events.py:14:def get_event_store():
./platform/src/L01_data_layer/routers/events.py:15:    return EventStore(db.get_pool(), redis_client)
./platform/src/L01_data_layer/routers/events.py:18:async def create_event(event_data: EventCreate, store: EventStore = Depends(get_event_store)):
./platform/src/L01_data_layer/routers/events.py:28:    store: EventStore = Depends(get_event_store)
./platform/src/L01_data_layer/routers/events.py:33:async def get_event(event_id: UUID, store: EventStore = Depends(get_event_store)):
./platform/src/L01_data_layer/__init__.py:25:    EventStore,
./platform/src/L01_data_layer/__init__.py:53:    "EventStore",
./platform/src/L12_nl_interface/services/l01_bridge.py:8:- Async event recording to L01 EventStore
./platform/src/L12_nl_interface/services/l01_bridge.py:377:        """Send events to L01 EventStore.
./platform/src/L12_nl_interface/utils/service_categorizer.py:26:                "EventStore",
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/attributes.py:1753:    def fire_append_event(

## Event Type Definitions
./platform/src/L05_planning/services/execution_monitor.py:27:class ExecutionEvent(str, Enum):
./platform/src/L05_planning/services/execution_monitor.py:285:        event_type: ExecutionEvent,
./platform/src/L05_planning/services/execution_monitor.py:292:            event_type: Type of event
./platform/src/L05_planning/services/execution_monitor.py:302:            "event_type": event_type.value,
./platform/src/L05_planning/services/execution_monitor.py:315:        if event_type in self._callbacks:
./platform/src/L05_planning/services/execution_monitor.py:316:            for callback in self._callbacks[event_type]:
./platform/src/L05_planning/services/execution_monitor.py:333:        logger.debug(f"Publishing event: {event_data['event_type']} (mock)")
./platform/src/L05_planning/services/execution_monitor.py:337:        event_type: ExecutionEvent,
./platform/src/L05_planning/services/execution_monitor.py:344:            event_type: Event type to listen for
./platform/src/L05_planning/services/execution_monitor.py:347:        if event_type not in self._callbacks:
./platform/src/L05_planning/services/execution_monitor.py:348:            self._callbacks[event_type] = []
./platform/src/L05_planning/services/execution_monitor.py:349:        self._callbacks[event_type].append(callback)
./platform/src/L06_evaluation/models/__init__.py:3:from .cloud_event import CloudEvent, EventSource, EventType
./platform/src/L06_evaluation/models/__init__.py:15:    "EventType",
./platform/src/L06_evaluation/models/cloud_event.py:10:class EventSource(str, Enum):
./platform/src/L06_evaluation/models/cloud_event.py:20:class EventType(str, Enum):
./platform/src/L06_evaluation/models/cloud_event.py:35:class CloudEvent:
./platform/src/L06_evaluation/services/event_validator.py:28:class EventValidator:
./platform/src/L06_evaluation/services/audit_logger.py:29:    async def log(self, event_type: str, data: Dict[str, Any]):
./platform/src/L06_evaluation/services/audit_logger.py:34:            event_type: Type of event
./platform/src/L06_evaluation/services/audit_logger.py:39:            "event_type": event_type,
./platform/src/L06_evaluation/services/audit_logger.py:43:        logger.info(f"Audit log: {event_type}")
./platform/src/L06_evaluation/services/evaluation_service.py:176:                "event_type": event.type,
./platform/src/L06_evaluation/__init__.py:11:from .models.cloud_event import CloudEvent, EventSource, EventType
./platform/src/L06_evaluation/__init__.py:22:    "EventType",
./platform/src/L07_learning/services/training_data_extractor.py:70:            event_type = event.get('type', '')
./platform/src/L07_learning/services/training_data_extractor.py:72:            if event_type == 'execution.completed':
./platform/src/L07_learning/services/training_data_extractor.py:74:            elif event_type == 'planning.completed':
./platform/src/L07_learning/services/training_data_extractor.py:76:            elif event_type == 'evaluation.completed':
./platform/src/L07_learning/services/training_data_extractor.py:80:                logger.debug(f"Skipping event type: {event_type}")

## CQRS Patterns
./platform/output/L02_runtime/runtime_context_bridge.py:267:        # Query database for checkpoint versions
./platform/output/L05_planning/planning_context_retriever.py:267:        # Query for previous versions of planning context
./platform/src/L02_runtime/backends/protocol.py:210:            command: Command and arguments to execute
./platform/src/L02_runtime/backends/protocol.py:211:            timeout_seconds: Command timeout
./platform/src/L02_runtime/services/document_bridge.py:35:    - Query authoritative documents
./platform/src/L02_runtime/services/document_bridge.py:84:        # Query cache: query_key -> (result, expiry_time)
./platform/src/L02_runtime/services/document_bridge.py:115:        Query documents using hybrid search.
./platform/src/L02_runtime/services/document_bridge.py:128:        logger.info(f"Querying documents: {query}")
./platform/src/L02_runtime/services/document_bridge.py:253:            # Query for relevant documents
./platform/src/L02_runtime/services/document_bridge.py:319:            query: Query to find source for
./platform/src/L02_runtime/services/document_bridge.py:330:            # Query documents
./platform/src/L02_runtime/services/mcp_client.py:96:            server_command: Command to start MCP server (e.g., ['node', 'server.js'])
./platform/src/L02_runtime/services/sandbox_manager.py:87:        For KubernetesRuntime: Query available RuntimeClasses from cluster
./platform/src/L05_planning/templates/common_templates.py:173:            name="Simple Query",
./platform/src/L06_evaluation/services/__init__.py:12:from .query_engine import QueryEngine
./platform/src/L06_evaluation/services/__init__.py:27:    "QueryEngine",
./platform/src/L06_evaluation/services/event_validator.py:66:            r"[;\$\{\}]",  # Command injection
./platform/src/L06_evaluation/services/metrics_engine.py:267:        Query metrics with aggregation.
./platform/src/L06_evaluation/services/metrics_engine.py:285:                    logger.debug(f"Query cache hit: {cache_key}")
./platform/src/L06_evaluation/services/compliance_validator.py:102:        # Query actual duration from metrics
./platform/src/L06_evaluation/services/query_engine.py:1:"""Query engine for metric queries with caching"""
./platform/src/L06_evaluation/services/query_engine.py:14:class QueryEngine:
./platform/src/L06_evaluation/services/evaluation_service.py:23:from .query_engine import QueryEngine
./platform/src/L06_evaluation/services/evaluation_service.py:77:        self.query = QueryEngine(self.metrics, self.cache)
./platform/src/L06_evaluation/services/evaluation_service.py:206:        Query quality scores for agent.
./platform/src/L06_evaluation/services/evaluation_service.py:234:        Query anomalies.
./platform/src/L06_evaluation/tests/test_integration.py:45:    # Query quality scores
./platform/src/L09_api_gateway/services/validator.py:22:    - Query string validation
./platform/src/L09_api_gateway/services/validator.py:114:                f"Query string too long (max {self.max_query_length} chars)",
./platform/src/L09_api_gateway/services/l01_bridge.py:100:            query_params: Query parameters

## Event Table Contents (sample)
(eval):22: command not found: psql
No events table
