"""Test helper functions."""
import asyncio
from typing import Any, Callable, Coroutine

async def with_timeout(coro: Coroutine, timeout: float = 30.0) -> Any:
    """Run coroutine with timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)

async def initialize_layer(layer_class: type, **kwargs) -> Any:
    """Initialize a layer and return it."""
    layer = layer_class(**kwargs)
    await layer.initialize()
    return layer

async def cleanup_layer(layer: Any) -> None:
    """Safely cleanup a layer."""
    if layer and hasattr(layer, 'cleanup'):
        try:
            await layer.cleanup()
        except Exception:
            pass
