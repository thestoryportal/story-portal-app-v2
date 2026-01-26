"""
L05 Planning Service - V2 API
Path: platform/src/L05_planning/main.py

V2 API endpoints for plan parsing, execution, and management.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .parsers.multi_format_parser import MultiFormatParser, ParseError
from .services.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStatus,
    ExecutionContext,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="L05 Planning Service",
    description="V2 Planning service with multi-format parsing, atomic unit decomposition, and validated execution",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator: Optional[PipelineOrchestrator] = None


# ==================== Request/Response Models ====================

class ParseRequest(BaseModel):
    """Request to parse a plan markdown."""
    markdown: str = Field(..., description="Plan markdown content")


class ParseResponse(BaseModel):
    """Response from parsing a plan."""
    success: bool
    plan_id: str
    format_type: str
    step_count: int
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    """Request to execute a plan."""
    markdown: str = Field(..., description="Plan markdown content")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context variables")
    dry_run: bool = Field(default=False, description="Run in dry-run mode (no actual execution)")
    stop_on_failure: bool = Field(default=True, description="Stop execution on first failure")
    quality_threshold: float = Field(default=70.0, description="Minimum quality score for success")


class ExecuteResponse(BaseModel):
    """Response from plan execution."""
    execution_id: str
    plan_id: str
    status: str
    total_units: int
    passed_units: int
    failed_units: int
    skipped_units: int
    average_score: float
    overall_assessment: Optional[str]
    duration_ms: int
    unit_results: List[Dict[str, Any]]


class StatusResponse(BaseModel):
    """Response with execution status."""
    execution_id: str
    plan_id: str
    status: str
    total_units: int
    passed_units: int
    failed_units: int
    average_score: float
    overall_assessment: Optional[str]
    duration_ms: int


class RollbackRequest(BaseModel):
    """Request to rollback an execution."""
    pass


class RollbackResponse(BaseModel):
    """Response from rollback operation."""
    success: bool
    execution_id: str
    message: str


class TraceResponse(BaseModel):
    """Response with execution trace."""
    execution_id: str
    plan_id: str
    events: List[Dict[str, Any]]
    checkpoints: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    components: Dict[str, Any] = Field(default_factory=dict)


# ==================== Health Endpoints ====================

@app.get("/health", response_model=HealthResponse)
async def health():
    """Comprehensive health check endpoint."""
    components = {}

    if orchestrator:
        stats = orchestrator.get_statistics()
        components = {
            "orchestrator": "healthy",
            "bridges": stats.get("bridges", {}),
            "total_executions": stats.get("total_executions", 0),
        }
    else:
        components["orchestrator"] = "not_initialized"

    return HealthResponse(
        status="healthy",
        service="l05-planning",
        version="2.0.0",
        components=components,
    )


@app.get("/health/live")
async def health_live():
    """Liveness probe."""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe."""
    if orchestrator and orchestrator._initialized:
        return {"status": "ready"}
    return {"status": "not_ready"}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "l05-planning",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "v2": {
                "parse": "POST /v2/plans/parse",
                "execute": "POST /v2/plans/execute",
                "status": "GET /v2/plans/{id}/status",
                "rollback": "POST /v2/plans/{id}/rollback",
                "trace": "GET /v2/plans/{id}/trace",
            },
            "health": {
                "health": "GET /health",
                "live": "GET /health/live",
                "ready": "GET /health/ready",
            },
        },
    }


# ==================== V2 API Endpoints ====================

@app.post("/v2/plans/parse", response_model=ParseResponse)
async def parse_plan(request: ParseRequest):
    """
    Parse a plan markdown into a structured format.

    Returns the parsed plan with detected format type and extracted steps.
    """
    try:
        parser = MultiFormatParser()
        parsed_plan = parser.parse(request.markdown)

        return ParseResponse(
            success=True,
            plan_id=parsed_plan.plan_id,
            format_type=parsed_plan.format_type.value,
            step_count=len(parsed_plan.steps),
            steps=[
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "files": step.files,
                    "acceptance_criteria": step.acceptance_criteria,
                    "dependencies": step.dependencies,
                }
                for step in parsed_plan.steps
            ],
            metadata=parsed_plan.metadata,
        )

    except ParseError as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    except Exception as e:
        logger.error(f"Parse failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/v2/plans/execute", response_model=ExecuteResponse)
