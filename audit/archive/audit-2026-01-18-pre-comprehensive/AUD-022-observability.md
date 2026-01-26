# Observability Audit
## Prometheus Metrics
./platform/shared/clients/l01_client.py:395:                               metrics: Optional[Dict[str, Any]] = None,
./platform/shared/clients/l01_client.py:404:            "metrics": metrics or {},
./platform/shared/clients/l01_client.py:1039:        response = await client.post("/metrics/", json=payload)
./platform/shared/clients/l01_client.py:1043:    async def query_metrics(
./platform/shared/clients/l01_client.py:1052:        """Query metrics with filters."""
./platform/shared/clients/l01_client.py:1069:        response = await client.get("/metrics/", params=params)
./platform/archive/l12-pre-v2/core/session_manager.py:13:- Session metrics and statistics
./platform/archive/l12-pre-v2/core/session_manager.py:109:        >>> metrics = manager.get_session_metrics("session-123")
./platform/archive/l12-pre-v2/core/session_manager.py:236:        # Update session metrics
./platform/archive/l12-pre-v2/core/session_manager.py:352:    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
./platform/archive/l12-pre-v2/core/session_manager.py:353:        """Get metrics for a specific session.
./platform/archive/l12-pre-v2/core/session_manager.py:356:            session_id: Session to get metrics for
./platform/archive/l12-pre-v2/core/session_manager.py:359:            Dict with session metrics, or None if session not found
./platform/archive/l12-pre-v2/core/session_manager.py:362:            >>> metrics = manager.get_session_metrics("session-123")
./platform/archive/l12-pre-v2/core/session_manager.py:363:            >>> print(f"Memory: {metrics['memory_mb']:.2f}MB")
./platform/archive/l12-pre-v2/core/session_manager.py:386:    def get_all_session_metrics(self) -> List[Dict[str, Any]]:
./platform/archive/l12-pre-v2/core/session_manager.py:387:        """Get metrics for all active sessions.
./platform/archive/l12-pre-v2/core/session_manager.py:390:            List of session metrics dicts
./platform/archive/l12-pre-v2/core/session_manager.py:393:            >>> all_metrics = manager.get_all_session_metrics()
./platform/archive/l12-pre-v2/core/session_manager.py:394:            >>> for metrics in all_metrics:
./platform/archive/l12-pre-v2/core/session_manager.py:395:            ...     print(f"{metrics['session_id']}: {metrics['service_count']} services")
./platform/archive/l12-pre-v2/core/session_manager.py:398:            self.get_session_metrics(session_id)
./platform/archive/l12-pre-v2/core/session_manager.py:402:    def get_global_metrics(self) -> Dict[str, Any]:
./platform/archive/l12-pre-v2/core/session_manager.py:403:        """Get global metrics across all sessions.
./platform/archive/l12-pre-v2/core/session_manager.py:406:            Dict with global metrics
./platform/archive/l12-pre-v2/core/session_manager.py:409:            >>> metrics = manager.get_global_metrics()
./platform/archive/l12-pre-v2/core/session_manager.py:410:            >>> print(f"Active sessions: {metrics['active_sessions']}")
./platform/archive/l12-pre-v2/interfaces/http_api.py:9:GET /v1/sessions/{id} - Get session metrics
./platform/archive/l12-pre-v2/interfaces/http_api.py:208:            Health status with basic metrics
./platform/archive/l12-pre-v2/interfaces/http_api.py:371:    # Get session metrics endpoint
## Logging Configuration
./platform/shared/clients/l01_client.py:10:import logging
./platform/shared/clients/l01_client.py:12:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/config/settings.py:32:import logging
./platform/archive/l12-pre-v2/config/settings.py:39:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/config/settings.py:286:        """Validate logging level.
./platform/archive/l12-pre-v2/config/settings.py:331:    def configure_logging(self) -> None:
./platform/archive/l12-pre-v2/config/settings.py:332:        """Configure Python logging based on log_level setting.
./platform/archive/l12-pre-v2/config/settings.py:336:            >>> settings.configure_logging()
./platform/archive/l12-pre-v2/config/settings.py:338:        logging.basicConfig(
./platform/archive/l12-pre-v2/config/settings.py:339:            level=getattr(logging, self.log_level),
./platform/archive/l12-pre-v2/core/service_registry.py:15:import logging
./platform/archive/l12-pre-v2/core/service_registry.py:21:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/core/service_factory.py:17:import logging
./platform/archive/l12-pre-v2/core/service_factory.py:23:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/core/service_factory.py:341:            service_name: Service name (for logging)
./platform/archive/l12-pre-v2/core/session_manager.py:23:import logging
./platform/archive/l12-pre-v2/core/session_manager.py:30:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/core/session_manager.py:271:        # Get session info for logging
./platform/archive/l12-pre-v2/interfaces/http_api.py:19:import logging
./platform/archive/l12-pre-v2/interfaces/http_api.py:42:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/interfaces/http_api.py:98:    settings.configure_logging()
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:13:import logging
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:28:# Configure logging to file (not stdout/stderr to avoid MCP protocol interference)
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:29:logging.basicConfig(
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:30:    level=logging.INFO,
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:33:        logging.FileHandler("/tmp/l12_mcp_server.log"),
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:36:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:20:import logging
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:34:logger = logging.getLogger(__name__)
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:62:        self.settings.configure_logging()
## OpenTelemetry
./platform/shared/clients/l01_client.py:1265:        span_id: str,
./platform/shared/clients/l01_client.py:1294:            "span_id": span_id,
./platform/archive/l12-pre-v2/interfaces/http_api.py:92:async def lifespan(app: FastAPI):
./platform/archive/l12-pre-v2/interfaces/http_api.py:93:    """Lifespan context manager for startup and shutdown."""
./platform/archive/l12-pre-v2/interfaces/http_api.py:190:        lifespan=lifespan,
./platform/src/L07_learning/models/training_example.py:233:            'travel': ['flight', 'hotel', 'booking', 'trip', 'destination'],
./platform/src/L09_api_gateway/models/request_models.py:50:    span_id: str = Field(..., description="W3C Trace Context span ID")
./platform/src/L09_api_gateway/models/request_models.py:84:    @validator("span_id")
./platform/src/L09_api_gateway/models/request_models.py:85:    def validate_span_id(cls, v):
./platform/src/L09_api_gateway/models/request_models.py:86:        """Validate W3C span ID format"""
./platform/src/L09_api_gateway/models/request_models.py:89:            raise ValueError("Invalid span_id format (must be 16 hex chars)")
./platform/src/L09_api_gateway/models/request_models.py:97:            "X-Span-ID": self.span_id,
./platform/src/L09_api_gateway/services/l01_bridge.py:52:        span_id: str,
./platform/src/L09_api_gateway/services/l01_bridge.py:80:            span_id: Span ID within trace
./platform/src/L09_api_gateway/services/l01_bridge.py:113:                span_id=span_id,
./platform/src/L09_api_gateway/services/response_formatter.py:53:        response.headers["X-Span-ID"] = context.span_id
./platform/src/L09_api_gateway/services/event_publisher.py:65:                "span_id": context.span_id,
./platform/src/L09_api_gateway/tests/test_router.py:39:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_router.py:62:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_router.py:98:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_router.py:131:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_validator.py:18:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_validator.py:41:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_validator.py:67:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_validator.py:93:        span_id="b" * 16,
./platform/src/L09_api_gateway/tests/test_validator.py:122:        span_id="b" * 16,
./platform/src/L09_api_gateway/gateway.py:248:                        request_id=f"req-{context.trace_id}-{context.span_id}",
./platform/src/L09_api_gateway/gateway.py:250:                        span_id=context.span_id,
./platform/src/L09_api_gateway/gateway.py:316:        span_id = uuid.uuid4().hex[:16]
./platform/src/L09_api_gateway/gateway.py:335:            span_id=span_id,
## Monitoring Service Status
Prometheus: NOT RUNNING
Internal Server ErrorGrafana: RUNNING
