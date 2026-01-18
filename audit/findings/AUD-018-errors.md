# Error Handling Audit
## Custom Exception Classes
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
./platform/src/L09_api_gateway/errors.py:140:class AuthorizationError(GatewayError):
./platform/src/L09_api_gateway/errors.py:146:class ValidationError(GatewayError):
./platform/src/L09_api_gateway/errors.py:152:class RateLimitError(GatewayError):
./platform/src/L09_api_gateway/errors.py:165:class CircuitBreakerError(GatewayError):

## Exception Handling Patterns
Found 18310 except clauses

## Bare Except (anti-pattern)
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
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/state_changes.py:138:            except:

## Error Code Definitions
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
./platform/src/L02_runtime/services/lifecycle_manager.py:290:                code="E2023",
./platform/src/L02_runtime/services/lifecycle_manager.py:297:                code="E2023",
./platform/src/L02_runtime/services/lifecycle_manager.py:328:                code="E2023",
./platform/src/L02_runtime/services/lifecycle_manager.py:352:                code="E2024",
./platform/src/L02_runtime/services/lifecycle_manager.py:362:                code="E2024",
./platform/src/L02_runtime/services/lifecycle_manager.py:369:                code="E2024",
./platform/src/L02_runtime/services/lifecycle_manager.py:401:                code="E2024",
./platform/src/L02_runtime/services/lifecycle_manager.py:421:                code="E2000",
./platform/src/L02_runtime/services/lifecycle_manager.py:442:                code="E2000",
./platform/src/L02_runtime/services/lifecycle_manager.py:490:                code="E2025",
./platform/src/L02_runtime/services/lifecycle_manager.py:498:                code="E2000",
./platform/src/L02_runtime/services/lifecycle_manager.py:521:                code="E2000",
./platform/src/L02_runtime/services/resource_manager.py:188:                code="E2070",
./platform/src/L02_runtime/services/resource_manager.py:224:                code="E2073",
./platform/src/L02_runtime/services/resource_manager.py:252:                code="E2070",
./platform/src/L02_runtime/services/resource_manager.py:418:                code="E2070",
./platform/src/L02_runtime/services/sandbox_manager.py:147:                code="E2040",
./platform/src/L02_runtime/services/sandbox_manager.py:165:                code="E2041",
./platform/src/L02_runtime/services/sandbox_manager.py:173:                code="E2042",
./platform/src/L02_runtime/services/sandbox_manager.py:180:                code="E2043",
./platform/src/L02_runtime/services/sandbox_manager.py:193:                code="E2044",
./platform/src/L02_runtime/services/session_bridge.py:186:                code="E2050",
./platform/src/L02_runtime/services/session_bridge.py:276:                code="E2052",
./platform/src/L02_runtime/services/session_bridge.py:311:                code="E2054",
./platform/src/L02_runtime/services/session_bridge.py:345:                code="E2053",
./platform/src/L02_runtime/services/state_manager.py:240:                    code="E2031",

## HTTP Error Responses
./platform/src/L09_api_gateway/services/idempotency.py:74:                    status_code=cached["status_code"],
./platform/src/L09_api_gateway/services/backend_executor.py:156:                status_code=response.status_code,
./platform/src/L09_api_gateway/services/response_formatter.py:109:            status_code=error.http_status,
./platform/src/L09_api_gateway/services/response_formatter.py:155:            status_code=202,
./platform/src/L09_api_gateway/services/l01_bridge.py:117:                status_code=status_code,
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
./platform/src/L09_api_gateway/routers/v1/goals.py:43:@router.post("/", status_code=201)
./platform/src/L09_api_gateway/routers/v1/goals.py:58:        raise HTTPException(status_code=500, detail=f"Failed to create goal: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/goals.py:77:        raise HTTPException(status_code=500, detail=f"Failed to list goals: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/goals.py:91:            raise HTTPException(status_code=404, detail="Goal not found")
./platform/src/L09_api_gateway/routers/v1/goals.py:92:        raise HTTPException(status_code=500, detail=f"Failed to get goal: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/goals.py:108:            raise HTTPException(status_code=404, detail="Goal not found")
./platform/src/L09_api_gateway/routers/v1/goals.py:109:        raise HTTPException(status_code=500, detail=f"Failed to update goal: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/agents.py:7:from fastapi import APIRouter, HTTPException, Header, Depends
./platform/src/L09_api_gateway/routers/v1/agents.py:41:        raise HTTPException(status_code=401, detail="Invalid API key")
./platform/src/L09_api_gateway/routers/v1/agents.py:45:@router.post("/", status_code=201)
./platform/src/L09_api_gateway/routers/v1/agents.py:60:        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/agents.py:78:        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/agents.py:92:            raise HTTPException(status_code=404, detail="Agent not found")
./platform/src/L09_api_gateway/routers/v1/agents.py:93:        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")
./platform/src/L09_api_gateway/routers/v1/agents.py:109:            raise HTTPException(status_code=404, detail="Agent not found")
