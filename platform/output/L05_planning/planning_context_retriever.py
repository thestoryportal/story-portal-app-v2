"""
Planning Context Retriever - Phase 15 + Phase 16 Integration

Combines task context with document search to provide comprehensive
context for planning phase operations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class PlanningContextRetriever:
    """
    Retrieves and combines context for planning phase.

    Integrates:
    - Task-specific context from context-orchestrator
    - Relevant documents from document-consolidator
    - Historical planning data
    - Architectural constraints and patterns

    Used by planning agents to gather comprehensive context before
    generating implementation plans.
    """

    def __init__(self, context_service, document_service):
        """
        Initialize planning context retriever.

        Args:
            context_service: ContextService instance from L01_data
            document_service: DocumentService instance from L01_data
        """
        self.context_service = context_service
        self.document_service = document_service

    async def get_planning_context(
        self,
        task_id: str,
        include_history: bool = True,
        document_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive planning context for a task.

        Args:
            task_id: Unique task identifier
            include_history: Include historical planning data
            document_limit: Maximum relevant documents to retrieve

        Returns:
            Dictionary containing all planning context
        """
        context_id = f"task:{task_id}:planning"

        # Get task context
        task_context = await self.context_service.get_context(context_id)

        if not task_context:
            # Initialize new planning context
            task_context = {
                'context_id': context_id,
                'data': {
                    'task_id': task_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'new'
                },
                'metadata': {},
                'version': 0
            }

        # Extract task description for document search
        task_description = task_context['data'].get('description', '')
        task_requirements = task_context['data'].get('requirements', [])

        # Build search query from task info
        search_query = self._build_search_query(task_description, task_requirements)

        # Get relevant documents
        relevant_docs = await self.get_relevant_documents(
            query=search_query,
            limit=document_limit
        )

        # Get historical planning data if requested
        history = []
        if include_history:
            history = await self._get_planning_history(task_id)

        return {
            'task_id': task_id,
            'task_context': task_context['data'],
            'relevant_documents': relevant_docs,
            'planning_history': history,
            'retrieved_at': datetime.utcnow().isoformat(),
            'document_count': len(relevant_docs),
            'history_count': len(history)
        }

    async def get_relevant_documents(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get documents relevant to planning task.

        Performs semantic search over document corpus to find
        relevant specifications, patterns, and examples.

        Args:
            query: Search query describing task needs
            limit: Maximum documents to return
            filters: Optional metadata filters (document type, source, etc.)

        Returns:
            List of relevant documents with similarity scores
        """
        # Perform semantic search
        search_results = await self.document_service.query(
            query=query,
            limit=limit * 2  # Get extra for filtering
        )

        documents = search_results.get('documents', [])

        # Apply filters if provided
        if filters:
            documents = self._apply_filters(documents, filters)

        # Limit to requested number
        documents = documents[:limit]

        # Enrich with planning-specific metadata
        enriched = []
        for doc in documents:
            enriched_doc = {
                **doc,
                'relevance_score': doc['similarity'],
                'planning_hints': self._extract_planning_hints(doc)
            }
            enriched.append(enriched_doc)

        return enriched

    def _build_search_query(
        self,
        description: str,
        requirements: List[str]
    ) -> str:
        """
        Build effective search query from task info.

        Args:
            description: Task description
            requirements: List of task requirements

        Returns:
            Optimized search query string
        """
        query_parts = []

        if description:
            query_parts.append(description)

        if requirements:
            # Add top requirements (limit to avoid query bloat)
            query_parts.extend(requirements[:3])

        return ' '.join(query_parts)

    def _apply_filters(
        self,
        documents: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply metadata filters to document list.

        Args:
            documents: List of documents to filter
            filters: Filter criteria

        Returns:
            Filtered document list
        """
        filtered = []

        for doc in documents:
            metadata = doc.get('metadata', {})
            matches = True

            for key, value in filters.items():
                if isinstance(value, list):
                    # Match if metadata value in list
                    if metadata.get(key) not in value:
                        matches = False
                        break
                else:
                    # Exact match
                    if metadata.get(key) != value:
                        matches = False
                        break

            if matches:
                filtered.append(doc)

        return filtered

    def _extract_planning_hints(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract planning-specific hints from document.

        Analyzes document content and metadata to provide
        actionable hints for planning phase.

        Args:
            document: Document dictionary

        Returns:
            Planning hints dictionary
        """
        hints = {
            'has_examples': False,
            'has_patterns': False,
            'has_constraints': False,
            'document_type': 'unknown'
        }

        content = document.get('content', '').lower()
        metadata = document.get('metadata', {})

        # Detect document types
        if 'spec' in metadata.get('type', '').lower() or 'specification' in content:
            hints['document_type'] = 'specification'
            hints['has_constraints'] = True

        if 'example' in content or 'sample' in content:
            hints['has_examples'] = True

        if 'pattern' in content or 'best practice' in content:
            hints['has_patterns'] = True

        if 'must' in content or 'required' in content or 'constraint' in content:
            hints['has_constraints'] = True

        return hints

    async def _get_planning_history(
        self,
        task_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get historical planning data for task.

        Args:
            task_id: Task identifier
            limit: Maximum history entries to return

        Returns:
            List of historical planning records
        """
        context_id = f"task:{task_id}:planning"

        # Query for previous versions of planning context
        query = """
            SELECT version, data, metadata, created_at
            FROM contexts
            WHERE context_id = $1
            ORDER BY version DESC
            LIMIT $2
        """

        results = await self.context_service.db.fetch(query, context_id, limit)

        history = []
        for row in results:
            import json
            data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
            metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']

            history.append({
                'version': row['version'],
                'status': data.get('status'),
                'plan_summary': data.get('plan_summary'),
                'created_at': row['created_at'].isoformat(),
                'metadata': metadata
            })

        return history

    async def save_planning_context(
        self,
        task_id: str,
        plan_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save planning context for future reference.

        Args:
            task_id: Task identifier
            plan_data: Planning data to save
            metadata: Optional metadata

        Returns:
            Saved context information
        """
        context_id = f"task:{task_id}:planning"

        saved = await self.context_service.save_context(
            context_id=context_id,
            data=plan_data,
            metadata=metadata or {}
        )

        return {
            'task_id': task_id,
            'context_id': context_id,
            'version': saved['version'],
            'saved_at': saved['updated_at']
        }
