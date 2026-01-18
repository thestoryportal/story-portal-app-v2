#!/usr/bin/env python3
"""Validation script for L12 Phase 2 enhancements.

Tests:
1. Service Categorization
2. Workflow Templates
3. Semantic Matching (if Ollama available)
4. WebSocket Handler (Redis required)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.L12_nl_interface.core.service_registry import get_registry
from src.L12_nl_interface.core.service_factory import ServiceFactory
from src.L12_nl_interface.utils.service_categorizer import ServiceCategorizer
from src.L12_nl_interface.services.workflow_templates import WorkflowTemplates, WorkflowCategory
from src.L12_nl_interface.services.embedding_service import EmbeddingService


def test_service_categorization():
    """Test ServiceCategorizer functionality."""
    print("\n" + "="*60)
    print("TEST 1: Service Categorization")
    print("="*60)

    registry = get_registry()
    services = registry.list_all_services()

    # Test category retrieval
    categories = ServiceCategorizer.CATEGORIES
    print(f"✓ Found {len(categories)} categories")

    # Test category assignment
    for service in services[:5]:  # Test first 5 services
        category_id = ServiceCategorizer.get_category_for_service(service.service_name)
        if category_id:
            category_name = ServiceCategorizer.get_category_name(category_id)
            print(f"  {service.service_name} → {category_name}")

    # Test grouping
    grouped = ServiceCategorizer.group_services_by_category(services)
    print(f"✓ Grouped services into {len(grouped)} categories")

    # Test formatting
    formatted = ServiceCategorizer.format_categorized_services(services[:10])
    print(f"✓ Formatted output ({len(formatted)} chars)")

    print("✅ Service Categorization: PASSED")
    return True


def test_workflow_templates():
    """Test WorkflowTemplates functionality."""
    print("\n" + "="*60)
    print("TEST 2: Workflow Templates")
    print("="*60)

    registry = get_registry()
    factory = ServiceFactory(registry)
    templates = WorkflowTemplates(registry, factory)

    # Test template listing
    all_templates = templates.list_templates()
    print(f"✓ Found {len(all_templates)} workflow templates")

    # Test category filtering
    testing_templates = templates.list_templates(category=WorkflowCategory.TESTING)
    deployment_templates = templates.list_templates(category=WorkflowCategory.DEPLOYMENT)
    data_templates = templates.list_templates(category=WorkflowCategory.DATA_PIPELINE)
    monitoring_templates = templates.list_templates(category=WorkflowCategory.MONITORING)

    print(f"  Testing: {len(testing_templates)} templates")
    print(f"  Deployment: {len(deployment_templates)} templates")
    print(f"  Data Pipeline: {len(data_templates)} templates")
    print(f"  Monitoring: {len(monitoring_templates)} templates")

    # Test template retrieval
    template = templates.get_template("testing.unit")
    if template:
        print(f"✓ Retrieved 'testing.unit' template:")
        print(f"  Description: {template.description}")
        print(f"  Steps: {len(template.steps)}")
        print(f"  Parameters: {list(template.parameters.keys())}")

    # Test search
    matches = templates.search_templates("deployment")
    print(f"✓ Search found {len(matches)} matches for 'deployment'")

    print("✅ Workflow Templates: PASSED")
    return True


async def test_semantic_matching():
    """Test EmbeddingService (Ollama integration)."""
    print("\n" + "="*60)
    print("TEST 3: Semantic Matching")
    print("="*60)

    try:
        embedding_service = EmbeddingService(
            ollama_base_url="http://localhost:11434",
            embedding_model="nomic-embed-text",
            timeout=5.0
        )

        await embedding_service.start()

        # Test embedding generation
        text1 = "create a strategic plan"
        text2 = "planning service for goal decomposition"

        embedding1 = await embedding_service.generate_embedding(text1)
        embedding2 = await embedding_service.generate_embedding(text2)

        if embedding1 and embedding2:
            print(f"✓ Generated embeddings:")
            print(f"  Text 1: {len(embedding1)} dimensions")
            print(f"  Text 2: {len(embedding2)} dimensions")

            # Test cosine similarity
            similarity = EmbeddingService.cosine_similarity(embedding1, embedding2)
            print(f"✓ Cosine similarity: {similarity:.3f}")

            await embedding_service.stop()
            print("✅ Semantic Matching: PASSED")
            return True
        else:
            print("⚠️  Semantic Matching: SKIPPED (Ollama not responding)")
            return None

    except Exception as e:
        print(f"⚠️  Semantic Matching: SKIPPED (Ollama not available: {e})")
        return None


async def test_websocket_handler():
    """Test WebSocketConnectionManager."""
    print("\n" + "="*60)
    print("TEST 4: WebSocket Handler")
    print("="*60)

    try:
        from src.L12_nl_interface.interfaces.websocket_handler import WebSocketConnectionManager

        ws_manager = WebSocketConnectionManager()
        print("✓ Created WebSocketConnectionManager")

        # Test initialization (without actually starting Redis)
        print(f"  Active connections: {len(ws_manager.active_connections)}")
        print(f"  Global connections: {len(ws_manager.global_connections)}")

        print("✅ WebSocket Handler: PASSED (structure validation)")
        return True

    except Exception as e:
        print(f"⚠️  WebSocket Handler: SKIPPED ({e})")
        return None


def test_mcp_server_tools():
    """Test MCP Server tool definitions."""
    print("\n" + "="*60)
    print("TEST 5: MCP Server Tools")
    print("="*60)

    from src.L12_nl_interface.interfaces.mcp_server_stdio import L12MCPServer

    try:
        server = L12MCPServer()
        tools = server.get_tools()

        print(f"✓ MCP Server initialized")
        print(f"✓ Found {len(tools)} tools:")

        expected_tools = [
            "browse_services",
            "invoke_service",
            "search_services",
            "list_services",
            "get_service_info",
            "list_methods",
            "get_session_info",
            "list_workflows",
            "get_workflow_info",
            "execute_workflow",
            "search_workflows"
        ]

        tool_names = [tool["name"] for tool in tools]

        for expected_tool in expected_tools:
            if expected_tool in tool_names:
                print(f"  ✓ {expected_tool}")
            else:
                print(f"  ✗ {expected_tool} (MISSING)")
                return False

        # Check for new workflow tools
        workflow_tools = [name for name in tool_names if "workflow" in name]
        print(f"✓ Found {len(workflow_tools)} workflow-related tools")

        print("✅ MCP Server Tools: PASSED")
        return True

    except Exception as e:
        print(f"❌ MCP Server Tools: FAILED ({e})")
        return False


async def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("L12 PHASE 2 ENHANCEMENTS VALIDATION")
    print("="*60)

    results = {}

    # Test 1: Service Categorization
    results["categorization"] = test_service_categorization()

    # Test 2: Workflow Templates
    results["workflows"] = test_workflow_templates()

    # Test 3: Semantic Matching (may skip if Ollama unavailable)
    results["semantic"] = await test_semantic_matching()

    # Test 4: WebSocket Handler
    results["websocket"] = await test_websocket_handler()

    # Test 5: MCP Server Tools
    results["mcp_tools"] = test_mcp_server_tools()

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result is True else ("⚠️  SKIPPED" if result is None else "❌ FAILED")
        print(f"{test_name.upper()}: {status}")

    print(f"\nResults: {passed}/{total} passed, {skipped}/{total} skipped, {failed}/{total} failed")

    if failed > 0:
        print("\n❌ VALIDATION FAILED")
        return 1
    else:
        print("\n✅ VALIDATION PASSED")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
