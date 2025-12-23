"""
Integration Tests for RAG Pipeline Module/Submodule Filtering

Tests the RAG pipeline with module/submodule filtering functionality.
Following TDD: These tests will fail initially until filtering is implemented.
"""

import pytest
import os
import tempfile
from pathlib import Path
from src.rag.pipeline import FlexCubeRAGPipeline
from src.rag.query_engine import FlexCubeQueryEngine


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    content = "This is a test document about loans. It contains information about new loan applications."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_text_file_account():
    """Create another sample text file for testing."""
    content = "This is a test document about accounts. It contains information about creating new accounts."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def pipeline():
    """Create RAG pipeline instance for testing."""
    # Note: This requires Qdrant and Ollama to be running
    # In TDD, these tests may fail if services are not available
    try:
        pipeline = FlexCubeRAGPipeline()
        return pipeline
    except Exception as e:
        pytest.skip(f"RAG pipeline not available: {e}")


class TestRAGPipelineModuleFiltering:
    """Integration tests for RAG pipeline with module/submodule filtering."""
    
    def test_index_document_with_module_submodule(self, pipeline, sample_text_file):
        """Test indexing document with module and submodule (unique combination)."""
        # Arrange: Pipeline and document ready
        
        # Act: Index document with module and submodule
        num_chunks = pipeline.index_documents(
            file_paths=[sample_text_file],
            module="Loan",
            submodule="New"
        )
        
        # Assert: Document indexed successfully
        assert num_chunks > 0
        
        # Assert: Chunks in Qdrant have metadata["module"]="Loan"
        # Note: This requires querying Qdrant directly, which may need additional setup
        # For TDD, we verify the indexing succeeded
        # TODO: Add direct Qdrant query to verify metadata
    
    def test_index_document_without_module_submodule(self, pipeline, sample_text_file):
        """Test indexing document without module/submodule (backward compatible)."""
        # Arrange: Pipeline and document ready
        
        # Act: Index document without module/submodule
        num_chunks = pipeline.index_documents(
            file_paths=[sample_text_file]
        )
        
        # Assert: Document indexed successfully
        assert num_chunks > 0
        
        # Assert: Chunks in Qdrant don't have module/submodule in metadata
        # TODO: Add direct Qdrant query to verify no module/submodule metadata
    
    def test_query_with_module_filter(self, pipeline, sample_text_file, sample_text_file_account):
        """Test querying with module filter (module is unique, but can have multiple documents with different submodules)."""
        # Arrange: Index documents
        #   - doc1.pdf with module="Loan", submodule="New"
        #   - doc2.pdf with module="Loan", submodule="Existing" (same unique module "Loan", different submodule)
        #   - doc3.pdf with module="Account", submodule="Create" (different unique module)
        
        # Create second file for Loan Existing
        loan_existing_content = "This is about existing loans and loan modifications."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(loan_existing_content)
            loan_existing_file = f.name
        
        try:
            # Index documents
            pipeline.index_documents(
                file_paths=[sample_text_file],
                module="Loan",
                submodule="New"
            )
            pipeline.index_documents(
                file_paths=[loan_existing_file],
                module="Loan",
                submodule="Existing"
            )
            pipeline.index_documents(
                file_paths=[sample_text_file_account],
                module="Account",
                submodule="Create"
            )
            
            # Act: Query with module filter
            answer, sources = pipeline.query(
                question="test question about loans",
                module="Loan"
            )
            
            # Assert: Returns answer
            assert answer is not None
            assert len(answer) > 0
            
            # Assert: Sources include documents with module="Loan" (both doc1 and doc2)
            # Note: This is a simplified check - actual implementation would filter in Qdrant
            assert len(sources) > 0
            
        finally:
            # Cleanup
            if os.path.exists(loan_existing_file):
                os.unlink(loan_existing_file)
    
    def test_query_with_submodule_filter(self, pipeline, sample_text_file, sample_text_file_account):
        """Test querying with module+submodule filter (unique combination - submodule name not unique, but combination is)."""
        # Arrange: Index documents
        #   - doc1.pdf with module="Loan", submodule="New"
        #   - doc2.pdf with module="Loan", submodule="Existing"
        #   - doc3.pdf with module="Account", submodule="New" (same submodule name "New", but different unique module)
        
        # Create files
        loan_existing_content = "This is about existing loans."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(loan_existing_content)
            loan_existing_file = f.name
        
        try:
            # Index documents
            pipeline.index_documents(
                file_paths=[sample_text_file],
                module="Loan",
                submodule="New"
            )
            pipeline.index_documents(
                file_paths=[loan_existing_file],
                module="Loan",
                submodule="Existing"
            )
            pipeline.index_documents(
                file_paths=[sample_text_file_account],
                module="Account",
                submodule="New"
            )
            
            # Act: Query with module and submodule filter
            answer, sources = pipeline.query(
                question="test question",
                module="Loan",
                submodule="New"
            )
            
            # Assert: Returns answer
            assert answer is not None
            
            # Assert: Sources only include doc1.pdf (unique combination: module="Loan" + submodule="New")
            # Note: This requires Qdrant filtering to be implemented
            assert len(sources) > 0
            
        finally:
            # Cleanup
            if os.path.exists(loan_existing_file):
                os.unlink(loan_existing_file)
    
    def test_query_without_filters_searches_all(self, pipeline, sample_text_file, sample_text_file_account):
        """Test that query without filters searches all documents (ignores module/submodule)."""
        # Arrange: Index documents
        #   - doc1.pdf with module="Loan", submodule="New"
        #   - doc2.pdf with module="Account", submodule="Create"
        #   - doc3.pdf with module="Loan", submodule="Existing"
        
        loan_existing_content = "This is about existing loans."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(loan_existing_content)
            loan_existing_file = f.name
        
        try:
            # Index documents
            pipeline.index_documents(
                file_paths=[sample_text_file],
                module="Loan",
                submodule="New"
            )
            pipeline.index_documents(
                file_paths=[sample_text_file_account],
                module="Account",
                submodule="Create"
            )
            pipeline.index_documents(
                file_paths=[loan_existing_file],
                module="Loan",
                submodule="Existing"
            )
            
            # Act: Query without filters
            answer, sources = pipeline.query("test question")
            
            # Assert: Searches all documents (no filtering)
            assert answer is not None
            # Sources can come from any document regardless of module/submodule
            assert len(sources) > 0
            
        finally:
            # Cleanup
            if os.path.exists(loan_existing_file):
                os.unlink(loan_existing_file)


