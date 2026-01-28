"""
Tool Registry Routes

Endpoints for tool listing, retrieval, registration, search, and deprecation.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import List, Optional
import logging

from ..dto import (
    ToolDTO,
    ToolListResponseDTO,
    ToolSearchRequestDTO,
    ToolSearchResultDTO,
    ToolRegisterRequestDTO,
    ToolDeprecateRequestDTO,
)
from ..models import ToolCategory, SourceType, DeprecationState, ToolDefinition, ToolManifest
from ..models.error_codes import ErrorCode, ToolExecutionError

logger = logging.getLogger(__name__)

router = APIRouter()


def get_registry(request: Request):
    """Get tool registry from app state."""
    registry = getattr(request.app.state, "tool_registry", None)
    if not registry:
        raise HTTPException(
            status_code=503,
            detail={"code": "E3707", "message": "Tool registry not available"}
        )
    return registry


def tool_definition_to_dto(tool_def: ToolDefinition) -> ToolDTO:
    """Convert ToolDefinition dataclass to ToolDTO."""
    return ToolDTO(
        tool_id=tool_def.tool_id,
        tool_name=tool_def.tool_name,
        description=tool_def.description,
        category=tool_def.category.value if isinstance(tool_def.category, ToolCategory) else tool_def.category,
        tags=tool_def.tags or [],
        latest_version=tool_def.latest_version,
        source_type=tool_def.source_type.value if isinstance(tool_def.source_type, SourceType) else tool_def.source_type,
        source_metadata=tool_def.source_metadata or {},
        deprecation_state=tool_def.deprecation_state.value if isinstance(tool_def.deprecation_state, DeprecationState) else tool_def.deprecation_state,
        deprecation_date=tool_def.deprecation_date,
        created_at=tool_def.created_at,
        updated_at=tool_def.updated_at,
        requires_approval=tool_def.requires_approval,
        default_timeout_seconds=tool_def.default_timeout_seconds,
        default_cpu_millicore_limit=tool_def.default_cpu_millicore_limit,
        default_memory_mb_limit=tool_def.default_memory_mb_limit,
    )


@router.get("", response_model=ToolListResponseDTO)
async def list_tools(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    include_deprecated: bool = Query(False, description="Include deprecated tools"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ToolListResponseDTO:
    """
    List all available tools.

    Supports filtering by category and deprecation state.
    """
    registry = get_registry(request)

    try:
        # Convert category string to enum if provided
        category_enum = None
        if category:
            try:
                category_enum = ToolCategory(category)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "E3701",
                        "message": f"Invalid category: {category}",
                        "valid_categories": [c.value for c in ToolCategory],
                    }
                )

        tools = await registry.list_tools(
            category=category_enum,
            include_deprecated=include_deprecated
        )

        # Convert to DTOs
        tool_dtos = [tool_definition_to_dto(t) for t in tools]

        # Simple pagination
        total = len(tool_dtos)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = tool_dtos[start:end]

        return ToolListResponseDTO(
            tools=paginated,
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except ToolExecutionError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Failed to list tools: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": "Failed to list tools"}
        )


@router.get("/{tool_id}", response_model=ToolDTO)
async def get_tool(request: Request, tool_id: str) -> ToolDTO:
    """
    Get tool definition by ID.

    Returns full tool metadata including version and configuration.
    """
    registry = get_registry(request)

    try:
        tool_def = await registry.get_tool(tool_id)
        return tool_definition_to_dto(tool_def)

    except ToolExecutionError as e:
        if e.code == ErrorCode.E3001:
            raise HTTPException(status_code=404, detail=e.to_dict())
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Failed to get tool {tool_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": f"Failed to get tool: {tool_id}"}
        )


@router.post("/search", response_model=List[ToolSearchResultDTO])
async def search_tools(
    request: Request,
    search_request: ToolSearchRequestDTO,
) -> List[ToolSearchResultDTO]:
    """
    Semantic search for tools.

    Uses pgvector embeddings for natural language tool discovery.
    """
    registry = get_registry(request)

    try:
        # Convert category string to enum if provided
        category_enum = None
        if search_request.category:
            try:
                category_enum = ToolCategory(search_request.category)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "E3701",
                        "message": f"Invalid category: {search_request.category}",
                    }
                )

        results = await registry.semantic_search(
            query=search_request.query,
            limit=search_request.limit,
            category=category_enum,
        )

        # Convert to DTOs
        return [
            ToolSearchResultDTO(
                tool=tool_definition_to_dto(tool_def),
                similarity_score=score,
            )
            for tool_def, score in results
        ]

    except HTTPException:
        raise
    except ToolExecutionError as e:
        if e.code == ErrorCode.E3005:
            # Embedding generation failed - likely Ollama unavailable
            raise HTTPException(
                status_code=503,
                detail={
                    "code": e.code.value,
                    "message": "Semantic search unavailable - embedding service down",
                }
            )
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Semantic search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3005", "message": "Semantic search failed"}
        )


@router.post("", response_model=ToolDTO, status_code=201)
async def register_tool(
    request: Request,
    tool_request: ToolRegisterRequestDTO,
) -> ToolDTO:
    """
    Register a new tool in the registry.

    Creates tool definition and initial version.
    """
    registry = get_registry(request)

    try:
        # Create ToolDefinition from request
        tool_def = ToolDefinition(
            tool_id=tool_request.tool_id,
            tool_name=tool_request.tool_name,
            description=tool_request.description,
            category=ToolCategory(tool_request.category),
            tags=tool_request.tags,
            latest_version=tool_request.version,
            source_type=SourceType(tool_request.source_type),
            source_metadata=tool_request.source_metadata,
            requires_approval=tool_request.requires_approval,
            default_timeout_seconds=tool_request.default_timeout_seconds,
            default_cpu_millicore_limit=tool_request.default_cpu_millicore_limit,
            default_memory_mb_limit=tool_request.default_memory_mb_limit,
            required_permissions=tool_request.required_permissions,
            result_schema=tool_request.result_schema,
        )

        # Create ToolManifest
        tool_manifest = ToolManifest(
            tool_id=tool_request.tool_id,
            tool_name=tool_request.tool_name,
            version=tool_request.version,
            description=tool_request.description,
            category=ToolCategory(tool_request.category),
            parameters_schema=tool_request.input_schema or {},
        )

        # Register in database
        await registry.register_tool(tool_def, tool_manifest)

        logger.info(f"Registered tool: {tool_request.tool_id} v{tool_request.version}")

        # Fetch and return the created tool
        created_tool = await registry.get_tool(tool_request.tool_id)
        return tool_definition_to_dto(created_tool)

    except ToolExecutionError as e:
        if e.code == ErrorCode.E3007:
            raise HTTPException(status_code=409, detail=e.to_dict())  # Conflict - already exists
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Failed to register tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": "Tool registration failed"}
        )


@router.put("/{tool_id}/deprecate", response_model=ToolDTO)
async def deprecate_tool(
    request: Request,
    tool_id: str,
    deprecate_request: ToolDeprecateRequestDTO,
) -> ToolDTO:
    """
    Deprecate a tool.

    Marks the tool as deprecated with optional replacement recommendation.
    """
    registry = get_registry(request)

    try:
        # Verify tool exists
        tool_def = await registry.get_tool(tool_id)

        # TODO: Implement deprecation in registry
        # For now, return the tool as-is with a warning
        logger.warning(f"Tool deprecation not fully implemented for {tool_id}")

        return tool_definition_to_dto(tool_def)

    except ToolExecutionError as e:
        if e.code == ErrorCode.E3001:
            raise HTTPException(status_code=404, detail=e.to_dict())
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Failed to deprecate tool {tool_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "E3008", "message": "Tool deprecation failed"}
        )
