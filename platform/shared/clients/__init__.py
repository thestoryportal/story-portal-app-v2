"""
Shared HTTP clients for inter-layer communication.

This package provides HTTP-based clients for all platform layers to communicate
with each other without requiring direct Python package imports.
"""

from .l01_client import L01Client

__all__ = [
    "L01Client",
]
