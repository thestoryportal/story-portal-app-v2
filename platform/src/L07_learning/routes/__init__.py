"""
L07 Learning Layer - Routes

REST API route handlers for datasets, jobs, models, and examples.
"""

from .datasets import router as datasets_router
from .jobs import router as jobs_router
from .models import router as models_router
from .examples import router as examples_router

__all__ = [
    "datasets_router",
    "jobs_router",
    "models_router",
    "examples_router",
]
