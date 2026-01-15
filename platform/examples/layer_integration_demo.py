"""
Platform Layer Integration Demo

Demonstrates integration between:
- L02 Agent Runtime Layer
- L03 Tool Execution Layer
- L04 Model Gateway Layer

This example shows the complete flow of an agent requesting inference
and using tools that can also request inference.
"""

import asyncio
import sys
from pathlib import Path

# Add platform to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def demo_l04_standalone():
    """Demo: L04 Model Gateway standalone usage"""
    print("\n" + "="*80)
    print("DEMO 1: L04 Model Gateway - Standalone Usage")
    print("="*80 + "\n")

    from src.L04_model_gateway.services import ModelGateway
    from src.L04_model_gateway.models import Message, MessageRole

    # Initialize gateway
    gateway = ModelGateway()
    print("✅ Model Gateway initialized")

    # Check health
    health = await gateway.health_check()
    print(f"✅ Health check complete:")
    print(f"   - Registry: {health['registry']['total_models']} models")
    print(f"   - Providers: {list(health['providers'].keys())}")

    # List available models
    models = gateway.registry.get_available_models()
    print(f"\n📋 Available models:")
    for model in models:
        print(f"   - {model.model_id} ({model.provider})")
        print(f"     Context: {model.context_window}, Capabilities: {model.capabilities.capabilities_list}")

    # Create inference request
    from src.L04_model_gateway.models import InferenceRequest
    messages = [Message(role=MessageRole.USER, content="Hello! What is 2+2?")]
    request = InferenceRequest.create(
        agent_did="did:key:demo-agent",
        messages=messages,
        system_prompt="You are a helpful AI assistant.",
        temperature=0.7,
        capabilities=["text"]
    )

    print(f"\n🚀 Executing inference request...")
    print(f"   Request ID: {request.request_id}")
    print(f"   Agent DID: {request.agent_did}")

    # Execute (using mock adapter since we're in demo)
    try:
        response = await gateway.execute(request)
        print(f"\n✅ Inference complete!")
        print(f"   Model: {response.model_id} ({response.provider})")
        print(f"   Tokens: {response.token_usage.total_tokens}")
        print(f"   Latency: {response.latency_ms}ms")
        print(f"   Cached: {response.cached}")
        print(f"\n💬 Response: {response.content}")
    except Exception as e:
        print(f"⚠️  Inference failed (expected in demo without Ollama): {e}")

    await gateway.close()
    print("\n✅ Demo 1 complete\n")


async def demo_l02_with_l04():
    """Demo: L02 Agent Runtime using L04 Model Gateway"""
    print("\n" + "="*80)
    print("DEMO 2: L02 Agent Runtime + L04 Model Gateway Integration")
    print("="*80 + "\n")

    from src.L02_runtime.services import ModelGatewayBridge

    # Initialize bridge
    bridge = ModelGatewayBridge()
    print("✅ Model Gateway Bridge initialized")

    # Check gateway health through bridge
    health = await bridge.check_gateway_health()
    print(f"✅ Gateway health: {health.get('gateway', 'unknown')}")

    # Get available models
    models = await bridge.get_available_models()
    print(f"\n📋 Available models through bridge: {len(models)}")
    for model in models[:3]:  # Show first 3
        print(f"   - {model['model_id']} ({model['provider']})")

    # Request inference for an agent
    try:
        print(f"\n🚀 Agent requesting inference through bridge...")
        result = await bridge.request_inference(
            agent_did="did:key:runtime-agent-123",
            messages=[
                {"role": "user", "content": "Explain quantum computing in one sentence."}
            ],
            system_prompt="You are a concise AI assistant.",
            temperature=0.5,
            max_tokens=100,
            capabilities=["text"]
        )

        if result.get("streaming"):
            print("   Streaming response (not shown in demo)")
        else:
            print(f"\n✅ Agent inference complete!")
            print(f"   Model: {result['model_id']}")
            print(f"   Tokens: {result['token_usage']['total_tokens']}")
            print(f"   Response: {result['content']}")

    except Exception as e:
        print(f"⚠️  Inference failed (expected without Ollama): {e}")

    await bridge.close()
    print("\n✅ Demo 2 complete\n")


async def demo_l03_with_l04():
    """Demo: L03 Tool Execution using L04 Model Gateway"""
    print("\n" + "="*80)
    print("DEMO 3: L03 Tool Execution + L04 Model Gateway Integration")
    print("="*80 + "\n")

    from src.L03_tool_execution.services import ToolModelBridge

    # Initialize bridge
    bridge = ToolModelBridge()
    print("✅ Tool Model Bridge initialized")

    try:
        # Simulate a tool requesting inference
        print(f"\n🔧 Tool requesting inference during execution...")
        result = await bridge.tool_request_inference(
            tool_id="summarizer_tool",
            agent_did="did:key:tool-agent-456",
            prompt="Summarize: The quick brown fox jumps over the lazy dog.",
            system_prompt="You are a text summarization tool.",
            temperature=0.3,
            max_tokens=50,
            capabilities=["text"]
        )

        print(f"✅ Tool inference complete!")
        print(f"   Tool: summarizer_tool")
        print(f"   Result: {result}")

    except Exception as e:
        print(f"⚠️  Tool inference failed (expected without Ollama): {e}")

    try:
        # Simulate tool analyzing results with LLM
        print(f"\n🔍 Tool analyzing execution results with LLM...")
        analysis = await bridge.tool_analyze_result(
            tool_id="analyzer_tool",
            agent_did="did:key:tool-agent-456",
            tool_output="File processed: 1234 lines, 56 functions, 789 tests",
            analysis_prompt="What does this code analysis tell us about code quality?"
        )

        print(f"✅ Analysis complete!")
        print(f"   Analysis: {analysis['analysis']}")

    except Exception as e:
        print(f"⚠️  Analysis failed (expected without Ollama): {e}")

    await bridge.close()
    print("\n✅ Demo 3 complete\n")


