# Security Audit
## Authentication Patterns
Found 658 auth-related code lines
## Authorization Patterns
Found 5251 authz-related code lines
## Input Validation
Found 13677 validation-related code lines
## Potential Hardcoded Secrets
Found 34 potential hardcoded passwords
## SQL Patterns
Found 10829 raw SQL patterns (review needed)
## CORS Configuration
./platform/archive/l12-pre-v2/interfaces/http_api.py:24:from fastapi.middleware.cors import CORSMiddleware
./platform/archive/l12-pre-v2/interfaces/http_api.py:195:        CORSMiddleware,
./platform/archive/l12-pre-v2/interfaces/http_api.py:196:        allow_origins=["*"],  # Configure appropriately for production
./platform/src/L02_runtime/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L02_runtime/main.py:20:    CORSMiddleware,
./platform/src/L02_runtime/main.py:21:    allow_origins=["*"],
./platform/src/L03_tool_execution/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L03_tool_execution/main.py:20:    CORSMiddleware,
./platform/src/L03_tool_execution/main.py:21:    allow_origins=["*"],
./platform/src/L04_model_gateway/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L04_model_gateway/main.py:20:    CORSMiddleware,
./platform/src/L04_model_gateway/main.py:21:    allow_origins=["*"],
./platform/src/L05_planning/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L05_planning/main.py:20:    CORSMiddleware,
./platform/src/L05_planning/main.py:21:    allow_origins=["*"],
./platform/src/L06_evaluation/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L06_evaluation/main.py:20:    CORSMiddleware,
./platform/src/L06_evaluation/main.py:21:    allow_origins=["*"],
./platform/src/L07_learning/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L07_learning/main.py:20:    CORSMiddleware,
./platform/src/L07_learning/main.py:21:    allow_origins=["*"],
./platform/src/L11_integration/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L11_integration/main.py:20:    CORSMiddleware,
./platform/src/L11_integration/main.py:21:    allow_origins=["*"],
./platform/src/L10_human_interface/main.py:6:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L10_human_interface/main.py:20:    CORSMiddleware,
./platform/src/L10_human_interface/main.py:21:    allow_origins=["*"],
./platform/src/L01_data_layer/main.py:11:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L01_data_layer/main.py:104:    CORSMiddleware,
./platform/src/L01_data_layer/main.py:105:    allow_origins=["*"],  # Configure appropriately for production
./platform/src/L12_nl_interface/interfaces/http_api.py:24:from fastapi.middleware.cors import CORSMiddleware
./platform/src/L12_nl_interface/interfaces/http_api.py:195:        CORSMiddleware,
./platform/src/L12_nl_interface/interfaces/http_api.py:196:        allow_origins=["*"],  # Configure appropriately for production
./platform/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py:13:class CORSMiddleware:
./platform/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py:17:        allow_origins: typing.Sequence[str] = (),
./platform/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py:32:        allow_all_origins = "*" in allow_origins
./platform/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py:63:        self.allow_origins = allow_origins
./platform/.venv/lib/python3.12/site-packages/starlette/middleware/cors.py:102:        return origin in self.allow_origins
./platform/.venv/lib/python3.12/site-packages/fastapi/middleware/cors.py:1:from starlette.middleware.cors import CORSMiddleware as CORSMiddleware  # noqa
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/commands/serving.py:89:    from fastapi.middleware.cors import CORSMiddleware
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/commands/serving.py:702:                CORSMiddleware,
./platform/services/mcp-document-consolidator/python/venv/lib/python3.12/site-packages/transformers/commands/serving.py:703:                allow_origins=["*"],
