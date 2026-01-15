"""API routers for L01 Data Layer."""

from .health import router as health_router
from .events import router as events_router
from .agents import router as agents_router
from .tools import router as tools_router
from .config import router as config_router
from .goals import router as goals_router
from .plans import router as plans_router
from .evaluations import router as evaluations_router
from .feedback import router as feedback_router
from .documents import router as documents_router
from .sessions import router as sessions_router
from .training_examples import router as training_examples_router
from .datasets import router as datasets_router
from .models import router as models_router

# L06 Evaluation routers
from .quality_scores import router as quality_scores_router
from .metrics import router as metrics_router
from .anomalies import router as anomalies_router
from .compliance_results import router as compliance_results_router
from .alerts import router as alerts_router

# L09 API Gateway routers
from .api_requests import router as api_requests_router
from .authentication_events import router as authentication_events_router
from .rate_limit_events import router as rate_limit_events_router

# L10 Human Interface routers
from .user_interactions import router as user_interactions_router
from .control_operations import router as control_operations_router

# L11 Integration Layer routers
from .saga_executions import router as saga_executions_router
from .saga_steps import router as saga_steps_router
from .circuit_breaker_events import router as circuit_breaker_events_router
from .service_registry_events import router as service_registry_events_router

__all__ = [
    "health_router",
    "events_router",
    "agents_router",
    "tools_router",
    "config_router",
    "goals_router",
    "plans_router",
    "evaluations_router",
    "feedback_router",
    "documents_router",
    "sessions_router",
    "training_examples_router",
    "datasets_router",
    "models_router",
    # L06 Evaluation
    "quality_scores_router",
    "metrics_router",
    "anomalies_router",
    "compliance_results_router",
    "alerts_router",
    # L09 API Gateway
    "api_requests_router",
    "authentication_events_router",
    "rate_limit_events_router",
    # L10 Human Interface
    "user_interactions_router",
    "control_operations_router",
    # L11 Integration Layer
    "saga_executions_router",
    "saga_steps_router",
    "circuit_breaker_events_router",
    "service_registry_events_router",
]
