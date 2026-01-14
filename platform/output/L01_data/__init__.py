"""
L01_data - Data Layer Integration Module

This module provides enhanced data services that integrate Phase 15 (document-consolidator)
and Phase 16 (context-orchestrator) capabilities with the core Data Layer v4.0.

Components:
- enhanced_context_service: Context persistence and retrieval with document integration
- enhanced_document_service: Document ingestion, storage, and semantic search
"""

from .enhanced_context_service import ContextService
from .enhanced_document_service import DocumentService

__all__ = [
    'ContextService',
    'DocumentService',
]
