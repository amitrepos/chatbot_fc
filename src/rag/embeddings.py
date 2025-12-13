"""
BGE-Large Embeddings Module

This module provides embedding generation using BGE-large-en-v1.5 model.
BGE (BAAI General Embedding) is optimized for retrieval tasks and provides
1024-dimensional embeddings suitable for FlexCube documentation.
"""

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from loguru import logger
import os


class BGEEmbeddings:
    """
    BGE-Large Embeddings wrapper for LlamaIndex.
    
    Uses BAAI/bge-large-en-v1.5 model which provides high-quality
    embeddings for retrieval tasks. The model generates 1024-dimensional
    vectors optimized for semantic search.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        """
        Initialize BGE embeddings model.
        
        Args:
            model_name: HuggingFace model identifier for BGE-large
        """
        self.model_name = model_name
        logger.info(f"Initializing BGE embeddings model: {model_name}")
        
        # Initialize HuggingFace embedding model
        # This will download the model on first use (~1.3GB)
        self.embed_model = HuggingFaceEmbedding(
            model_name=model_name,
            device="cpu",  # CPU-only since we have no GPU
            trust_remote_code=True
        )
        
        logger.info("BGE embeddings model initialized successfully")
    
    def get_embedding_model(self):
        """
        Get the embedding model instance for use with LlamaIndex.
        
        Returns:
            HuggingFaceEmbedding: The embedding model instance
        """
        return self.embed_model
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            int: Embedding dimension (1024 for BGE-large)
        """
        return 1024


def create_embedding_model(model_name: str = "BAAI/bge-large-en-v1.5") -> HuggingFaceEmbedding:
    """
    Factory function to create a BGE embedding model.
    
    Args:
        model_name: HuggingFace model identifier
        
    Returns:
        HuggingFaceEmbedding: Configured embedding model
    """
    embeddings = BGEEmbeddings(model_name)
    return embeddings.get_embedding_model()

