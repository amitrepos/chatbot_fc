"""
Document Loader Module

This module provides document loading capabilities for FlexCube documentation.
Supports PDF, DOCX, and plain text files commonly used in FlexCube documentation.
"""

from pathlib import Path
from typing import List, Optional
from llama_index.core import Document
from llama_index.readers.file import PDFReader, DocxReader
from loguru import logger
import os


class FlexCubeDocumentLoader:
    """
    Document loader for FlexCube documentation files.
    
    Supports multiple file formats:
    - PDF (.pdf) - Most common for FlexCube manuals
    - DOCX (.docx) - Word documents
    - TXT (.txt) - Plain text files
    """
    
    def __init__(self, data_dir: str = "/var/www/chatbot_FC/data/documents"):
        """
        Initialize document loader.
        
        Args:
            data_dir: Directory containing FlexCube documents
        """
        self.data_dir = Path(data_dir)
        self.pdf_reader = PDFReader()
        self.docx_reader = DocxReader()
        
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Data directory created: {self.data_dir}")
    
    def load_pdf(self, file_path: str) -> List[Document]:
        """
        Load a PDF document.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List[Document]: List of Document objects from the PDF
        """
        logger.info(f"Loading PDF: {file_path}")
        documents = self.pdf_reader.load_data(file=Path(file_path))
        logger.info(f"Loaded {len(documents)} pages from PDF")
        return documents
    
    def load_docx(self, file_path: str) -> List[Document]:
        """
        Load a DOCX document.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            List[Document]: List of Document objects from the DOCX
        """
        logger.info(f"Loading DOCX: {file_path}")
        documents = self.docx_reader.load_data(file=Path(file_path))
        logger.info(f"Loaded {len(documents)} sections from DOCX")
        return documents
    
    def load_text(self, file_path: str) -> List[Document]:
        """
        Load a plain text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            List[Document]: List containing a single Document object
        """
        logger.info(f"Loading text file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        document = Document(text=content, metadata={"source": file_path})
        logger.info(f"Loaded text file: {len(content)} characters")
        return [document]
    
    def load_file(self, file_path: str, module: Optional[str] = None, submodule: Optional[str] = None) -> List[Document]:
        """
        Load a document file, automatically detecting the format.
        
        Args:
            file_path: Path to document file
            module: Optional module name (unique module, e.g., "Loan", "Account")
            submodule: Optional submodule name (NOT unique, can exist under different modules, e.g., "New")
            
        Returns:
            List[Document]: List of Document objects with module/submodule in metadata
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        suffix = path.suffix.lower()
        
        # Load documents based on file type
        if suffix == '.pdf':
            documents = self.load_pdf(file_path)
        elif suffix == '.docx':
            documents = self.load_docx(file_path)
        elif suffix == '.txt':
            documents = self.load_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        # Add module/submodule to metadata for all documents
        for doc in documents:
            if module:
                doc.metadata["module"] = module
            if submodule:
                doc.metadata["submodule"] = submodule
            # Ensure source is set
            if "source" not in doc.metadata:
                doc.metadata["source"] = file_path
        
        return documents
    
    def load_directory(self, directory: Optional[str] = None) -> List[Document]:
        """
        Load all supported documents from a directory.
        
        Args:
            directory: Directory to load from (defaults to data_dir)
            
        Returns:
            List[Document]: List of all Document objects from the directory
        """
        if directory is None:
            directory = self.data_dir
        else:
            directory = Path(directory)
        
        all_documents = []
        supported_extensions = {'.pdf', '.docx', '.txt'}
        
        logger.info(f"Loading documents from directory: {directory}")
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    documents = self.load_file(str(file_path))
                    all_documents.extend(documents)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
        
        logger.info(f"Loaded {len(all_documents)} total documents from directory")
        return all_documents




