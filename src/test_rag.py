#!/usr/bin/env python3
"""
Test Script for RAG Pipeline

This script tests the complete RAG pipeline with sample documents.
Run this to verify all components are working correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.rag.pipeline import FlexCubeRAGPipeline
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_rag_pipeline():
    """Test the complete RAG pipeline."""
    logger.info("=" * 60)
    logger.info("Testing FlexCube RAG Pipeline")
    logger.info("=" * 60)
    
    # Initialize pipeline
    logger.info("\n1. Initializing RAG Pipeline...")
    pipeline = FlexCubeRAGPipeline()
    logger.info("✅ Pipeline initialized")
    
    # Check if documents exist
    data_dir = "/var/www/chatbot_FC/data/documents"
    import glob
    pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
    docx_files = glob.glob(os.path.join(data_dir, "*.docx"))
    txt_files = glob.glob(os.path.join(data_dir, "*.txt"))
    
    all_files = pdf_files + docx_files + txt_files
    
    if not all_files:
        logger.warning(f"\n⚠️  No documents found in {data_dir}")
        logger.info("Creating a sample test document...")
        
        # Create a sample test document
        sample_file = os.path.join(data_dir, "sample_flexcube.txt")
        with open(sample_file, 'w') as f:
            f.write("""
FlexCube Universal Banking System - Sample Documentation

Account Management:
FlexCube provides comprehensive account management capabilities. Users can create,
modify, and close various types of accounts including savings, current, and fixed
deposit accounts. Each account has a unique account number and is associated with
a customer profile.

Transaction Processing:
The system supports multiple transaction types including deposits, withdrawals,
transfers, and payments. All transactions are processed in real-time and are
recorded in the transaction ledger. The system maintains a complete audit trail
for compliance purposes.

Error Handling:
Common errors in FlexCube include:
- ERR_ACC_NOT_FOUND: Account does not exist
- ERR_INSUFFICIENT_FUNDS: Account balance is insufficient
- ERR_INVALID_TRANSACTION: Transaction type is not supported

To resolve ERR_ACC_NOT_FOUND, verify the account number and ensure the account
is active. For ERR_INSUFFICIENT_FUNDS, check the account balance before
processing the transaction.
            """)
        logger.info(f"✅ Created sample document: {sample_file}")
        all_files = [sample_file]
    
    # Index documents
    logger.info(f"\n2. Indexing {len(all_files)} document(s)...")
    try:
        num_chunks = pipeline.index_documents(file_paths=all_files)
        logger.info(f"✅ Indexed {num_chunks} chunks successfully")
    except Exception as e:
        logger.error(f"❌ Error indexing documents: {e}")
        return False
    
    # Get stats
    logger.info("\n3. Pipeline Statistics:")
    stats = pipeline.get_stats()
    for key, value in stats.items():
        logger.info(f"   {key}: {value}")
    
    # Test queries
    logger.info("\n4. Testing Queries...")
    test_questions = [
        "What is FlexCube?",
        "How do I handle ERR_ACC_NOT_FOUND error?",
        "What types of accounts does FlexCube support?",
        "How are transactions processed?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n   Question {i}: {question}")
        try:
            answer = pipeline.query(question)
            logger.info(f"   Answer: {answer[:200]}...")
            logger.info("   ✅ Query successful")
        except Exception as e:
            logger.error(f"   ❌ Query failed: {e}")
            return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All tests passed!")
    logger.info("=" * 60)
    return True


if __name__ == "__main__":
    success = test_rag_pipeline()
    sys.exit(0 if success else 1)


