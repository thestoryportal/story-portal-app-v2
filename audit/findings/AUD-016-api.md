# API Endpoint Audit
## FastAPI Route Definitions
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
./platform/src/L11_integration/app.py:165:@app.get("/health/live")
./platform/src/L11_integration/app.py:171:@app.get("/health/ready")
./platform/src/L11_integration/app.py:197:@app.get("/health/detailed")
./platform/src/L11_integration/app.py:229:@app.get("/services")
./platform/src/L11_integration/app.py:249:@app.get("/metrics")
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
./platform/src/L01_data_layer/routers/goals.py:64:@router.get("/{goal_id}")
./platform/src/L01_data_layer/routers/goals.py:76:@router.patch("/{goal_id}")
./platform/src/L01_data_layer/routers/goals.py:112:@router.get("/")
./platform/src/L01_data_layer/routers/plans.py:14:@router.post("/", status_code=201)
./platform/src/L01_data_layer/routers/plans.py:59:@router.get("/{plan_id}")
./platform/src/L01_data_layer/routers/plans.py:71:@router.patch("/{plan_id}")
./platform/src/L01_data_layer/routers/plans.py:152:@router.get("/")
./platform/src/L01_data_layer/routers/evaluations.py:14:@router.post("/", response_model=Evaluation, status_code=201)
./platform/src/L01_data_layer/routers/evaluations.py:18:@router.get("/", response_model=list[Evaluation])
./platform/src/L01_data_layer/routers/evaluations.py:22:@router.get("/{evaluation_id}", response_model=Evaluation)
./platform/src/L01_data_layer/routers/evaluations.py:29:@router.get("/agent/{agent_id}/stats")
./platform/src/L01_data_layer/routers/feedback.py:14:@router.post("/", response_model=FeedbackEntry, status_code=201)
./platform/src/L01_data_layer/routers/feedback.py:18:@router.get("/", response_model=list[FeedbackEntry])
./platform/src/L01_data_layer/routers/feedback.py:22:@router.get("/unprocessed", response_model=list[FeedbackEntry])
./platform/src/L01_data_layer/routers/feedback.py:26:@router.get("/{feedback_id}", response_model=FeedbackEntry)
./platform/src/L01_data_layer/routers/feedback.py:33:@router.patch("/{feedback_id}", response_model=FeedbackEntry)
./platform/src/L01_data_layer/routers/documents.py:13:@router.post("/", response_model=Document, status_code=201)
./platform/src/L01_data_layer/routers/documents.py:17:@router.get("/", response_model=list[Document])
./platform/src/L01_data_layer/routers/documents.py:21:@router.get("/{document_id}", response_model=Document)
./platform/src/L01_data_layer/routers/documents.py:28:@router.patch("/{document_id}", response_model=Document)
./platform/src/L01_data_layer/routers/documents.py:35:@router.delete("/{document_id}", status_code=204)
./platform/src/L01_data_layer/routers/sessions.py:15:@router.post("/", response_model=Session, status_code=201)
./platform/src/L01_data_layer/routers/sessions.py:19:@router.get("/", response_model=list[Session])
./platform/src/L01_data_layer/routers/sessions.py:23:@router.get("/{session_id}", response_model=Session)
./platform/src/L01_data_layer/routers/sessions.py:30:@router.patch("/{session_id}", response_model=Session)
./platform/src/L01_data_layer/routers/models.py:13:@router.post("/usage", status_code=201)
./platform/src/L01_data_layer/routers/models.py:65:@router.get("/usage")
./platform/src/L01_data_layer/routers/models.py:119:@router.get("/usage/{request_id}")
./platform/src/L01_data_layer/routers/training_examples.py:17:@router.post("/", response_model=TrainingExample, status_code=201)
./platform/src/L01_data_layer/routers/training_examples.py:26:@router.get("/", response_model=list[TrainingExample])
./platform/src/L01_data_layer/routers/training_examples.py:47:@router.get("/statistics")
./platform/src/L01_data_layer/routers/training_examples.py:55:@router.get("/{example_id}", response_model=TrainingExample)
./platform/src/L01_data_layer/routers/training_examples.py:67:@router.patch("/{example_id}", response_model=TrainingExample)
./platform/src/L01_data_layer/routers/training_examples.py:80:@router.delete("/{example_id}", status_code=204)
./platform/src/L01_data_layer/routers/datasets.py:17:@router.post("/", response_model=Dataset, status_code=201)
./platform/src/L01_data_layer/routers/datasets.py:26:@router.get("/", response_model=list[Dataset])
./platform/src/L01_data_layer/routers/datasets.py:43:@router.get("/statistics")
./platform/src/L01_data_layer/routers/datasets.py:51:@router.get("/{dataset_id}", response_model=Dataset)
./platform/src/L01_data_layer/routers/datasets.py:63:@router.patch("/{dataset_id}", response_model=Dataset)
./platform/src/L01_data_layer/routers/datasets.py:76:@router.delete("/{dataset_id}", status_code=204)
./platform/src/L01_data_layer/routers/datasets.py:87:@router.post("/{dataset_id}/examples/{example_id}")
./platform/src/L01_data_layer/routers/datasets.py:98:@router.delete("/{dataset_id}/examples/{example_id}", status_code=204)
./platform/src/L01_data_layer/routers/datasets.py:110:@router.get("/{dataset_id}/examples", response_model=List[UUID])
./platform/src/L01_data_layer/routers/datasets.py:120:@router.get("/{dataset_id}/split-counts")
./platform/src/L01_data_layer/routers/anomalies.py:13:@router.post("/", status_code=201)
./platform/src/L01_data_layer/routers/anomalies.py:59:@router.get("/{anomaly_id}")
./platform/src/L01_data_layer/routers/anomalies.py:71:@router.patch("/{anomaly_id}")
./platform/src/L01_data_layer/routers/anomalies.py:113:@router.get("/")
./platform/src/L01_data_layer/routers/quality_scores.py:14:@router.post("/", status_code=201)
./platform/src/L01_data_layer/routers/quality_scores.py:56:@router.get("/{score_id}")
./platform/src/L01_data_layer/routers/quality_scores.py:68:@router.get("/")

