"""
Query Engine Module

This module provides the main query engine that combines:
- Vector retrieval from Qdrant
- LLM generation via Ollama/Mistral
- Source citation for answers
"""

from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import ResponseMode
from typing import Optional, List
from loguru import logger

from .ollama_llm import OllamaLLM
from .vector_store import FlexCubeVectorStore
from .embeddings import BGEEmbeddings


class FlexCubeQueryEngine:
    """
    Main query engine for FlexCube RAG system.
    
    Combines vector retrieval with LLM generation to answer questions
    about FlexCube documentation. Provides source citations for answers.
    """
    
    def __init__(
        self,
        vector_store: FlexCubeVectorStore,
        embedding_model: BGEEmbeddings,
        llm_model: str = "mistral:7b",
        ollama_url: str = "http://localhost:11434",
        similarity_top_k: int = 5
    ):
        """
        Initialize query engine.
        
        Args:
            vector_store: Qdrant vector store instance
            embedding_model: BGE embeddings model
            llm_model: Ollama model name
            ollama_url: Ollama API URL
            similarity_top_k: Number of top chunks to retrieve
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.similarity_top_k = similarity_top_k
        
        logger.info("Initializing FlexCube query engine")
        
        # Create Ollama LLM
        self.llm = OllamaLLM(
            model=llm_model,
            base_url=ollama_url
        )
        
        # Create vector store index
        storage_context = vector_store.get_storage_context()
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store.get_vector_store(),
            embed_model=embedding_model.get_embedding_model(),
            storage_context=storage_context
        )
        
        # Create retriever
        self.retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=similarity_top_k
        )
        
        # Create response synthesizer with source citation
        self.response_synthesizer = get_response_synthesizer(
            llm=self.llm,
            response_mode=ResponseMode.COMPACT  # Compact mode for concise answers
        )
        
        # Create query engine
        self.query_engine = RetrieverQueryEngine(
            retriever=self.retriever,
            response_synthesizer=self.response_synthesizer
        )
        
        logger.info("Query engine initialized successfully")
    
    def query(self, question: str) -> tuple[str, List[str]]:
        """
        Query the RAG system with a question.
        
        Args:
            question: User's question about FlexCube
            
        Returns:
            tuple: (answer, sources) - Answer text and list of source file paths
        """
        logger.info(f"Processing query: {question[:100]}...")
        
        try:
            # Initialize sources list fresh for each query
            sources = []
            seen_sources = set()
            
            # First, retrieve nodes to get sources BEFORE querying
            # This ensures we always have source information
            retrieved_nodes = self.retriever.retrieve(question)
            
            # Keywords that suggest FlexCube-specific content (check early)
            question_lower = question.lower()
            flexcube_keywords = ['flexcube', 'oracle', 'banking', 'account', 'transaction', 
                               'loan', 'deposit', 'customer', 'error', 'module', 'screen',
                               'microfinance', 'ledger', 'gl', 'branch', 'payment', 'schedule',
                               'processing', 'rollover', 'delinquency', 'status', 'simulation']
            is_flexcube_related = any(keyword in question_lower for keyword in flexcube_keywords)
            
            # Check if we have retrieved nodes with sufficient relevance
            has_relevant_sources = False
            if retrieved_nodes:
                # For FlexCube questions, always consider sources relevant
                if is_flexcube_related:
                    has_relevant_sources = True
                else:
                    # For general questions, check similarity scores
                    for node in retrieved_nodes[:3]:
                        if hasattr(node, 'score') and node.score is not None:
                            if node.score > 0.3:
                                has_relevant_sources = True
                                break
                        else:
                            has_relevant_sources = True
                            break
            
            # Extract sources from retrieved nodes
            if has_relevant_sources and retrieved_nodes:
                # Extract sources from retrieved nodes
                for node in retrieved_nodes:
                    source = None
                    
                    # Try to get source from node metadata
                    # LlamaIndex stores file info in 'file_name' or 'source' fields
                    if hasattr(node, 'metadata') and node.metadata:
                        source = (node.metadata.get('file_name', None) or 
                                 node.metadata.get('source', None) or 
                                 node.metadata.get('file_path', None))
                    elif hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                        source = (node.node.metadata.get('file_name', None) or
                                 node.node.metadata.get('source', None) or
                                 node.node.metadata.get('file_path', None))
                    
                    # Add source if found and not duplicate
                    if source and source not in seen_sources:
                        # Extract just filename for cleaner display
                        if '/' in source:
                            filename = source.split('/')[-1]
                            sources.append(filename)
                        else:
                            sources.append(source)
                        seen_sources.add(source)
                        
                        # Limit to top 5 sources
                        if len(sources) >= 5:
                            break
            
            # Now query the LLM with the retrieved context
            response = self.query_engine.query(question)
            answer = str(response)
            
            # Check if answer seems to be from general knowledge vs. documents
            answer_lower = answer.lower()
            
            # Phrases that indicate the LLM found the context/documents irrelevant
            # When the LLM says these, it means the RAG documents don't have the answer
            # Important: Include variations with "text", "context", "document", "provided"
            irrelevant_context_phrases = [
                # Direct statements about missing information
                "does not contain any information",
                "doesn't contain any information",
                "does not contain information",
                "doesn't contain information",
                "no information about",
                "no information regarding",
                "not contain any information",
                # Context/text/document variations
                "text does not contain",
                "text doesn't contain",
                "context does not contain",
                "context doesn't contain",
                "document does not contain",
                "provided text does not",
                "provided context does not",
                # Relevance statements  
                "not related to",
                "not relevant to",
                "isn't relevant",
                "is not relevant",
                "doesn't pertain",
                "does not pertain",
                # Inability statements
                "i don't have information",
                "i cannot find",
                "cannot answer based on",
                "unable to find",
                "no relevant information",
                "outside the scope",
                "not mentioned in"
            ]
            
            # Check if LLM indicated the context was not useful
            context_was_irrelevant = any(phrase in answer_lower for phrase in irrelevant_context_phrases)
            
            # Log for debugging
            logger.debug(f"is_flexcube_related: {is_flexcube_related}, context_was_irrelevant: {context_was_irrelevant}, has_relevant_sources: {has_relevant_sources}")
            
            # CRITICAL: If RAG context was irrelevant and question is NOT FlexCube-related,
            # make a second call to the LLM to answer from general knowledge
            # This is the TWO-TIER flow: RAG first, then general knowledge fallback
            if context_was_irrelevant and not is_flexcube_related:
                logger.info("RAG context irrelevant for general question - asking LLM to answer from general knowledge")
                
                # Create a prompt that asks the LLM to answer from its own knowledge
                general_knowledge_prompt = f"""You are a helpful AI assistant. Answer the following question from your general knowledge.

