export class ConsolidatorError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ConsolidatorError';
  }
}

export class DocumentNotFoundError extends ConsolidatorError {
  constructor(documentId: string) {
    super(
      `Document not found: ${documentId}`,
      'DOCUMENT_NOT_FOUND',
      { documentId }
    );
  }
}

export class ConflictResolutionError extends ConsolidatorError {
  constructor(conflictId: string, reason: string) {
    super(
      `Failed to resolve conflict: ${reason}`,
      'CONFLICT_RESOLUTION_FAILED',
      { conflictId, reason }
    );
  }
}

export class EmbeddingError extends ConsolidatorError {
  constructor(reason: string) {
    super(
      `Embedding generation failed: ${reason}`,
      'EMBEDDING_FAILED',
      { reason }
    );
  }
}

export class LLMError extends ConsolidatorError {
  constructor(model: string, reason: string) {
    super(
      `LLM inference failed: ${reason}`,
      'LLM_FAILED',
      { model, reason }
    );
  }
}

export class ValidationError extends ConsolidatorError {
  constructor(field: string, reason: string) {
    super(
      `Validation failed for ${field}: ${reason}`,
      'VALIDATION_FAILED',
      { field, reason }
    );
  }
}

export class DatabaseError extends ConsolidatorError {
  constructor(operation: string, reason: string) {
    super(
      `Database operation failed: ${reason}`,
      'DATABASE_FAILED',
      { operation, reason }
    );
  }
}

export class ServiceUnavailableError extends ConsolidatorError {
  constructor(service: string, reason: string) {
    super(
      `Service unavailable: ${service} - ${reason}`,
      'SERVICE_UNAVAILABLE',
      { service, reason }
    );
  }
}