async def execute_plan(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """
    Execute a plan through the V2 pipeline.

    Steps:
    1. Parse markdown
    2. Decompose into atomic units
    3. Execute each unit with validation
    4. Score quality with L06
    5. Return results
    """
    global orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        context = ExecutionContext(
            working_dir=Path.cwd(),
            dry_run=request.dry_run,
            stop_on_failure=request.stop_on_failure,
            quality_threshold=request.quality_threshold,
            variables=request.context,
        )

        result = await orchestrator.execute_plan_markdown(
            markdown=request.markdown,
            context=context,
        )

        return ExecuteResponse(
            execution_id=result.execution_id,
            plan_id=result.plan_id,
            status=result.status.value,
            total_units=result.total_units,
            passed_units=result.passed_units,
            failed_units=result.failed_units,
            skipped_units=result.skipped_units,
            average_score=result.average_score,
            overall_assessment=result.overall_assessment.value if result.overall_assessment else None,
            duration_ms=result.duration_ms,
            unit_results=[
                {
                    "unit_id": ur.unit_id,
                    "unit_title": ur.unit_title,
                    "status": ur.status.value,
                    "quality_score": ur.quality_score,
                    "error": ur.error,
                    "duration_ms": ur.duration_ms,
                    "checkpoint_hash": ur.checkpoint_hash,
                }
                for ur in result.unit_results
            ],
        )

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


@app.get("/v2/plans/{execution_id}/status", response_model=StatusResponse)
async def get_execution_status(execution_id: str):
    """
    Get the status of a plan execution.
    """
    global orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    result = await orchestrator.get_execution_status(execution_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return StatusResponse(
        execution_id=result.execution_id,
        plan_id=result.plan_id,
        status=result.status.value,
        total_units=result.total_units,
        passed_units=result.passed_units,
        failed_units=result.failed_units,
        average_score=result.average_score,
        overall_assessment=result.overall_assessment.value if result.overall_assessment else None,
        duration_ms=result.duration_ms,
    )


@app.post("/v2/plans/{execution_id}/rollback", response_model=RollbackResponse)
async def rollback_execution(execution_id: str, request: RollbackRequest):
    """
    Rollback a plan execution to the last checkpoint.
    """
    global orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    success = await orchestrator.rollback_execution(execution_id)

    if success:
        return RollbackResponse(
            success=True,
            execution_id=execution_id,
            message="Rollback successful",
        )
    else:
        return RollbackResponse(
            success=False,
            execution_id=execution_id,
            message="Rollback failed: no checkpoints found",
        )


@app.get("/v2/plans/{execution_id}/trace", response_model=TraceResponse)
async def get_execution_trace(execution_id: str):
    """
    Get distributed trace for an execution.

    Returns events and checkpoints for debugging.
    """
    global orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    result = await orchestrator.get_execution_status(execution_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    # Get events from L11 bridge
    events = orchestrator.l11_bridge.get_events(correlation_id=execution_id)

    # Get checkpoints
    checkpoints = []
    for ur in result.unit_results:
        if ur.checkpoint_hash:
            checkpoints.append({
                "unit_id": ur.unit_id,
                "checkpoint_hash": ur.checkpoint_hash,
                "status": ur.status.value,
            })

    return TraceResponse(
        execution_id=execution_id,
        plan_id=result.plan_id,
        events=[
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp.isoformat(),
                "payload": e.payload,
            }
            for e in events
        ],
        checkpoints=checkpoints,
    )


@app.get("/v2/stats")
async def get_statistics():
    """
    Get service statistics.
    """
    global orchestrator

    if not orchestrator:
        return {"error": "Orchestrator not initialized"}

    return orchestrator.get_statistics()


# ==================== Lifecycle Events ====================

@app.on_event("startup")
async def startup():
    """Initialize orchestrator on startup."""
    global orchestrator
    logger.info("L05 Planning Service starting...")

    orchestrator = PipelineOrchestrator(
        working_dir=Path.cwd(),
    )
    await orchestrator.initialize()

    logger.info("L05 Planning Service started (V2)")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global orchestrator
    logger.info("L05 Planning Service shutting down...")

    if orchestrator:
        await orchestrator.close()
        orchestrator = None

    logger.info("L05 Planning Service shutdown complete")