## Route Counts
GET routes:      120
POST routes:       42
PUT routes:        5
DELETE routes:        8

## OpenAPI Specifications

## Health Endpoints
./platform/src/L02_runtime/services/health_monitor.py:69:        self.liveness_path = liveness_config.get("path", "/healthz")
./platform/src/L02_runtime/services/health_monitor.py:76:        self.readiness_path = readiness_config.get("path", "/ready")
./platform/src/L09_api_gateway/gateway.py:139:        @self.app.get("/health/live")
./platform/src/L09_api_gateway/gateway.py:146:        @self.app.get("/health/ready")
./platform/src/L09_api_gateway/gateway.py:178:        @self.app.get("/health/startup")
./platform/src/L09_api_gateway/gateway.py:189:        @self.app.get("/health/detailed")
./platform/src/L11_integration/tests/test_integration.py:83:                endpoint="http://localhost:8002/health",
./platform/src/L11_integration/examples/basic_usage.py:50:                    endpoint="http://localhost:8002/health",
./platform/src/L11_integration/examples/basic_usage.py:60:                    endpoint="http://localhost:8003/health",
./platform/src/L11_integration/app.py:165:@app.get("/health/live")
./platform/src/L11_integration/app.py:171:@app.get("/health/ready")
./platform/src/L11_integration/app.py:197:@app.get("/health/detailed")
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
./platform/src/L12_nl_interface/config/settings.py:369:                response = httpx.get(f"{self.l01_base_url}/health", timeout=2.0)
./platform/src/L12_nl_interface/config/settings.py:377:                response = httpx.get(f"{self.l04_base_url}/health", timeout=2.0)
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
