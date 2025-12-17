"""
Text Chunking Strategy Module

This module implements text chunking strategies optimized for FlexCube documentation.
Chunking is critical for RAG performance - chunks should be large enough to contain
complete context but small enough for efficient retrieval.
"""

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document
from typing import List
from loguru import logger


class FlexCubeChunker:
    """
    Text chunker optimized for FlexCube documentation.
    
    Uses sentence-based chunking with overlap to ensure context preservation.
    Settings are tuned for technical banking documentation which often contains
    structured information that benefits from larger chunks with overlap.
    """
    
    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        separator: str = " "
    ):
        """
        Initialize chunker with optimized settings for FlexCube docs.
        
        Args:
            chunk_size: Maximum characters per chunk (default: 1024)
            chunk_overlap: Characters to overlap between chunks (default: 200)
            separator: Character to use for splitting (default: space)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create sentence splitter with our settings
        self.node_parser = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator
        )
        
        logger.info(
            f"Initialized FlexCube chunker: "
            f"size={chunk_size}, overlap={chunk_overlap}"
        )
    
    def chunk_documents(self, documents: List[Document]) -> List:
        """
        Chunk a list of documents into nodes.
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List: List of Node objects (chunks)
        """
        logger.info(f"Chunking {len(documents)} documents")
        nodes = self.node_parser.get_nodes_from_documents(documents)
        logger.info(f"Created {len(nodes)} chunks from documents")
        return nodes


def create_chunker(
    chunk_size: int = 1024,
    chunk_overlap: int = 200
) -> FlexCubeChunker:
    """
    Factory function to create a FlexCube chunker.
    
    Args:
        chunk_size: Maximum characters per chunk
        chunk_overlap: Characters to overlap between chunks
        
    Returns:
        FlexCubeChunker: Configured chunker instance
    """
    return FlexCubeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


