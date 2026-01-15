"""Document store service."""

import asyncpg
from typing import List, Optional
from uuid import UUID

from ..models import Document, DocumentCreate, DocumentUpdate


class DocumentStore:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def create_document(self, doc_data: DocumentCreate) -> Document:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO documents (title, content, content_type, metadata, tags) VALUES ($1, $2, $3, $4, $5) RETURNING id, title, content, content_type, metadata, tags, version, created_at, updated_at",
                doc_data.title, doc_data.content, doc_data.content_type, doc_data.metadata, doc_data.tags,
            )
        return Document(**dict(row))

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, title, content, content_type, metadata, tags, version, created_at, updated_at FROM documents WHERE id = $1",
                document_id,
            )
        return Document(**dict(row)) if row else None

    async def update_document(self, document_id: UUID, doc_data: DocumentUpdate) -> Optional[Document]:
        update_fields = []
        params = []
        param_count = 1
        for field, value in doc_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1
        if not update_fields:
            return await self.get_document(document_id)
        update_fields.append("version = version + 1")
        update_fields.append("updated_at = NOW()")
        query = f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ${param_count} RETURNING id, title, content, content_type, metadata, tags, version, created_at, updated_at"
        params.append(document_id)
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        return Document(**dict(row)) if row else None

    async def list_documents(self, limit: int = 100) -> List[Document]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, title, content, content_type, metadata, tags, version, created_at, updated_at FROM documents ORDER BY updated_at DESC LIMIT $1",
                limit,
            )
        return [Document(**dict(row)) for row in rows]

    async def delete_document(self, document_id: UUID) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("DELETE FROM documents WHERE id = $1", document_id)
        return result.split()[-1] == "1"