async def demo_full_integration():
    """Demo: Complete integration of L02 + L03 + L04"""
    print("\n" + "="*80)
    print("DEMO 4: Full Platform Integration (L02 + L03 + L04)")
    print("="*80 + "\n")

    print("🏗️  Platform Architecture:")
    print("   L02 Agent Runtime → L04 Model Gateway → LLM Providers")
    print("   L03 Tool Execution → L04 Model Gateway → LLM Providers")
    print("                     ↓")
    print("   Unified inference with caching, routing, rate limiting\n")

    # Simulate agent workflow
    print("📋 Agent Workflow Simulation:")
    print("   1. Agent spawns via L02")
    print("   2. Agent requests inference via L04")
    print("   3. Gateway routes to optimal model")
    print("   4. Gateway checks cache")
    print("   5. Gateway checks rate limits")
    print("   6. Provider executes inference")
    print("   7. Response cached and returned")
    print("   8. Agent may invoke tools via L03")
    print("   9. Tools can request inference via L04")
    print("   10. Complete agent task with full platform support")

    print("\n✨ Key Integration Benefits:")
    print("   ✅ Unified model access across all layers")
    print("   ✅ Automatic caching reduces costs")
    print("   ✅ Rate limiting prevents overuse")
    print("   ✅ Circuit breakers handle provider failures")
    print("   ✅ Intelligent routing optimizes performance")
    print("   ✅ Tools can leverage LLMs during execution")

    print("\n✅ Demo 4 complete\n")


async def demo_integration_patterns():
    """Demo: Common integration patterns"""
    print("\n" + "="*80)
    print("DEMO 5: Integration Patterns and Best Practices")
    print("="*80 + "\n")

    print("🎯 Pattern 1: Agent with Model Gateway")
    print("   Use Case: Agent needs to generate code, analyze data, or respond")
    print("   Code: L02 AgentRuntime → ModelGatewayBridge → L04 Gateway")
    print("   Benefits: Automatic caching, rate limiting, fallback\n")

    print("🎯 Pattern 2: Tool with Model Gateway")
    print("   Use Case: Tool needs LLM for analysis, composition, or transformation")
    print("   Code: L03 ToolExecutor → ToolModelBridge → L04 Gateway")
    print("   Benefits: Tools become AI-powered, can compose complex results\n")

    print("🎯 Pattern 3: Agent + Tools + Models")
    print("   Use Case: Complete agentic workflow")
    print("   Flow:")
    print("      1. Agent (L02) requests inference (L04)")
    print("      2. Model suggests tool use")
    print("      3. Agent invokes tool (L03)")
    print("      4. Tool uses LLM for processing (L04)")
    print("      5. Tool returns result to agent")
    print("      6. Agent uses result in next inference (L04)")
    print("   Benefits: Full agentic capabilities with intelligent routing\n")

    print("🎯 Pattern 4: Multi-Model Workflow")
    print("   Use Case: Different models for different tasks")
    print("   Example:")
    print("      - Vision model for image analysis")
    print("      - Fast model for classification")
    print("      - Powerful model for reasoning")
    print("   Gateway automatically routes based on requirements\n")

    print("✅ Demo 5 complete\n")


async def main():
    """Run all integration demos"""
    print("\n" + "="*80)
    print("🚀 PLATFORM LAYER INTEGRATION DEMO")
    print("="*80)
    print("\nDemonstrating integration between:")
    print("  • L02 Agent Runtime Layer")
    print("  • L03 Tool Execution Layer")
    print("  • L04 Model Gateway Layer")
    print("\n" + "="*80)

    try:
        # Run demos
        await demo_l04_standalone()
        await demo_l02_with_l04()
        await demo_l03_with_l04()
        await demo_full_integration()
        await demo_integration_patterns()

        print("\n" + "="*80)
        print("✅ ALL INTEGRATION DEMOS COMPLETE")
        print("="*80 + "\n")

        print("📚 Next Steps:")
        print("   1. Install dependencies: pip install httpx redis --break-system-packages")
        print("   2. Ensure Ollama running: curl localhost:11434/api/tags")
        print("   3. Run tests: pytest src/L04_model_gateway/tests/")
        print("   4. Try live inference with Ollama models")
        print("   5. Add Anthropic/OpenAI API keys for production\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
