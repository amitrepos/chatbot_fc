"""
RAG Pipeline Module for FlexCube AI Assistant

This module contains the core RAG (Retrieval-Augmented Generation) components:
- Document loaders and processors
- Embedding generation
- Vector store integration (Qdrant)
- Query engine with Mistral integration
- Query expansion for semantic search improvement

Query Expansion Feature:
    The QueryExpander class generates synonyms and alternative phrasings
    before vector search to improve retrieval of semantically similar content.
    Example: "logged in" → "signed in", "authenticated", "user sessions"
"""

from .query_expander import QueryExpander, MultiQueryRetriever
from .query_engine import FlexCubeQueryEngine
from .pipeline import FlexCubeRAGPipeline

__all__ = [
    'QueryExpander',
    'MultiQueryRetriever', 
    'FlexCubeQueryEngine',
    'FlexCubeRAGPipeline'
]

