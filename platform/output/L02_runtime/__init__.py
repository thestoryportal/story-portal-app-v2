"""
L02_runtime - Runtime Integration Module

This module provides runtime integration components that bridge the agent runtime
with Phase 16 context-orchestrator for state persistence and checkpoint management.

Components:
- runtime_context_bridge: Agent state persistence and recovery bridge
"""

from .runtime_context_bridge import RuntimeContextBridge

__all__ = [
    'RuntimeContextBridge',
]