Question: {question}

Please provide a helpful and accurate answer."""
                
                # Call LLM directly without RAG context
                general_response = self.llm.complete(general_knowledge_prompt)
                answer = str(general_response.text).strip()
                
                # Clear sources - this is from model's general knowledge
                sources = []
                seen_sources = set()
                logger.info("Answered from general knowledge - no document sources")
            
            elif context_was_irrelevant and is_flexcube_related:
                # FlexCube question but LLM indicated context wasn't helpful
                # However, if we already have sources from retrieval, KEEP them
                # The LLM might just be using different phrasing
                if sources:
                    logger.info("FlexCube question - keeping existing sources despite LLM phrasing")
                else:
                    logger.info("FlexCube question but no sources found - keeping RAG answer")
            
            elif not is_flexcube_related and not has_relevant_sources:
                # General question with low relevance - fall back to general knowledge
                logger.info("General question with low relevance - asking LLM for general knowledge answer")
                
                general_knowledge_prompt = f"""You are a helpful AI assistant. Answer the following question from your general knowledge.

Question: {question}

Please provide a helpful and accurate answer."""
                
                general_response = self.llm.complete(general_knowledge_prompt)
                answer = str(general_response.text).strip()
                
                sources = []
                seen_sources = set()
                logger.info("Answered from general knowledge - no document sources")
            
            # Also try to get sources from response object (as backup)
            # Only if:
            # 1. We don't have sources yet AND
            # 2. Question is FlexCube-related AND
            # 3. Context was NOT marked as irrelevant (don't re-add sources if LLM said they weren't useful)
            if not sources and is_flexcube_related and not context_was_irrelevant:
                source_nodes = None
                
                # Method 1: Direct source_nodes attribute
                if hasattr(response, 'source_nodes') and response.source_nodes:
                    source_nodes = response.source_nodes
                # Method 2: Check metadata in response
                elif hasattr(response, 'metadata') and response.metadata:
                    if 'source_nodes' in response.metadata:
                        source_nodes = response.metadata['source_nodes']
                
                # Extract sources from response source_nodes
                if source_nodes:
                    for node in source_nodes[:5]:
                        source = None
                        
                        # Try different node structures
                        if hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                            source = (node.node.metadata.get('file_name', None) or
                                     node.node.metadata.get('source', None) or
                                     node.node.metadata.get('file_path', None))
                        elif hasattr(node, 'metadata'):
                            source = (node.metadata.get('file_name', None) or
                                     node.metadata.get('source', None) or
                                     node.metadata.get('file_path', None))
                        elif isinstance(node, dict):
                            source = (node.get('file_name', None) or
                                     node.get('source', None) or
                                     node.get('file_path', None))
                        
                        if source and source not in seen_sources:
                            filename = source.split('/')[-1] if '/' in source else source
                            sources.append(filename)
                            seen_sources.add(source)
            
            logger.info(f"Query completed: {len(answer)} characters, {len(sources)} sources")
            logger.debug(f"Sources found: {sources}")
            return answer, sources
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise
    
    def add_documents(self, documents):
        """
        Add documents to the index (for incremental indexing).
        
        Args:
            documents: List of Document objects to add
        """
        logger.info(f"Adding {len(documents)} documents to index")
        self.index.insert(documents)
        logger.info("Documents added successfully")

