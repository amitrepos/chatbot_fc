"""
RAG Pipeline Orchestrator

This module provides the main RAG pipeline that orchestrates all components:
- Document loading
- Text chunking
- Embedding generation
- Vector storage in Qdrant
- Query processing
"""

from typing import List, Optional
from loguru import logger
import os

from .document_loader import FlexCubeDocumentLoader
from .chunking import FlexCubeChunker
from .embeddings import BGEEmbeddings
from .vector_store import FlexCubeVectorStore
from .query_engine import FlexCubeQueryEngine


class FlexCubeRAGPipeline:
    """
    Main RAG pipeline orchestrator for FlexCube AI Assistant.
    
    Handles the complete workflow from document ingestion to query answering.
    """
    
    def __init__(
        self,
        data_dir: str = "/var/www/chatbot_FC/data/documents",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "flexcube_docs",
        ollama_url: str = "http://localhost:11434",
        llm_model: str = "mistral:7b",
        embedding_model: str = "BAAI/bge-large-en-v1.5"
    ):
        """
        Initialize RAG pipeline with all components.
        
        Args:
            data_dir: Directory containing FlexCube documents
            qdrant_host: Qdrant server hostname
            qdrant_port: Qdrant server port
            collection_name: Qdrant collection name
            ollama_url: Ollama API URL
            llm_model: Ollama model name
            embedding_model: HuggingFace embedding model name
        """
        logger.info("Initializing FlexCube RAG Pipeline")
        
        # Initialize components
        self.document_loader = FlexCubeDocumentLoader(data_dir=data_dir)
        self.chunker = FlexCubeChunker()
        self.embeddings = BGEEmbeddings(model_name=embedding_model)
        self.vector_store = FlexCubeVectorStore(
            host=qdrant_host,
            port=qdrant_port,
            collection_name=collection_name,
            embedding_dimension=1024
        )
        
        # Create collection if needed
        self.vector_store.create_collection_if_not_exists()
        
        # Initialize query engine (will be created after indexing)
        self.query_engine: Optional[FlexCubeQueryEngine] = None
        self.ollama_url = ollama_url
        self.llm_model = llm_model
        
        logger.info("RAG Pipeline initialized")
    
    def index_documents(
        self,
        file_paths: Optional[List[str]] = None,
        directory: Optional[str] = None
    ) -> int:
        """
        Index documents into the vector store.
        
        Args:
            file_paths: List of specific file paths to index
            directory: Directory to index (if file_paths not provided)
            
        Returns:
            int: Number of documents indexed
        """
        logger.info("Starting document indexing")
        
        # Load documents
        if file_paths:
            all_documents = []
            for file_path in file_paths:
                try:
                    docs = self.document_loader.load_file(file_path)
                    all_documents.extend(docs)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
        else:
            all_documents = self.document_loader.load_directory(directory)
        
        if not all_documents:
            logger.warning("No documents to index")
            return 0
        
        logger.info(f"Loaded {len(all_documents)} documents, starting chunking")
        
        # Chunk documents
        nodes = self.chunker.chunk_documents(all_documents)
        
        logger.info(f"Created {len(nodes)} chunks, starting indexing")
        
        # Create index and add nodes
        from llama_index.core import VectorStoreIndex
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.query_engine import RetrieverQueryEngine
        
        storage_context = self.vector_store.get_storage_context()
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            embed_model=self.embeddings.get_embedding_model()
        )
        
        # Initialize query engine with the index
        self.query_engine = FlexCubeQueryEngine(
            vector_store=self.vector_store,
            embedding_model=self.embeddings,
            llm_model=self.llm_model,
            ollama_url=self.ollama_url
        )
        
        # Replace the index in query engine
        self.query_engine.index = index
        self.query_engine.retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=5
        )
        self.query_engine.query_engine = RetrieverQueryEngine(
            retriever=self.query_engine.retriever,
            response_synthesizer=self.query_engine.response_synthesizer
        )
        
        logger.info(f"Indexed {len(nodes)} chunks successfully")
        return len(nodes)
    
    def query(self, question: str) -> tuple[str, List[str]]:
        """
        Query the RAG system.
        
        Args:
            question: User's question
            
        Returns:
            tuple: (answer, sources) - Answer text and list of source file paths
        """
        if self.query_engine is None:
            raise RuntimeError("Query engine not initialized. Please index documents first.")
        
        return self.query_engine.query(question)
    
    def get_stats(self) -> dict:
        """
        Get pipeline statistics.
        
        Returns:
            dict: Statistics about the pipeline
        """
        try:
            collections = self.vector_store.client.get_collections()
            collection_info = None
            for col in collections.collections:
                if col.name == self.vector_store.collection_name:
                    collection_info = self.vector_store.client.get_collection(
                        self.vector_store.collection_name
                    )
                    break
            
            stats = {
                "collection_name": self.vector_store.collection_name,
                "vector_dimension": self.vector_store.embedding_dimension,
                "documents_indexed": collection_info.points_count if collection_info else 0
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

