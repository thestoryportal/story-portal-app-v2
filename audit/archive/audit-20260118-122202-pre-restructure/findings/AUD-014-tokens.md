# Token Management Audit
## JWT Patterns
./platform/src/L03_tool_execution/__init__.py:10:- Permission enforcement (JWT + OPA)
./platform/src/L03_tool_execution/models/tool_result.py:113:    capability_token: Optional[str] = None  # JWT capability token (Gap G-006)
./platform/src/L06_evaluation/models/error_codes.py:13:    E6002 = "E6002"  # Invalid JWT signature
./platform/src/L06_evaluation/models/error_codes.py:98:            message="Invalid JWT signature",
./platform/src/L06_evaluation/models/error_codes.py:108:            root_cause="JWT exp claim is in the past",
./platform/src/L09_api_gateway/models/consumer_models.py:14:    OAUTH_JWT = "oauth_jwt"
./platform/src/L09_api_gateway/main.py:6:- Authentication (JWT, API Keys)
./platform/src/L09_api_gateway/services/l01_bridge.py:163:            auth_method: Authentication method (api_key, oauth, jwt, etc.)
./platform/src/L09_api_gateway/services/authentication.py:2:Authentication Handler - API Key, OAuth/JWT, mTLS
./platform/src/L09_api_gateway/services/authentication.py:6:import jwt
./platform/src/L09_api_gateway/services/authentication.py:17:    - OAuth 2.0 with JWT (RS256)
./platform/src/L09_api_gateway/services/authentication.py:46:        if auth_header.startswith("Bearer ") and not self._is_jwt(auth_header):
./platform/src/L09_api_gateway/services/authentication.py:51:        # Try JWT authentication
./platform/src/L09_api_gateway/services/authentication.py:52:        if auth_header.startswith("Bearer ") and self._is_jwt(auth_header):
./platform/src/L09_api_gateway/services/authentication.py:53:            return await self._authenticate_jwt(auth_header, consumer_lookup_fn)
./platform/src/L09_api_gateway/services/authentication.py:64:            details={"supported_methods": ["api_key", "oauth_jwt", "mtls"]},
./platform/src/L09_api_gateway/services/authentication.py:112:    async def _authenticate_jwt(
./platform/src/L09_api_gateway/services/authentication.py:115:        """Authenticate using OAuth 2.0 JWT"""
./platform/src/L09_api_gateway/services/authentication.py:119:            # Decode JWT header to get algorithm and key ID
./platform/src/L09_api_gateway/services/authentication.py:120:            unverified_header = jwt.get_unverified_header(token)
./platform/src/L09_api_gateway/services/authentication.py:124:            unverified_payload = jwt.decode(token, options={"verify_signature": False})
./platform/src/L09_api_gateway/services/authentication.py:128:                    ErrorCode.E9104, "Missing subject claim in JWT"
./platform/src/L09_api_gateway/services/authentication.py:143:            # Verify JWT signature with proper key
./platform/src/L09_api_gateway/services/authentication.py:144:            # This raises jwt.InvalidSignatureError if signature is invalid
./platform/src/L09_api_gateway/services/authentication.py:145:            decoded = jwt.decode(
./platform/src/L09_api_gateway/services/authentication.py:157:            # Signature and expiration verified successfully by jwt.decode above
./platform/src/L09_api_gateway/services/authentication.py:165:        except jwt.ExpiredSignatureError:
./platform/src/L09_api_gateway/services/authentication.py:169:        except jwt.InvalidSignatureError:
./platform/src/L09_api_gateway/services/authentication.py:171:                ErrorCode.E9104, "Invalid JWT signature"
./platform/src/L09_api_gateway/services/authentication.py:173:        except jwt.DecodeError as e:
## API Key Patterns
./platform/shared/clients/l01_client.py:18:    def __init__(self, base_url: str = "http://localhost:8002", timeout: float = 30.0, api_key: Optional[str] = None):
./platform/shared/clients/l01_client.py:21:        self.api_key = api_key
./platform/shared/clients/l01_client.py:28:            if self.api_key:
./platform/shared/clients/l01_client.py:29:                headers["X-API-Key"] = self.api_key
./platform/archive/l12-pre-v2/services/command_history.py:123:        "api_key",
./platform/src/L04_model_gateway/models/provider_config.py:82:    api_key_env_var: Optional[str] = None
./platform/src/L04_model_gateway/models/provider_config.py:101:            "api_key_env_var": self.api_key_env_var,
./platform/src/L04_model_gateway/providers/anthropic_adapter.py:34:        api_key: str = None,
./platform/src/L04_model_gateway/providers/anthropic_adapter.py:45:        self.api_key = api_key
./platform/src/L04_model_gateway/providers/openai_adapter.py:34:        api_key: str = None,
./platform/src/L04_model_gateway/providers/openai_adapter.py:45:        self.api_key = api_key
./platform/src/L06_evaluation/services/alert_manager.py:30:        pagerduty_api_key: Optional[str] = None,
./platform/src/L06_evaluation/services/alert_manager.py:38:            pagerduty_api_key: PagerDuty API key (optional)
./platform/src/L06_evaluation/services/alert_manager.py:42:        self.pagerduty_key = pagerduty_api_key
./platform/src/L09_api_gateway/models/consumer_models.py:13:    API_KEY = "api_key"
./platform/src/L09_api_gateway/models/consumer_models.py:49:    api_key_hash: Optional[str] = None  # bcrypt hash
./platform/src/L09_api_gateway/services/l01_bridge.py:28:    def __init__(self, l01_base_url: str = "http://localhost:8002", l01_api_key: Optional[str] = None):
./platform/src/L09_api_gateway/services/l01_bridge.py:33:            l01_api_key: API key for authenticating with L01
./platform/src/L09_api_gateway/services/l01_bridge.py:36:        if not l01_api_key:
./platform/src/L09_api_gateway/services/l01_bridge.py:38:            l01_api_key = os.getenv("L01_API_KEY")
./platform/src/L09_api_gateway/services/l01_bridge.py:40:        self.l01_client = L01Client(base_url=l01_base_url, api_key=l01_api_key)
./platform/src/L09_api_gateway/services/l01_bridge.py:42:        logger.info(f"L09Bridge initialized with base_url={l01_base_url}, auth={bool(l01_api_key)}")
./platform/src/L09_api_gateway/services/l01_bridge.py:163:            auth_method: Authentication method (api_key, oauth, jwt, etc.)
./platform/src/L09_api_gateway/services/authentication.py:47:            return await self._authenticate_api_key(
./platform/src/L09_api_gateway/services/authentication.py:64:            details={"supported_methods": ["api_key", "oauth_jwt", "mtls"]},
./platform/src/L09_api_gateway/services/authentication.py:67:    async def _authenticate_api_key(
./platform/src/L09_api_gateway/services/authentication.py:71:        api_key = auth_header.replace("Bearer ", "").strip()
./platform/src/L09_api_gateway/services/authentication.py:73:        if not api_key:
./platform/src/L09_api_gateway/services/authentication.py:78:        consumer = await consumer_lookup_fn(api_key=api_key)
./platform/src/L09_api_gateway/services/authentication.py:82:                ErrorCode.E9101, "Invalid API key", details={"key_prefix": api_key[:8]}
## Session Patterns
./platform/shared/clients/l01_client.py:157:        session_id: Optional[str] = None,
./platform/shared/clients/l01_client.py:189:        if session_id:
./platform/shared/clients/l01_client.py:190:            payload["session_id"] = session_id
./platform/shared/clients/l01_client.py:277:        session_id: Optional[str] = None,
./platform/shared/clients/l01_client.py:290:        if session_id:
./platform/shared/clients/l01_client.py:291:            params["session_id"] = session_id
./platform/shared/clients/l01_client.py:458:        session_id: Optional[str] = None,
./platform/shared/clients/l01_client.py:495:        if session_id:
./platform/shared/clients/l01_client.py:496:            payload["session_id"] = session_id
./platform/shared/clients/l01_client.py:687:    # Session methods
./platform/shared/clients/l01_client.py:688:    async def create_session(
./platform/shared/clients/l01_client.py:691:        session_type: str = "runtime",
./platform/shared/clients/l01_client.py:696:        """Create a new session."""
./platform/shared/clients/l01_client.py:698:        response = await client.post("/sessions/", json={
./platform/shared/clients/l01_client.py:700:            "session_type": session_type,
./platform/shared/clients/l01_client.py:708:    async def get_session(self, session_id: UUID) -> Dict[str, Any]:
./platform/shared/clients/l01_client.py:709:        """Get session by ID."""
./platform/shared/clients/l01_client.py:711:        response = await client.get(f"/sessions/{session_id}")
./platform/shared/clients/l01_client.py:715:    async def update_session(
./platform/shared/clients/l01_client.py:717:        session_id: UUID,
./platform/shared/clients/l01_client.py:723:        """Update session."""
./platform/shared/clients/l01_client.py:735:        response = await client.patch(f"/sessions/{session_id}", json=update_data)
./platform/shared/clients/l01_client.py:739:    async def list_sessions(
./platform/shared/clients/l01_client.py:744:        """List sessions."""
./platform/shared/clients/l01_client.py:749:        response = await client.get("/sessions/", params=params)
./platform/shared/clients/l01_client.py:1438:        session_id: Optional[str] = None,
./platform/shared/clients/l01_client.py:1467:        if session_id:
./platform/shared/clients/l01_client.py:1468:            payload["session_id"] = session_id
./platform/archive/l12-pre-v2/config/settings.py:9:    L12_SESSION_TTL_SECONDS: Session TTL in seconds (default: 3600)
./platform/archive/l12-pre-v2/config/settings.py:17:    L12_MEMORY_LIMIT_MB: Per-session memory limit in MB (default: 500)
## LLM Token Tracking
./platform/shared/clients/l01_client.py:447:    # Model usage methods
./platform/shared/clients/l01_client.py:448:    async def record_model_usage(
./platform/shared/clients/l01_client.py:473:        """Record model usage with rich metadata."""
./platform/shared/clients/l01_client.py:514:        response = await client.post("/models/usage", json=payload)
./platform/archive/l12-pre-v2/config/settings.py:21:    L12_ENABLE_L01_BRIDGE: Enable L01 usage tracking (default: true)
./platform/archive/l12-pre-v2/config/settings.py:63:        enable_l01_bridge: Enable L01 usage tracking
./platform/archive/l12-pre-v2/config/settings.py:152:        description="L01 Data Layer base URL for usage tracking",
./platform/archive/l12-pre-v2/config/settings.py:162:        description="Enable L01 usage tracking bridge",
./platform/archive/l12-pre-v2/core/session_manager.py:41:        memory_mb: Current memory usage in megabytes
./platform/archive/l12-pre-v2/core/session_manager.py:99:        memory_monitor: MemoryMonitor for tracking memory usage
./platform/archive/l12-pre-v2/interfaces/http_api.py:118:    # Initialize L01Bridge for usage tracking
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:121:                    "Services are grouped by usage (e.g., Data Storage, Agent Management, AI Models). "
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:205:                    "parameters, dependencies, and usage examples. "
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:240:                    "memory usage, and metrics. "
./platform/archive/l12-pre-v2/interfaces/mcp_server_stdio.py:511:            f"Memory usage: {metrics['memory_mb']:.2f} MB\n"
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:236:                    "Shows active services, memory usage, age, and metrics. "
./platform/archive/l12-pre-v2/interfaces/mcp_server.py:554:                f"Memory usage: {metrics['memory_mb']:.2f} MB\n"
./platform/archive/l12-pre-v2/models/service_metadata.py:100:        examples: Optional usage examples
./platform/archive/l12-pre-v2/models/command_models.py:259:        memory_usage_mb: Approximate memory usage in MB
./platform/archive/l12-pre-v2/models/command_models.py:267:        ...     memory_usage_mb=125.4
./platform/archive/l12-pre-v2/models/command_models.py:277:    memory_usage_mb: Optional[float] = Field(
./platform/archive/l12-pre-v2/models/command_models.py:279:        description="Memory usage in MB",
./platform/archive/l12-pre-v2/models/command_models.py:301:                "memory_usage_mb": 125.4
./platform/archive/l12-pre-v2/routing/command_router.py:88:            l01_bridge: Optional L12Bridge for usage tracking
./platform/archive/l12-pre-v2/services/memory_monitor.py:23:    """Snapshot of memory usage at a point in time.
./platform/archive/l12-pre-v2/services/memory_monitor.py:48:    The MemoryMonitor tracks memory usage per session to detect leaks and
./platform/archive/l12-pre-v2/services/memory_monitor.py:227:        A leak is detected if memory usage has grown by threshold_mb
./platform/archive/l12-pre-v2/services/l01_bridge.py:4:invocations to the L01 Data Layer. It records usage metrics including
./platform/archive/l12-pre-v2/services/l01_bridge.py:12:- Comprehensive usage metrics tracking
./platform/archive/l12-pre-v2/services/l01_bridge.py:159:    """Bridge for recording L12 usage to L01 Data Layer.
