"""
Qdrant Vector Store Integration

This module provides integration with Qdrant vector database for storing
and retrieving document embeddings. Qdrant is optimized for high-performance
vector similarity search required for RAG systems.
"""

from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from loguru import logger
import os
from typing import Optional


class FlexCubeVectorStore:
    """
    Qdrant vector store wrapper for FlexCube documents.
    
    Manages the connection to Qdrant and provides methods for creating
    and managing vector indices. Uses 1024-dimensional vectors from
    BGE-large embeddings.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "flexcube_docs",
        embedding_dimension: int = 1024
    ):
        """
        Initialize Qdrant vector store connection.
        
        Args:
            host: Qdrant server hostname
            port: Qdrant server port
            collection_name: Name of the Qdrant collection
            embedding_dimension: Dimension of embeddings (1024 for BGE-large)
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        
        logger.info(f"Connecting to Qdrant at {host}:{port}")
        
        # Create Qdrant client
        self.client = QdrantClient(host=host, port=port)
        
        # Create vector store
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name
        )
        
        logger.info(f"Qdrant vector store initialized: {collection_name}")
    
    def create_collection_if_not_exists(self):
        """
        Create Qdrant collection if it doesn't exist.
        
        This ensures the collection is ready with the correct vector size
        for BGE-large embeddings (1024 dimensions).
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
    
    def get_storage_context(self) -> StorageContext:
        """
        Get storage context for LlamaIndex.
        
        Returns:
            StorageContext: Configured storage context with Qdrant
        """
        return StorageContext.from_defaults(vector_store=self.vector_store)
    
    def get_vector_store(self) -> QdrantVectorStore:
        """
        Get the Qdrant vector store instance.
        
        Returns:
            QdrantVectorStore: The vector store instance
        """
        return self.vector_store


def create_vector_store(
    host: str = "localhost",
    port: int = 6333,
    collection_name: str = "flexcube_docs",
    embedding_dimension: int = 1024
) -> FlexCubeVectorStore:
    """
    Factory function to create a FlexCube vector store.
    
    Args:
        host: Qdrant server hostname
        port: Qdrant server port
        collection_name: Name of the Qdrant collection
        embedding_dimension: Dimension of embeddings
        
    Returns:
        FlexCubeVectorStore: Configured vector store instance
    """
    vector_store = FlexCubeVectorStore(
        host=host,
        port=port,
        collection_name=collection_name,
        embedding_dimension=embedding_dimension
    )
    vector_store.create_collection_if_not_exists()
    return vector_store

