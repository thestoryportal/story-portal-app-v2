# Error Handling Audit
## Custom Exception Classes
./platform/archive/l12-pre-v2/core/service_factory.py:26:class DependencyError(Exception):
./platform/archive/l12-pre-v2/core/service_factory.py:32:class CircularDependencyError(DependencyError):
./platform/archive/l12-pre-v2/models/command_models.py:29:class ErrorCode(str, Enum):
./platform/archive/l12-pre-v2/models/command_models.py:118:class ErrorResponse(BaseModel):
./platform/src/L02_runtime/services/agent_executor.py:26:class ExecutorError(Exception):
./platform/src/L02_runtime/services/document_bridge.py:22:class DocumentError(Exception):
./platform/src/L02_runtime/services/fleet_manager.py:23:class FleetError(Exception):
./platform/src/L02_runtime/services/lifecycle_manager.py:30:class LifecycleError(Exception):
./platform/src/L02_runtime/services/resource_manager.py:46:class ResourceError(Exception):
./platform/src/L02_runtime/services/sandbox_manager.py:25:class SandboxError(Exception):
./platform/src/L02_runtime/services/session_bridge.py:25:class SessionError(Exception):
./platform/src/L02_runtime/services/state_manager.py:35:class StateError(Exception):
./platform/src/L02_runtime/services/warm_pool_manager.py:23:class WarmPoolError(Exception):
./platform/src/L02_runtime/services/workflow_engine.py:30:class WorkflowError(Exception):
./platform/src/L03_tool_execution/models/error_codes.py:12:class ErrorCode(Enum):
./platform/src/L03_tool_execution/models/error_codes.py:156:class ToolExecutionError(Exception):
./platform/src/L03_tool_execution/models/tool_result.py:28:class ToolError:
./platform/src/L03_tool_execution/tests/test_models.py:119:class TestToolExecutionError:
./platform/src/L04_model_gateway/models/error_codes.py:12:class ErrorCategory(Enum):
./platform/src/L04_model_gateway/models/error_codes.py:24:class L04ErrorCode(Enum):
./platform/src/L04_model_gateway/models/error_codes.py:119:class L04Error(Exception):
./platform/src/L04_model_gateway/models/error_codes.py:148:class ConfigurationError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:153:class RoutingError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:158:class ProviderError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:163:class CacheError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:168:class RateLimitError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:173:class ValidationError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:178:class ResponseError(L04Error):
./platform/src/L04_model_gateway/models/error_codes.py:183:class CircuitBreakerError(L04Error):
./platform/src/L05_planning/models/error_codes.py:22:class ErrorCode(str, Enum):
./platform/src/L05_planning/models/error_codes.py:208:class PlanningError(Exception):
./platform/src/L05_planning/services/plan_validator.py:29:class ValidationError:
./platform/src/L06_evaluation/models/error_codes.py:8:class ErrorCode(str, Enum):
./platform/src/L06_evaluation/models/error_codes.py:73:class ErrorCodeMetadata:
./platform/src/L06_evaluation/models/error_codes.py:83:class ErrorCodeRegistry:
./platform/src/L06_evaluation/services/event_validator.py:15:class ValidationError(Exception):
./platform/src/L07_learning/models/error_codes.py:7:class LearningErrorCode(Enum):
./platform/src/L07_learning/models/error_codes.py:90:class LearningLayerException(Exception):
./platform/src/L07_learning/models/error_codes.py:108:class TrainingDataExtractionError(LearningLayerException):
./platform/src/L07_learning/models/error_codes.py:113:class ExampleFilteringError(LearningLayerException):
./platform/src/L07_learning/models/error_codes.py:118:class ModelRegistryError(LearningLayerException):
./platform/src/L07_learning/models/error_codes.py:123:class RLHFError(LearningLayerException):
./platform/src/L07_learning/models/error_codes.py:128:class TrainingError(LearningLayerException):
./platform/src/L07_learning/models/error_codes.py:133:class ValidationError(LearningLayerException):
./platform/src/L07_learning/models/error_codes.py:138:class IntegrationError(LearningLayerException):
./platform/src/L09_api_gateway/models/response_models.py:27:class ErrorResponse(BaseModel):
./platform/src/L09_api_gateway/errors.py:24:class ErrorCode(str, Enum):
./platform/src/L09_api_gateway/errors.py:101:class GatewayError(Exception):
./platform/src/L09_api_gateway/errors.py:128:class RoutingError(GatewayError):
./platform/src/L09_api_gateway/errors.py:134:class AuthenticationError(GatewayError):
## Exception Handling Patterns
Found 18384 except clauses
## Bare Except (anti-pattern)
./platform/ui/node_modules/flatted/python/flatted.py:81:        except:
./platform/src/L10_human_interface/services/websocket_gateway.py:61:                except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:2058:            except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:2111:        except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/provision.py:226:        except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/postgresql/provision.py:56:            except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/engine/result.py:774:        except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/engine/result.py:803:                    except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/engine/util.py:146:            except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/event/attr.py:455:                except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/event/attr.py:502:                except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/loading.py:148:                    except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/loading.py:172:                    except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/session.py:1241:            except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/session.py:1298:            except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/session.py:1362:                    except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/session.py:2560:            except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/session.py:4465:        except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/session.py:4740:        except:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/state.py:595:        except:
## Error Code Definitions
./platform/shared/clients/l01_client.py:218:        error_code: Optional[str] = None,
./platform/shared/clients/l01_client.py:240:        if error_code is not None:
./platform/shared/clients/l01_client.py:241:            updates["error_code"] = error_code
./platform/shared/clients/l01_client.py:1280:        error_code: Optional[str] = None,
./platform/shared/clients/l01_client.py:1318:        if error_code:
./platform/shared/clients/l01_client.py:1319:            payload["error_code"] = error_code
./platform/archive/l12-pre-v2/core/service_factory.py:20:from ..models import ErrorCode, ServiceMetadata
./platform/archive/l12-pre-v2/models/__init__.py:20:- ErrorCode: Error code enum
./platform/archive/l12-pre-v2/models/__init__.py:33:    ErrorCode,
./platform/archive/l12-pre-v2/models/__init__.py:50:    "ErrorCode",
./platform/archive/l12-pre-v2/models/command_models.py:29:class ErrorCode(str, Enum):
./platform/archive/l12-pre-v2/models/command_models.py:122:        code: Error code from ErrorCode enum
./platform/archive/l12-pre-v2/models/command_models.py:131:        ...     code=ErrorCode.SERVICE_NOT_FOUND,
./platform/archive/l12-pre-v2/models/command_models.py:138:    code: ErrorCode = Field(..., description="Error code")
./platform/archive/l12-pre-v2/routing/command_router.py:30:    ErrorCode,
./platform/archive/l12-pre-v2/routing/command_router.py:134:                ErrorCode.INVALID_REQUEST,
./platform/archive/l12-pre-v2/routing/command_router.py:184:                    ErrorCode.SERVICE_NOT_FOUND,
./platform/archive/l12-pre-v2/routing/command_router.py:197:                    ErrorCode.METHOD_NOT_FOUND,
./platform/archive/l12-pre-v2/routing/command_router.py:211:                    ErrorCode.SERVICE_INIT_ERROR,
./platform/archive/l12-pre-v2/routing/command_router.py:270:                    ErrorCode.TIMEOUT,
./platform/archive/l12-pre-v2/routing/command_router.py:278:                    ErrorCode.EXECUTION_ERROR,
./platform/archive/l12-pre-v2/routing/command_router.py:290:                ErrorCode.INTERNAL_ERROR,
./platform/archive/l12-pre-v2/routing/command_router.py:450:        error_code: ErrorCode,
./platform/archive/l12-pre-v2/routing/command_router.py:460:            error_code: ErrorCode enum value
./platform/archive/l12-pre-v2/routing/command_router.py:470:            ...     ErrorCode.METHOD_NOT_FOUND, "Method not found"
./platform/archive/l12-pre-v2/routing/command_router.py:474:            code=error_code, message=message, details=details or {}
./platform/src/L02_runtime/services/agent_executor.py:203:                code="E2000",
./platform/src/L02_runtime/services/agent_executor.py:235:                code="E2003",
./platform/src/L02_runtime/services/agent_executor.py:253:                code="E2004",
./platform/src/L02_runtime/services/agent_executor.py:349:                code="E2001",
./platform/src/L02_runtime/services/agent_executor.py:383:            code="E2001",
./platform/src/L02_runtime/services/agent_executor.py:437:                code="E2002",
./platform/src/L02_runtime/services/agent_executor.py:444:                code="E2001",
./platform/src/L02_runtime/services/document_bridge.py:171:                code="E2060",
./platform/src/L02_runtime/services/document_bridge.py:204:                    code="E2063",
./platform/src/L02_runtime/services/document_bridge.py:215:                code="E2063",
./platform/src/L02_runtime/services/document_bridge.py:261:                    code="E2061",
./platform/src/L02_runtime/services/document_bridge.py:307:                code="E2062",
./platform/src/L02_runtime/services/document_bridge.py:353:                code="E2061",
./platform/src/L02_runtime/services/fleet_manager.py:230:                    code="E2090",
./platform/src/L02_runtime/services/fleet_manager.py:267:                code="E2090",
./platform/src/L02_runtime/services/fleet_manager.py:299:                    code="E2091",
./platform/src/L02_runtime/services/fleet_manager.py:334:                code="E2091",
./platform/src/L02_runtime/services/fleet_manager.py:368:                code="E2093",
./platform/src/L02_runtime/services/lifecycle_manager.py:179:                code="E2021",
./platform/src/L02_runtime/services/lifecycle_manager.py:184:                code="E2020",
./platform/src/L02_runtime/services/lifecycle_manager.py:190:                code="E2020",
./platform/src/L02_runtime/services/lifecycle_manager.py:217:                code="E2022",
./platform/src/L02_runtime/services/lifecycle_manager.py:256:                code="E2022",
./platform/src/L02_runtime/services/lifecycle_manager.py:280:                code="E2023",
## HTTP Error Responses
./platform/archive/l12-pre-v2/interfaces/http_api.py:23:from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
./platform/archive/l12-pre-v2/interfaces/http_api.py:247:            raise HTTPException(status_code=500, detail="Router not initialized")
./platform/archive/l12-pre-v2/interfaces/http_api.py:254:            raise HTTPException(status_code=500, detail=str(e))
./platform/archive/l12-pre-v2/interfaces/http_api.py:282:            raise HTTPException(status_code=500, detail="Fuzzy matcher not initialized")
./platform/archive/l12-pre-v2/interfaces/http_api.py:300:            raise HTTPException(status_code=500, detail=str(e))
./platform/archive/l12-pre-v2/interfaces/http_api.py:322:            raise HTTPException(status_code=500, detail="Registry not initialized")
./platform/archive/l12-pre-v2/interfaces/http_api.py:343:            raise HTTPException(status_code=500, detail=str(e))
./platform/archive/l12-pre-v2/interfaces/http_api.py:361:            raise HTTPException(status_code=500, detail="Registry not initialized")
./platform/archive/l12-pre-v2/interfaces/http_api.py:365:            raise HTTPException(
./platform/archive/l12-pre-v2/interfaces/http_api.py:366:                status_code=404, detail=f"Service '{service_name}' not found"
./platform/archive/l12-pre-v2/interfaces/http_api.py:387:            raise HTTPException(status_code=500, detail="Session manager not initialized")
./platform/archive/l12-pre-v2/interfaces/http_api.py:391:            raise HTTPException(
./platform/archive/l12-pre-v2/interfaces/http_api.py:392:                status_code=404, detail=f"Session '{session_id}' not found"
./platform/archive/l12-pre-v2/interfaces/http_api.py:410:            raise HTTPException(status_code=500, detail="Session manager not initialized")
./platform/archive/l12-pre-v2/interfaces/http_api.py:427:            raise HTTPException(status_code=500, detail="Session manager not initialized")
./platform/src/L09_api_gateway/services/l01_bridge.py:117:                status_code=status_code,
./platform/src/L09_api_gateway/services/idempotency.py:74:                    status_code=cached["status_code"],
./platform/src/L09_api_gateway/services/backend_executor.py:156:                status_code=response.status_code,
./platform/src/L09_api_gateway/services/response_formatter.py:109:            status_code=error.http_status,
./platform/src/L09_api_gateway/services/response_formatter.py:155:            status_code=202,
./platform/src/L09_api_gateway/gateway.py:9:from fastapi import FastAPI, Request, Response, HTTPException, status
./platform/src/L09_api_gateway/gateway.py:164:                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
./platform/src/L09_api_gateway/gateway.py:183:                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
./platform/src/L09_api_gateway/gateway.py:254:                        status_code=response.status_code,
./platform/src/L09_api_gateway/gateway.py:271:                    status_code=response.status_code,
./platform/src/L09_api_gateway/gateway.py:296:                    status_code=error_response.status_code,
./platform/src/L09_api_gateway/gateway.py:308:                    status_code=500,
./platform/src/L09_api_gateway/gateway.py:411:            status_code=200,
./platform/src/L09_api_gateway/routers/v1/goals.py:7:from fastapi import APIRouter, HTTPException, Header, Depends
./platform/src/L09_api_gateway/routers/v1/goals.py:39:        raise HTTPException(status_code=401, detail="Invalid API key")
