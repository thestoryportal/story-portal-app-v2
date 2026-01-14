#!/usr/bin/env python3
"""
Embedding Service for MCP Document Consolidator

This service provides sentence embeddings using sentence-transformers.
It runs as a subprocess that communicates via JSON-RPC over stdin/stdout.

Usage:
    python embedding_service.py [--model MODEL_NAME] [--device DEVICE]

Protocol:
    Input (JSON per line):
        {"id": "request-id", "method": "embed", "params": {"texts": ["text1", "text2"]}}
        {"id": "request-id", "method": "embed_batch", "params": {"texts": [...], "batch_size": 32}}
        {"id": "request-id", "method": "similarity", "params": {"text1": "...", "text2": "..."}}
        {"id": "request-id", "method": "shutdown"}

    Output (JSON per line):
        {"id": "request-id", "result": [[0.1, 0.2, ...], [0.3, 0.4, ...]]}
        {"id": "request-id", "error": {"code": -1, "message": "Error message"}}
"""

import sys
import json
import argparse
import logging
from typing import List, Optional, Dict, Any
import numpy as np

# Configure logging to stderr (stdout is for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Default model - small and fast
DEFAULT_MODEL = 'all-MiniLM-L6-v2'
EMBEDDING_DIM = 384


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""

    def __init__(self, model_name: str = DEFAULT_MODEL, device: Optional[str] = None):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model to use
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto-detect)
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading model: {self.model_name}")

            # Auto-detect device if not specified
            if self.device is None:
                import torch
                if torch.cuda.is_available():
                    self.device = 'cuda'
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.device = 'mps'
                else:
                    self.device = 'cpu'

            logger.info(f"Using device: {self.device}")

            self.model = SentenceTransformer(self.model_name, device=self.device)

            # Verify model loads correctly
            test_embedding = self.model.encode(['test'], convert_to_numpy=True)
            self.embedding_dim = test_embedding.shape[1]

            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")

        except ImportError as e:
            logger.error(f"Failed to import sentence-transformers: {e}")
            logger.error("Install with: pip install sentence-transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not texts:
            return []

        if self.model is None:
            raise RuntimeError("Model not initialized")

        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True  # L2 normalize for cosine similarity
            )

            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a large list of texts in batches.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.embed(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity score (0-1)
        """
        embeddings = self.embed([text1, text2])

        vec1 = np.array(embeddings[0])
        vec2 = np.array(embeddings[1])

        # Embeddings are already normalized, so dot product = cosine similarity
        similarity = float(np.dot(vec1, vec2))

        return similarity


class JSONRPCServer:
    """JSON-RPC server that communicates over stdin/stdout."""

    def __init__(self, service: EmbeddingService):
        """
        Initialize the JSON-RPC server.

        Args:
            service: The embedding service to use
        """
        self.service = service
        self.running = True

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a single JSON-RPC request.

        Args:
            request: The parsed JSON-RPC request

        Returns:
            The JSON-RPC response
        """
        request_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})

        try:
            if method == 'embed':
                texts = params.get('texts', [])
                result = self.service.embed(texts)
                return {'id': request_id, 'result': result}

            elif method == 'embed_batch':
                texts = params.get('texts', [])
                batch_size = params.get('batch_size', 32)
                result = self.service.embed_batch(texts, batch_size)
                return {'id': request_id, 'result': result}

            elif method == 'similarity':
                text1 = params.get('text1', '')
                text2 = params.get('text2', '')
                result = self.service.similarity(text1, text2)
                return {'id': request_id, 'result': result}

            elif method == 'info':
                result = {
                    'model': self.service.model_name,
                    'device': self.service.device,
                    'embedding_dim': self.service.embedding_dim
                }
                return {'id': request_id, 'result': result}

            elif method == 'shutdown':
                self.running = False
                return {'id': request_id, 'result': {'status': 'shutting_down'}}

            else:
                return {
                    'id': request_id,
                    'error': {'code': -32601, 'message': f'Unknown method: {method}'}
                }

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                'id': request_id,
                'error': {'code': -1, 'message': str(e)}
            }

    def run(self):
        """Run the JSON-RPC server, reading from stdin and writing to stdout."""
        logger.info("Starting JSON-RPC server")

        # Signal readiness
        ready_msg = json.dumps({'status': 'ready', 'model': self.service.model_name})
        print(ready_msg, flush=True)

        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF received, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    error_response = {
                        'id': None,
                        'error': {'code': -32700, 'message': f'Parse error: {e}'}
                    }
                    print(json.dumps(error_response), flush=True)
                    continue

                response = self.handle_request(request)
                print(json.dumps(response), flush=True)

            except Exception as e:
                logger.error(f"Server error: {e}")
                error_response = {
                    'id': None,
                    'error': {'code': -32603, 'message': f'Internal error: {e}'}
                }
                print(json.dumps(error_response), flush=True)

        logger.info("Server stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Embedding Service for MCP Document Consolidator')
    parser.add_argument(
        '--model',
        type=str,
        default=DEFAULT_MODEL,
        help=f'Sentence-transformers model name (default: {DEFAULT_MODEL})'
    )
    parser.add_argument(
        '--device',
        type=str,
        choices=['cpu', 'cuda', 'mps'],
        default=None,
        help='Device to run on (default: auto-detect)'
    )

    args = parser.parse_args()

    try:
        service = EmbeddingService(model_name=args.model, device=args.device)
        server = JSONRPCServer(service)
        server.run()
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        # Output error as JSON for the parent process
        error_msg = json.dumps({'status': 'error', 'message': str(e)})
        print(error_msg, flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
