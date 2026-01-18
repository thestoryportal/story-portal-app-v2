# API Endpoint Audit
## FastAPI Route Definitions
./platform/archive/l12-pre-v2/interfaces/http_api.py:203:    @app.get("/health", response_model=HealthResponse, tags=["Health"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:226:    @app.post("/v1/services/invoke", response_model=InvokeResponse, tags=["Services"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:257:    @app.get("/v1/services/search", response_model=List[SearchResult], tags=["Services"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:303:    @app.get("/v1/services", response_model=List[ServiceListItem], tags=["Services"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:346:    @app.get("/v1/services/{service_name}", response_model=ServiceMetadata, tags=["Services"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:372:    @app.get("/v1/sessions/{session_id}", tags=["Sessions"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:398:    @app.get("/v1/sessions", tags=["Sessions"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:415:    @app.get("/v1/metrics", tags=["Metrics"])
./platform/archive/l12-pre-v2/interfaces/http_api.py:432:    @app.websocket("/v1/ws/{session_id}")
./platform/src/L02_runtime/main.py:27:@app.get("/health/live")
./platform/src/L02_runtime/main.py:32:@app.get("/health/ready")
./platform/src/L02_runtime/main.py:37:@app.get("/")
./platform/src/L02_runtime/main.py:46:@app.on_event("startup")
./platform/src/L02_runtime/main.py:51:@app.on_event("shutdown")
./platform/src/L03_tool_execution/main.py:27:@app.get("/health/live")
./platform/src/L03_tool_execution/main.py:32:@app.get("/health/ready")
./platform/src/L03_tool_execution/main.py:37:@app.get("/")
./platform/src/L03_tool_execution/main.py:46:@app.on_event("startup")
./platform/src/L03_tool_execution/main.py:51:@app.on_event("shutdown")
./platform/src/L04_model_gateway/main.py:27:@app.get("/health/live")
./platform/src/L04_model_gateway/main.py:32:@app.get("/health/ready")
./platform/src/L04_model_gateway/main.py:37:@app.get("/")
./platform/src/L04_model_gateway/main.py:46:@app.on_event("startup")
./platform/src/L04_model_gateway/main.py:51:@app.on_event("shutdown")
./platform/src/L05_planning/main.py:27:@app.get("/health/live")
./platform/src/L05_planning/main.py:32:@app.get("/health/ready")
./platform/src/L05_planning/main.py:37:@app.get("/")
./platform/src/L05_planning/main.py:46:@app.on_event("startup")
./platform/src/L05_planning/main.py:51:@app.on_event("shutdown")
./platform/src/L06_evaluation/main.py:27:@app.get("/health/live")
./platform/src/L06_evaluation/main.py:32:@app.get("/health/ready")
./platform/src/L06_evaluation/main.py:37:@app.get("/")
./platform/src/L06_evaluation/main.py:46:@app.on_event("startup")
./platform/src/L06_evaluation/main.py:51:@app.on_event("shutdown")
./platform/src/L07_learning/main.py:27:@app.get("/health/live")
./platform/src/L07_learning/main.py:32:@app.get("/health/ready")
./platform/src/L07_learning/main.py:37:@app.get("/")
./platform/src/L07_learning/main.py:46:@app.on_event("startup")
./platform/src/L07_learning/main.py:51:@app.on_event("shutdown")
./platform/src/L09_api_gateway/main.py:27:@app.on_event("startup")
./platform/src/L09_api_gateway/main.py:34:@app.on_event("shutdown")
./platform/src/L09_api_gateway/app.py:15:@app.on_event("startup")
./platform/src/L09_api_gateway/app.py:22:@app.on_event("shutdown")
./platform/src/L09_api_gateway/routers/v1/goals.py:43:@router.post("/", status_code=201)
./platform/src/L09_api_gateway/routers/v1/goals.py:61:@router.get("/")
./platform/src/L09_api_gateway/routers/v1/goals.py:80:@router.get("/{goal_id}")
./platform/src/L09_api_gateway/routers/v1/goals.py:95:@router.patch("/{goal_id}")
./platform/src/L09_api_gateway/routers/v1/agents.py:45:@router.post("/", status_code=201)
./platform/src/L09_api_gateway/routers/v1/agents.py:63:@router.get("/")
./platform/src/L09_api_gateway/routers/v1/agents.py:81:@router.get("/{agent_id}")
./platform/src/L09_api_gateway/routers/v1/agents.py:96:@router.patch("/{agent_id}")
./platform/src/L09_api_gateway/routers/v1/agents.py:113:@router.delete("/{agent_id}", status_code=204)
./platform/src/L09_api_gateway/routers/v1/tasks.py:42:@router.post("/", status_code=201)
./platform/src/L09_api_gateway/routers/v1/tasks.py:61:@router.get("/{task_id}")
./platform/src/L09_api_gateway/routers/v1/tasks.py:76:@router.patch("/{task_id}")
./platform/src/L11_integration/main.py:27:@app.get("/health/live")
./platform/src/L11_integration/main.py:32:@app.get("/health/ready")
./platform/src/L11_integration/main.py:37:@app.get("/")
./platform/src/L11_integration/main.py:46:@app.on_event("startup")
./platform/src/L11_integration/main.py:51:@app.on_event("shutdown")
./platform/src/L11_integration/app.py:165:@app.get("/health/live")
./platform/src/L11_integration/app.py:171:@app.get("/health/ready")
./platform/src/L11_integration/app.py:197:@app.get("/health/detailed")
./platform/src/L11_integration/app.py:229:@app.get("/services")
./platform/src/L11_integration/app.py:249:@app.get("/metrics")
./platform/src/L10_human_interface/main.py:27:@app.get("/health/live")
./platform/src/L10_human_interface/main.py:32:@app.get("/health/ready")
./platform/src/L10_human_interface/main.py:37:@app.get("/")
./platform/src/L10_human_interface/main.py:46:@app.on_event("startup")
./platform/src/L10_human_interface/main.py:51:@app.on_event("shutdown")
./platform/src/L10_human_interface/app.py:146:@app.get("/", response_class=HTMLResponse)
./platform/src/L10_human_interface/app.py:152:@app.get("/health/live")
./platform/src/L10_human_interface/app.py:158:@app.get("/health/ready")
./platform/src/L10_human_interface/app.py:183:@app.get("/api/agents")
./platform/src/L10_human_interface/app.py:218:@app.get("/api/agents/{agent_id}")
./platform/src/L10_human_interface/app.py:254:@app.get("/api/goals")
./platform/src/L10_human_interface/app.py:289:@app.websocket("/ws")
./platform/src/L01_data_layer/routers/health.py:9:@router.get("/live")
./platform/src/L01_data_layer/routers/health.py:14:@router.get("/ready")
./platform/src/L01_data_layer/routers/events.py:17:@router.post("/", response_model=Event, status_code=201)
./platform/src/L01_data_layer/routers/events.py:21:@router.get("/", response_model=list[Event])
./platform/src/L01_data_layer/routers/events.py:32:@router.get("/{event_id}", response_model=Event)
./platform/src/L01_data_layer/routers/agents.py:17:@router.post("/", response_model=Agent, status_code=201)
./platform/src/L01_data_layer/routers/agents.py:21:@router.get("/", response_model=list[Agent])
./platform/src/L01_data_layer/routers/agents.py:30:@router.get("/{agent_id}", response_model=Agent)
./platform/src/L01_data_layer/routers/agents.py:37:@router.patch("/{agent_id}", response_model=Agent)
./platform/src/L01_data_layer/routers/agents.py:44:@router.delete("/{agent_id}", status_code=204)
./platform/src/L01_data_layer/routers/tools.py:17:@router.post("/", response_model=Tool, status_code=201)
./platform/src/L01_data_layer/routers/tools.py:21:@router.get("/", response_model=list[Tool])
./platform/src/L01_data_layer/routers/tools.py:25:@router.get("/{tool_id}", response_model=Tool)
./platform/src/L01_data_layer/routers/tools.py:32:@router.patch("/{tool_id}", response_model=Tool)
./platform/src/L01_data_layer/routers/tools.py:39:@router.post("/tool-executions", response_model=ToolExecution, status_code=201)
./platform/src/L01_data_layer/routers/tools.py:43:@router.get("/tool-executions/{execution_id}", response_model=ToolExecution)
./platform/src/L01_data_layer/routers/tools.py:50:@router.get("/executions/by-invocation/{invocation_id}", response_model=ToolExecution)
./platform/src/L01_data_layer/routers/tools.py:58:@router.patch("/executions/{invocation_id}", response_model=ToolExecution)
./platform/src/L01_data_layer/routers/tools.py:70:@router.get("/executions", response_model=list[ToolExecution])
./platform/src/L01_data_layer/routers/config.py:12:@router.get("/{namespace}/{key}", response_model=Configuration)
./platform/src/L01_data_layer/routers/config.py:19:@router.put("/{namespace}/{key}", response_model=Configuration)
./platform/src/L01_data_layer/routers/config.py:24:@router.get("/{namespace}", response_model=list[Configuration])
./platform/src/L01_data_layer/routers/goals.py:13:@router.post("/", status_code=201)
## Route Counts
GET routes:      151
POST routes:       43
## OpenAPI Specifications
PUT routes:        5
## Health Endpoints
DELETE routes:        8
./platform/archive/l12-pre-v2/config/settings.py:369:                response = httpx.get(f"{self.l01_base_url}/health", timeout=2.0)
./platform/archive/l12-pre-v2/config/settings.py:377:                response = httpx.get(f"{self.l04_base_url}/health", timeout=2.0)
./platform/archive/l12-pre-v2/interfaces/http_api.py:10:GET /health - Health check
./platform/archive/l12-pre-v2/interfaces/http_api.py:203:    @app.get("/health", response_model=HealthResponse, tags=["Health"])
./platform/archive/l12-pre-v2/services/l01_bridge.py:458:                f"{self.base_url}/health", timeout=2.0
./platform/src/L02_runtime/main.py:27:@app.get("/health/live")
./platform/src/L02_runtime/main.py:32:@app.get("/health/ready")
./platform/src/L02_runtime/services/health_monitor.py:69:        self.liveness_path = liveness_config.get("path", "/healthz")
./platform/src/L02_runtime/services/health_monitor.py:76:        self.readiness_path = readiness_config.get("path", "/ready")
./platform/src/L03_tool_execution/main.py:27:@app.get("/health/live")
./platform/src/L03_tool_execution/main.py:32:@app.get("/health/ready")
./platform/src/L04_model_gateway/main.py:27:@app.get("/health/live")
./platform/src/L04_model_gateway/main.py:32:@app.get("/health/ready")
./platform/src/L05_planning/main.py:27:@app.get("/health/live")
./platform/src/L05_planning/main.py:32:@app.get("/health/ready")
./platform/src/L06_evaluation/main.py:27:@app.get("/health/live")
./platform/src/L06_evaluation/main.py:32:@app.get("/health/ready")
./platform/src/L07_learning/main.py:27:@app.get("/health/live")
./platform/src/L07_learning/main.py:32:@app.get("/health/ready")
./platform/src/L09_api_gateway/gateway.py:139:        @self.app.get("/health/live")
./platform/src/L09_api_gateway/gateway.py:146:        @self.app.get("/health/ready")
./platform/src/L09_api_gateway/gateway.py:178:        @self.app.get("/health/startup")
./platform/src/L09_api_gateway/gateway.py:189:        @self.app.get("/health/detailed")
./platform/src/L11_integration/main.py:27:@app.get("/health/live")
./platform/src/L11_integration/main.py:32:@app.get("/health/ready")
./platform/src/L11_integration/tests/test_integration.py:83:                endpoint="http://localhost:8002/health",
./platform/src/L11_integration/examples/basic_usage.py:50:                    endpoint="http://localhost:8002/health",
./platform/src/L11_integration/examples/basic_usage.py:60:                    endpoint="http://localhost:8003/health",
./platform/src/L11_integration/app.py:165:@app.get("/health/live")
./platform/src/L11_integration/app.py:171:@app.get("/health/ready")
./platform/src/L11_integration/app.py:197:@app.get("/health/detailed")
./platform/src/L10_human_interface/main.py:27:@app.get("/health/live")
./platform/src/L10_human_interface/main.py:32:@app.get("/health/ready")
./platform/src/L10_human_interface/app.py:152:@app.get("/health/live")
./platform/src/L10_human_interface/app.py:158:@app.get("/health/ready")
./platform/src/agents/qa/api_tester.py:27:            {"path": "/health/live", "method": "GET", "expected_status": 200},
./platform/src/agents/qa/api_tester.py:28:            {"path": "/health/ready", "method": "GET", "expected_status": 200},
./platform/src/agents/qa/api_tester.py:70:                {"action": "GET /health/live", "assert": "status == 200"},
./platform/src/agents/qa/api_tester.py:71:                {"action": "GET /health/ready", "assert": "status == 200 or 503"},
./platform/src/agents/qa/deploy_qa_swarm.py:28:            "L09 API Gateway (8000)": f"{self.base_url}/health/live",
./platform/src/agents/qa/deploy_qa_swarm.py:29:            "L01 Data Layer (8001)": "http://localhost:8001/health/live",
./platform/src/agents/qa/deploy_qa_swarm.py:30:            "L05 Orchestration (8006)": "http://localhost:8006/health/live",
./platform/src/agents/qa/deploy_qa_swarm.py:207:            response = requests.get(f"{url}/health/live", timeout=2)
./platform/src/L01_data_layer/routers/health.py:7:router = APIRouter(prefix="/health", tags=["health"])
./platform/src/L01_data_layer/routers/health.py:9:@router.get("/live")
./platform/src/L01_data_layer/routers/health.py:14:@router.get("/ready")
./platform/src/L01_data_layer/main.py:163:            "health": "/health/live, /health/ready",
./platform/src/L01_data_layer/middleware/auth.py:31:            "/health/live",
./platform/src/L01_data_layer/middleware/auth.py:32:            "/health/ready",
./platform/src/L01_data_layer/middleware/auth.py:33:            "/health/startup",
./platform/src/L12_nl_interface/config/settings.py:422:                response = httpx.get(f"{self.l01_base_url}/health", timeout=2.0)
./platform/src/L12_nl_interface/config/settings.py:430:                response = httpx.get(f"{self.l04_base_url}/health", timeout=2.0)
./platform/src/L12_nl_interface/interfaces/http_api.py:10:GET /health - Health check
./platform/src/L12_nl_interface/interfaces/http_api.py:203:    @app.get("/health", response_model=HealthResponse, tags=["Health"])
./platform/src/L12_nl_interface/services/l01_bridge.py:458:                f"{self.base_url}/health", timeout=2.0
./platform/tests/e2e/test_simple_workflow.py:101:        response = await client.get("/health")
./platform/.venv/lib/python3.12/site-packages/pip/_vendor/pygments/lexers/_mapping.py:291:    'LiveScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'LiveScript', ('livescript', 'live-script'), ('*.ls',), ('text/livescript',)),
./platform/.venv/lib/python3.12/site-packages/pygments/lexers/_mapping.py:291:    'LiveScriptLexer': ('pygments.lexers.javascript', 'LiveScript', ('livescript', 'live-script'), ('*.ls',), ('text/livescript',)),
./platform/.venv/lib/python3.12/site-packages/pygments/lexers/javascript.py:318:    url = 'https://livescript.net/'
./platform/.venv/lib/python3.12/site-packages/pygments/lexers/javascript.py:321:    mimetypes = ['text/livescript']
./platform/.venv/lib/python3.12/site-packages/prometheus_client/multiprocess.py:115:                    else:  # all/liveall
./platform/.venv/lib/python3.12/site-packages/_pytest/logging.py:657:        # CLI/live logging.
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/pip/_vendor/pygments/lexers/_mapping.py:291:    'LiveScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'LiveScript', ('livescript', 'live-script'), ('*.ls',), ('text/livescript',)),
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/huggingface_hub/hf_api.py:7639:            ...         "health_route": "/health",
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/huggingface_hub/inference/_client.py:3338:        url = model.rstrip("/") + "/health"
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/huggingface_hub/inference/_generated/_async_client.py:3447:        url = model.rstrip("/") + "/health"
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/commands/serving.py:754:        @app.get("/health")
