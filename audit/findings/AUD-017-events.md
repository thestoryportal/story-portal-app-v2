# Event Flow Audit
## Event Sourcing Code
./platform/archive/l12-pre-v2/services/l01_bridge.py:8:- Async event recording to L01 EventStore
./platform/archive/l12-pre-v2/services/l01_bridge.py:377:        """Send events to L01 EventStore.
./platform/archive/l12-pre-v2/utils/service_categorizer.py:26:                "EventStore",
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
## Event Type Definitions
./platform/shared/clients/l01_client.py:89:    async def publish_event(self, event_type: str, aggregate_type: str,
./platform/shared/clients/l01_client.py:95:            "event_type": event_type,
./platform/shared/clients/l01_client.py:105:                          event_type: Optional[str] = None,
./platform/shared/clients/l01_client.py:112:        if event_type:
./platform/shared/clients/l01_client.py:113:            params["event_type"] = event_type
./platform/shared/clients/l01_client.py:1731:        event_type: str,
./platform/shared/clients/l01_client.py:1749:            "event_type": event_type,
./platform/shared/clients/l01_client.py:1777:        event_type: str,
./platform/shared/clients/l01_client.py:1792:            "event_type": event_type
./platform/archive/l12-pre-v2/services/l01_bridge.py:108:class InvocationEvent:
./platform/archive/l12-pre-v2/services/l01_bridge.py:138:            "event_type": "l12.service_invoked",
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
## CQRS Patterns
./platform/shared/clients/l01_client.py:107:        """Query events."""
./platform/shared/clients/l01_client.py:1052:        """Query metrics with filters."""
./platform/archive/l12-pre-v2/interfaces/http_api.py:23:from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
./platform/archive/l12-pre-v2/interfaces/http_api.py:34:from ..routing.command_router import CommandRouter
./platform/archive/l12-pre-v2/interfaces/http_api.py:39:from ..services.command_history import CommandHistory
./platform/archive/l12-pre-v2/interfaces/http_api.py:125:    # Initialize CommandHistory for command replay
./platform/archive/l12-pre-v2/interfaces/http_api.py:126:    command_history = CommandHistory(
./platform/archive/l12-pre-v2/interfaces/http_api.py:143:    command_router = CommandRouter(
./platform/archive/l12-pre-v2/interfaces/http_api.py:259:        q: str = Query(..., description="Search query", min_length=1),
./platform/archive/l12-pre-v2/interfaces/http_api.py:260:        threshold: float = Query(
./platform/archive/l12-pre-v2/interfaces/http_api.py:263:        max_results: int = Query(
./platform/archive/l12-pre-v2/interfaces/http_api.py:305:        layer: Optional[str] = Query(
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:21:from ..routing.command_router import CommandRouter
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:69:            self.command_router = CommandRouter(
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:29:from ..routing.command_router import CommandRouter
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:53:        command_router: CommandRouter for invocation
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:82:        self.command_router = CommandRouter(
./platform/archive/l12-pre-v2/models/__init__.py:11:Command Models:
./platform/archive/l12-pre-v2/models/__init__.py:16:- SearchQuery: Fuzzy search query
./platform/archive/l12-pre-v2/models/__init__.py:38:    SearchQuery,
./platform/archive/l12-pre-v2/models/__init__.py:49:    # Command models
./platform/archive/l12-pre-v2/models/__init__.py:55:    "SearchQuery",
./platform/archive/l12-pre-v2/models/command_models.py:1:"""Command request/response models for L12 Natural Language Interface.
./platform/archive/l12-pre-v2/models/command_models.py:9:These models are used by CommandRouter, HTTP API, and MCP Server to handle
./platform/archive/l12-pre-v2/models/command_models.py:306:class SearchQuery(BaseModel):
./platform/archive/l12-pre-v2/models/command_models.py:307:    """Query for fuzzy service search.
./platform/archive/l12-pre-v2/models/command_models.py:317:        >>> query = SearchQuery(
./platform/archive/l12-pre-v2/routing/__init__.py:6:- CommandRouter: Routes commands to appropriate service methods
./platform/archive/l12-pre-v2/routing/__init__.py:11:from .command_router import CommandRouter
./platform/archive/l12-pre-v2/routing/__init__.py:17:    "CommandRouter",
## Event Table Contents (sample)
(eval):1: command not found: psql
No events table
