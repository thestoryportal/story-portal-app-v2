# Observability Audit
## Prometheus Metrics
./platform/src/L02_runtime/backends/kubernetes_runtime.py:121:        """Get pod resource usage from metrics server"""
./platform/src/L02_runtime/models/health_models.py:4:Models for agent health status and metrics.
./platform/src/L02_runtime/models/health_models.py:30:    """Collected health metrics"""
./platform/src/L02_runtime/models/health_models.py:64:    metrics: HealthMetrics = field(default_factory=HealthMetrics)
./platform/src/L02_runtime/models/health_models.py:82:            "metrics": self.metrics.to_dict(),
./platform/src/L02_runtime/services/fleet_manager.py:49:    - Track scaling metrics
./platform/src/L02_runtime/services/fleet_manager.py:129:        metrics: ScalingMetrics
./platform/src/L02_runtime/services/fleet_manager.py:132:        Evaluate whether scaling is needed based on metrics.
./platform/src/L02_runtime/services/fleet_manager.py:135:            metrics: Current fleet metrics
./platform/src/L02_runtime/services/fleet_manager.py:140:        current_replicas = metrics.current_replicas
./platform/src/L02_runtime/services/fleet_manager.py:141:        avg_cpu = metrics.avg_cpu_utilization
./platform/src/L02_runtime/services/fleet_manager.py:142:        avg_memory = metrics.avg_memory_utilization
./platform/src/L02_runtime/services/fleet_manager.py:374:    async def get_fleet_metrics(self) -> ScalingMetrics:
./platform/src/L02_runtime/services/fleet_manager.py:376:        Get current fleet metrics.
./platform/src/L02_runtime/services/fleet_manager.py:381:        # TODO: Collect actual metrics from instances
./platform/src/L02_runtime/services/fleet_manager.py:382:        # For now, return stub metrics
./platform/src/L02_runtime/services/health_monitor.py:4:Monitors agent health via probes and collects agent-specific metrics.
./platform/src/L02_runtime/services/health_monitor.py:5:Provides Kubernetes-compatible health endpoints and Prometheus metrics.
./platform/src/L02_runtime/services/health_monitor.py:44:    Monitors agent health and collects metrics.
./platform/src/L02_runtime/services/health_monitor.py:49:    - Collect and expose Prometheus metrics
./platform/src/L02_runtime/services/health_monitor.py:62:                - metrics: Metrics collection configuration
./platform/src/L02_runtime/services/health_monitor.py:82:        metrics_config = self.config.get("metrics", {})
./platform/src/L02_runtime/services/health_monitor.py:83:        self.error_rate_window = metrics_config.get("error_rate_window_seconds", 300)
./platform/src/L02_runtime/services/health_monitor.py:84:        self.latency_buckets = metrics_config.get(
./platform/src/L02_runtime/services/health_monitor.py:100:        self._metrics_history: List[MetricsSnapshot] = []
./platform/src/L02_runtime/services/health_monitor.py:109:        self._metrics_collection_task: Optional[asyncio.Task] = None
./platform/src/L02_runtime/services/health_monitor.py:129:        self._metrics_collection_task = asyncio.create_task(
./platform/src/L02_runtime/services/health_monitor.py:130:            self._metrics_collection_loop()
./platform/src/L02_runtime/services/health_monitor.py:304:        Record request metrics.
./platform/src/L02_runtime/services/health_monitor.py:358:    async def get_metrics_snapshot(self) -> MetricsSnapshot:

## Logging Configuration
./platform/src/L02_runtime/examples/basic_usage.py:12:import logging
./platform/src/L02_runtime/examples/basic_usage.py:27:# Configure logging
./platform/src/L02_runtime/examples/basic_usage.py:28:logging.basicConfig(
./platform/src/L02_runtime/examples/basic_usage.py:29:    level=logging.INFO,
./platform/src/L02_runtime/examples/basic_usage.py:33:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/runtime.py:9:import logging
./platform/src/L02_runtime/runtime.py:18:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/agent_executor.py:11:import logging
./platform/src/L02_runtime/services/agent_executor.py:23:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/document_bridge.py:12:import logging
./platform/src/L02_runtime/services/document_bridge.py:19:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/fleet_manager.py:11:import logging
./platform/src/L02_runtime/services/fleet_manager.py:20:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/health_monitor.py:11:import logging
./platform/src/L02_runtime/services/health_monitor.py:21:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/lifecycle_manager.py:13:import logging
./platform/src/L02_runtime/services/lifecycle_manager.py:27:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/mcp_client.py:12:import logging
./platform/src/L02_runtime/services/mcp_client.py:20:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/mcp_client.py:97:            server_name: Human-readable server name for logging
./platform/src/L02_runtime/services/resource_manager.py:11:import logging
./platform/src/L02_runtime/services/resource_manager.py:28:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/sandbox_manager.py:11:import logging
./platform/src/L02_runtime/services/sandbox_manager.py:22:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/session_bridge.py:12:import logging
./platform/src/L02_runtime/services/session_bridge.py:22:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/state_manager.py:13:import logging
./platform/src/L02_runtime/services/state_manager.py:32:logger = logging.getLogger(__name__)
./platform/src/L02_runtime/services/warm_pool_manager.py:11:import logging
./platform/src/L02_runtime/services/warm_pool_manager.py:20:logger = logging.getLogger(__name__)

## OpenTelemetry
./platform/src/L07_learning/models/training_example.py:233:            'travel': ['flight', 'hotel', 'booking', 'trip', 'destination'],
./platform/src/L09_api_gateway/models/request_models.py:50:    span_id: str = Field(..., description="W3C Trace Context span ID")
./platform/src/L09_api_gateway/models/request_models.py:84:    @validator("span_id")
./platform/src/L09_api_gateway/models/request_models.py:85:    def validate_span_id(cls, v):
./platform/src/L09_api_gateway/models/request_models.py:86:        """Validate W3C span ID format"""
./platform/src/L09_api_gateway/models/request_models.py:89:            raise ValueError("Invalid span_id format (must be 16 hex chars)")
./platform/src/L09_api_gateway/models/request_models.py:97:            "X-Span-ID": self.span_id,
./platform/src/L09_api_gateway/services/response_formatter.py:53:        response.headers["X-Span-ID"] = context.span_id
./platform/src/L09_api_gateway/services/event_publisher.py:65:                "span_id": context.span_id,
./platform/src/L09_api_gateway/services/l01_bridge.py:52:        span_id: str,
./platform/src/L09_api_gateway/services/l01_bridge.py:80:            span_id: Span ID within trace
./platform/src/L09_api_gateway/services/l01_bridge.py:113:                span_id=span_id,
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
./platform/src/L11_integration/models/error_codes.py:161:    ErrorCode.E11502: "Failed to create trace span",
./platform/src/L11_integration/models/trace.py:15:    """Type of span in distributed trace."""
./platform/src/L11_integration/models/trace.py:25:    """Status of a trace span."""
./platform/src/L11_integration/models/trace.py:41:    span_id: str = field(default_factory=lambda: str(uuid4()))  # Current span ID
./platform/src/L11_integration/models/trace.py:42:    parent_span_id: Optional[str] = None  # Parent span ID

## Monitoring Service Status
Prometheus: NOT RUNNING
Grafana: NOT RUNNING
