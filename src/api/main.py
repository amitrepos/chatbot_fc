"""
FastAPI Main Application

Main FastAPI application with endpoints for:
- Querying the RAG pipeline
- Document management
- Health checks
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.rag.pipeline import FlexCubeRAGPipeline

# Initialize FastAPI app
app = FastAPI(
    title="NUO CORE FlexCube AI Assistant API",
    description="RAG-based AI assistant for FlexCube banking software",
    version="1.0.0"
)

# CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global RAG pipeline instance
rag_pipeline: Optional[FlexCubeRAGPipeline] = None


def get_pipeline() -> FlexCubeRAGPipeline:
    """Get or initialize RAG pipeline."""
    global rag_pipeline
    if rag_pipeline is None:
        logger.info("Initializing RAG pipeline...")
        rag_pipeline = FlexCubeRAGPipeline()
        
        # Check if documents are already indexed, if so initialize query engine
        try:
            stats = rag_pipeline.get_stats()
            if stats.get("documents_indexed", 0) > 0:
                logger.info(f"Found {stats['documents_indexed']} indexed documents, initializing query engine...")
                # Create query engine from existing index
                from llama_index.core import VectorStoreIndex
                from llama_index.core.retrievers import VectorIndexRetriever
                from llama_index.core.query_engine import RetrieverQueryEngine
                
                storage_context = rag_pipeline.vector_store.get_storage_context()
                index = VectorStoreIndex.from_vector_store(
                    vector_store=rag_pipeline.vector_store.get_vector_store(),
                    embed_model=rag_pipeline.embeddings.get_embedding_model(),
                    storage_context=storage_context
                )
                
                from src.rag.query_engine import FlexCubeQueryEngine
                rag_pipeline.query_engine = FlexCubeQueryEngine(
                    vector_store=rag_pipeline.vector_store,
                    embedding_model=rag_pipeline.embeddings,
                    llm_model=rag_pipeline.llm_model,
                    ollama_url=rag_pipeline.ollama_url
                )
                rag_pipeline.query_engine.index = index
                rag_pipeline.query_engine.retriever = VectorIndexRetriever(
                    index=index,
                    similarity_top_k=5
                )
                rag_pipeline.query_engine.query_engine = RetrieverQueryEngine(
                    retriever=rag_pipeline.query_engine.retriever,
                    response_synthesizer=rag_pipeline.query_engine.response_synthesizer
                )
                logger.info("Query engine initialized from existing index")
        except Exception as e:
            logger.warning(f"Could not initialize query engine from existing index: {e}")
        
        logger.info("RAG pipeline initialized")
    return rag_pipeline


# Request/Response Models
class QueryRequest(BaseModel):
    """Query request model."""
    question: str
    top_k: Optional[int] = 5


class QueryResponse(BaseModel):
    """Query response model."""
    answer: str
    sources: List[str]
    processing_time: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    pipeline_ready: bool
    stats: Optional[dict] = None


# Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Enhanced web interface with tabs, image upload, and document management."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ask-NUO</title>
        <style>
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                font-weight: 600;
            }
            .header p {
                opacity: 0.9;
                font-size: 1.1em;
            }
            .tabs {
                display: flex;
                background: #f8f9fa;
                border-bottom: 2px solid #e9ecef;
            }
            .tab {
                flex: 1;
                padding: 15px 20px;
                background: transparent;
                border: none;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                color: #6c757d;
                transition: all 0.3s;
                border-bottom: 3px solid transparent;
            }
            .tab:hover {
                background: #e9ecef;
                color: #495057;
            }
            .tab.active {
                color: #667eea;
                background: white;
                border-bottom-color: #667eea;
            }
            .tab-content {
                display: none;
                padding: 30px;
            }
            .tab-content.active {
                display: block;
            }
            .query-section {
                margin-bottom: 25px;
            }
            .query-section label {
                display: block;
                font-weight: 600;
                margin-bottom: 10px;
                color: #495057;
            }
            textarea, input[type="text"] {
                width: 100%;
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            textarea {
                min-height: 120px;
                resize: vertical;
            }
            textarea:focus, input[type="text"]:focus {
                outline: none;
                border-color: #667eea;
            }
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            button.secondary {
                background: #6c757d;
            }
            button.danger {
                background: #dc3545;
            }
            button.success {
                background: #28a745;
            }
            .image-upload-area {
                border: 3px dashed #667eea;
                border-radius: 12px;
                padding: 40px;
                text-align: center;
                background: #f8f9ff;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 20px;
            }
            .image-upload-area:hover {
                background: #f0f2ff;
                border-color: #764ba2;
            }
            .image-upload-area.dragover {
                background: #e8ebff;
                border-color: #764ba2;
                transform: scale(1.02);
            }
            .image-preview {
                margin-top: 20px;
                text-align: center;
            }
            .image-preview img {
                max-width: 100%;
                max-height: 400px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .image-preview-actions {
                margin-top: 15px;
            }
            .answer {
                margin-top: 25px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .sources {
                margin-top: 20px;
                padding: 15px;
                background: #e8f5e9;
                border-radius: 8px;
                border-left: 4px solid #28a745;
            }
            .sources strong {
                color: #28a745;
                display: block;
                margin-bottom: 10px;
            }
            .sources ul {
                margin: 10px 0 0 0;
                padding-left: 20px;
            }
            .sources code {
                background: #c8e6c9;
                padding: 2px 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                color: #2e7d32;
            }
            .loading {
                text-align: center;
                padding: 30px;
                color: #667eea;
            }
            .loading::after {
                content: '...';
                animation: dots 1.5s steps(4, end) infinite;
            }
            @keyframes dots {
                0%, 20% { content: '.'; }
                40% { content: '..'; }
                60%, 100% { content: '...'; }
            }
            .error {
                color: #dc3545;
                padding: 15px;
                background: #f8d7da;
                border-radius: 8px;
                border-left: 4px solid #dc3545;
                margin-top: 15px;
            }
            .success-message {
                color: #28a745;
                padding: 15px;
                background: #d4edda;
                border-radius: 8px;
                border-left: 4px solid #28a745;
                margin-top: 15px;
            }
            .conversation-history {
                margin-top: 30px;
                border-top: 2px solid #e9ecef;
                padding-top: 20px;
            }
            .conversation-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            .conversation-item {
                margin-bottom: 20px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .conversation-question {
                font-weight: 600;
                color: #495057;
                margin-bottom: 15px;
                padding: 12px;
                background: white;
                border-radius: 6px;
            }
            .documents-list {
                margin-top: 20px;
            }
            .document-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                margin-bottom: 10px;
            }
            .document-info {
                flex: 1;
            }
            .document-name {
                font-weight: 600;
                color: #495057;
            }
            .document-meta {
                font-size: 12px;
                color: #6c757d;
                margin-top: 5px;
            }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 10px;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.3s;
            }
            .hidden {
                display: none;
            }
            @media (max-width: 768px) {
                .container {
                    margin: 10px;
                    border-radius: 8px;
                }
                .header h1 {
                    font-size: 2em;
                }
                .tabs {
                    flex-direction: column;
                }
                .tab {
                    border-bottom: 1px solid #e9ecef;
                    border-right: none;
                }
                .tab.active {
                    border-bottom-color: #667eea;
                }
                .button-group {
                    flex-direction: column;
                }
                button {
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 Ask-NUO</h1>
                <p>AI Assistant for FlexCube Banking Software Documentation</p>
            </div>
            
            <div class="tabs">
                <button class="tab active" onclick="switchTab('text')">📝 Text Query</button>
                <button class="tab" onclick="switchTab('image')">🖼️ Image Query</button>
                <button class="tab" onclick="switchTab('documents')">📚 Documents</button>
            </div>
            
            <!-- Text Query Tab -->
            <div id="text-tab" class="tab-content active">
                <div class="query-section">
                    <label for="question"><strong>Your Question:</strong></label>
                    <textarea id="question" placeholder="e.g., How do I handle ERR_ACC_NOT_FOUND error?"></textarea>
                    <div class="button-group">
                        <button onclick="askQuestion()" id="askBtn">Ask Question</button>
                        <button class="secondary" onclick="clearCurrentAnswer()">Clear</button>
                    </div>
                </div>
                <div id="current-answer"></div>
                <div class="conversation-history" id="conversation-history" style="display: none;">
                    <div class="conversation-header">
                        <h3>📜 Conversation History</h3>
                        <button class="danger" onclick="clearHistory()">Clear History</button>
                    </div>
                    <div id="history-items"></div>
                </div>
            </div>
            
            <!-- Image Query Tab -->
            <div id="image-tab" class="tab-content">
                <div class="query-section">
                    <label><strong>Upload Screenshot:</strong></label>
                    <div class="image-upload-area" id="imageUploadArea" onclick="document.getElementById('imageInput').click()">
                        <p style="font-size: 18px; margin-bottom: 10px;">📸 Click or drag & drop image here</p>
                        <p style="color: #6c757d; font-size: 14px;">Supports: PNG, JPG, JPEG (Max 10MB)</p>
                    </div>
                    <input type="file" id="imageInput" accept="image/*" style="display: none;" onchange="handleImageSelect(event)">
                    <div id="imagePreview" class="image-preview hidden"></div>
                    <div class="button-group" id="imageButtons" style="display: none;">
                        <button onclick="askImageQuestion()" id="askImageBtn">Analyze Image</button>
                        <button class="secondary" onclick="clearImage()">Clear Image</button>
                    </div>
                </div>
                <div id="image-answer"></div>
            </div>
            
            <!-- Documents Tab -->
            <div id="documents-tab" class="tab-content">
                <div class="query-section">
                    <label><strong>Upload Document:</strong></label>
                    <div class="image-upload-area" onclick="document.getElementById('docInput').click()">
                        <p style="font-size: 18px; margin-bottom: 10px;">📄 Click or drag & drop document here</p>
                        <p style="color: #6c757d; font-size: 14px;">Supports: PDF, DOCX, TXT</p>
                    </div>
                    <input type="file" id="docInput" accept=".pdf,.docx,.txt" style="display: none;" onchange="handleDocumentSelect(event)">
                    <div id="uploadProgress" class="hidden">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                        </div>
                        <p id="uploadStatus" style="text-align: center; margin-top: 10px; color: #667eea;"></p>
                    </div>
                </div>
                <div id="documents-list-section">
                    <h3 style="margin: 25px 0 15px 0;">📚 Indexed Documents</h3>
                    <div id="documentsList" class="documents-list">
                        <p style="color: #6c757d; text-align: center; padding: 20px;">Loading documents...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Global state
            let conversationHistory = JSON.parse(localStorage.getItem('flexcube_conversation_history') || '[]');
            let selectedImage = null;
            
            // Initialize
            window.addEventListener('DOMContentLoaded', function() {
                loadConversationHistory();
                loadDocuments();
                setupDragAndDrop();
            });
            
            // Tab switching
            function switchTab(tabName) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(tabName + '-tab').classList.add('active');
            }
            
            // Image handling
            function setupDragAndDrop() {
                const uploadArea = document.getElementById('imageUploadArea');
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                    uploadArea.addEventListener(eventName, preventDefaults, false);
                });
                function preventDefaults(e) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                ['dragenter', 'dragover'].forEach(eventName => {
                    uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
                });
                ['dragleave', 'drop'].forEach(eventName => {
                    uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
                });
                uploadArea.addEventListener('drop', handleDrop, false);
                function handleDrop(e) {
                    const dt = e.dataTransfer;
                    const files = dt.files;
                    if (files.length > 0) {
                        handleImageFile(files[0]);
                    }
                }
            }
            
            function handleImageSelect(event) {
                if (event.target.files && event.target.files[0]) {
                    handleImageFile(event.target.files[0]);
                }
            }
            
            function handleImageFile(file) {
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file');
                    return;
                }
                if (file.size > 10 * 1024 * 1024) {
                    alert('Image size must be less than 10MB');
                    return;
                }
                selectedImage = file;
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.getElementById('imagePreview');
                    preview.innerHTML = '<img src="' + e.target.result + '" alt="Preview">';
                    preview.classList.remove('hidden');
                    document.getElementById('imageButtons').style.display = 'flex';
                };
                reader.readAsDataURL(file);
            }
            
            function clearImage() {
                selectedImage = null;
                document.getElementById('imageInput').value = '';
                document.getElementById('imagePreview').classList.add('hidden');
                document.getElementById('imageButtons').style.display = 'none';
                document.getElementById('image-answer').innerHTML = '';
            }
            
            async function askImageQuestion() {
                if (!selectedImage) {
                    alert('Please select an image first');
                    return;
                }
                const answerDiv = document.getElementById('image-answer');
                const askBtn = document.getElementById('askImageBtn');
                askBtn.disabled = true;
                askBtn.textContent = 'Processing...';
                answerDiv.innerHTML = '<div class="loading">Analyzing image and searching for solutions</div>';
                
                try {
                    const formData = new FormData();
                    formData.append('image', selectedImage);
                    const response = await fetch('/api/query/image', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (response.ok) {
                        let html = '<div class="answer"><strong>Answer:</strong><p>' + data.answer.replace(/\\n/g, '<br>') + '</p>';
                        html += '<div class="sources"><strong>📚 Sources:</strong>';
                        if (data.sources && data.sources.length > 0) {
                            html += '<ul>';
                            data.sources.forEach(source => {
                                html += '<li><code>' + escapeHtml(source) + '</code></li>';
                            });
                            html += '</ul>';
                        } else {
                            html += '<p style="color: #95a5a6; font-style: italic;">No specific sources identified.</p>';
                        }
                        html += '</div></div>';
                        answerDiv.innerHTML = html;
                    } else {
                        answerDiv.innerHTML = '<div class="error">Error: ' + (data.detail || 'Unknown error') + '</div>';
                    }
                } catch (error) {
                    answerDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                } finally {
                    askBtn.disabled = false;
                    askBtn.textContent = 'Analyze Image';
                }
            }
            
            // Document handling
            function handleDocumentSelect(event) {
                if (event.target.files && event.target.files[0]) {
                    uploadDocument(event.target.files[0]);
                }
            }
            
            async function uploadDocument(file) {
                const formData = new FormData();
                formData.append('file', file);
                const progressDiv = document.getElementById('uploadProgress');
                const progressFill = document.getElementById('progressFill');
                const statusText = document.getElementById('uploadStatus');
                
                progressDiv.classList.remove('hidden');
                progressFill.style.width = '10%';
                statusText.textContent = 'Uploading ' + file.name + '...';
                
                try {
                    const xhr = new XMLHttpRequest();
                    xhr.upload.addEventListener('progress', (e) => {
                        if (e.lengthComputable) {
                            const percent = Math.min(90, (e.loaded / e.total) * 90);
                            progressFill.style.width = percent + '%';
                        }
                    });
                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            progressFill.style.width = '100%';
                            statusText.textContent = 'Indexing document...';
                            setTimeout(() => {
                                progressDiv.classList.add('hidden');
                                statusText.textContent = '';
                                loadDocuments();
                                document.getElementById('docInput').value = '';
                            }, 1000);
                        } else {
                            throw new Error('Upload failed');
                        }
                    };
                    xhr.open('POST', '/api/documents/upload');
                    xhr.send(formData);
                } catch (error) {
                    progressDiv.classList.add('hidden');
                    alert('Error uploading document: ' + error.message);
                }
            }
            
            async function loadDocuments() {
                try {
                    const response = await fetch('/api/documents');
                    const data = await response.json();
                    const listDiv = document.getElementById('documentsList');
                    if (data.documents && data.documents.length > 0) {
                        listDiv.innerHTML = data.documents.map(doc => `
                            <div class="document-item">
                                <div class="document-info">
                                    <div class="document-name">${escapeHtml(doc.filename)}</div>
                                    <div class="document-meta">${doc.size ? formatBytes(doc.size) : ''} ${doc.chunks ? '• ' + doc.chunks + ' chunks' : ''}</div>
                                </div>
                                <button class="danger" onclick="deleteDocument('${escapeHtml(doc.filename)}')">Delete</button>
                            </div>
                        `).join('');
                    } else {
                        listDiv.innerHTML = '<p style="color: #6c757d; text-align: center; padding: 20px;">No documents indexed yet.</p>';
                    }
                } catch (error) {
                    document.getElementById('documentsList').innerHTML = '<p class="error">Error loading documents: ' + error.message + '</p>';
                }
            }
            
            async function deleteDocument(filename) {
                if (!confirm('Are you sure you want to delete ' + filename + '?')) return;
                try {
                    const response = await fetch('/api/documents/' + encodeURIComponent(filename), {
                        method: 'DELETE'
                    });
                    if (response.ok) {
                        loadDocuments();
                    } else {
                        alert('Error deleting document');
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            // Text query functions (existing)
            function loadConversationHistory() {
                const historyDiv = document.getElementById('conversation-history');
                const historyItems = document.getElementById('history-items');
                if (conversationHistory.length > 0) {
                    historyDiv.style.display = 'block';
                    historyItems.innerHTML = conversationHistory.slice().reverse().map(item => {
                        let html = '<div class="conversation-item">';
                        html += '<div class="conversation-question">❓ ' + escapeHtml(item.question) + '</div>';
                        html += '<div class="conversation-answer">';
                        html += '<strong>Answer:</strong><p>' + item.answer.replace(/\\n/g, '<br>') + '</p>';
                        html += '<div class="sources"><strong>📚 Sources:</strong>';
                        if (item.sources && item.sources.length > 0) {
                            html += '<ul>';
                            item.sources.forEach(source => {
                                html += '<li><code>' + escapeHtml(source) + '</code></li>';
                            });
                            html += '</ul>';
                        } else {
                            html += '<p style="color: #95a5a6; font-style: italic;">No specific sources identified.</p>';
                        }
                        html += '</div>';
                        if (item.processing_time) {
                            html += '<div style="margin-top: 10px; font-size: 11px; color: #7f8c8d;">⏱️ ' + item.processing_time + 's</div>';
                        }
                        html += '</div></div>';
                        return html;
                    }).join('');
                } else {
                    historyDiv.style.display = 'none';
                }
            }
            
            function addToHistory(question, answer, sources, processingTime) {
                conversationHistory.push({
                    question, answer, sources: sources || [], processing_time: processingTime,
                    timestamp: new Date().toISOString()
                });
                if (conversationHistory.length > 50) {
                    conversationHistory = conversationHistory.slice(-50);
                }
                localStorage.setItem('flexcube_conversation_history', JSON.stringify(conversationHistory));
                loadConversationHistory();
            }
            
            function clearHistory() {
                if (confirm('Clear all conversation history?')) {
                    conversationHistory = [];
                    localStorage.removeItem('flexcube_conversation_history');
                    loadConversationHistory();
                }
            }
            
            function clearCurrentAnswer() {
                document.getElementById('current-answer').innerHTML = '';
                document.getElementById('question').value = '';
            }
            
            async function askQuestion() {
                const question = document.getElementById('question').value.trim();
                const answerDiv = document.getElementById('current-answer');
                const askBtn = document.getElementById('askBtn');
                if (!question) {
                    answerDiv.innerHTML = '<div class="error">Please enter a question.</div>';
                    return;
                }
                askBtn.disabled = true;
                askBtn.textContent = 'Processing...';
                answerDiv.innerHTML = '<div class="loading">Processing your question</div>';
                try {
                    const response = await fetch('/api/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question })
                    });
                    const data = await response.json();
                    if (response.ok) {
                        let html = '<div class="answer"><strong>Answer:</strong><p>' + data.answer.replace(/\\n/g, '<br>') + '</p>';
                        html += '<div class="sources"><strong>📚 Sources:</strong>';
                        if (data.sources && data.sources.length > 0) {
                            html += '<ul>';
                            data.sources.forEach(source => {
                                html += '<li><code>' + escapeHtml(source) + '</code></li>';
                            });
                            html += '</ul>';
                        } else {
                            html += '<p style="color: #95a5a6; font-style: italic;">No specific sources identified.</p>';
                        }
                        html += '</div></div>';
                        answerDiv.innerHTML = html;
                        addToHistory(question, data.answer, data.sources, data.processing_time);
                        document.getElementById('question').value = '';
                    } else {
                        answerDiv.innerHTML = '<div class="error">Error: ' + (data.detail || 'Unknown error') + '</div>';
                    }
                } catch (error) {
                    answerDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                } finally {
                    askBtn.disabled = false;
                    askBtn.textContent = 'Ask Question';
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function formatBytes(bytes) {
                if (!bytes) return '';
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
            }
            
            document.getElementById('question').addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'Enter') {
                    askQuestion();
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        return HealthResponse(
            status="healthy",
            pipeline_ready=True,
            stats=stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            pipeline_ready=False
        )


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the RAG pipeline with a question.
    
    Args:
        request: Query request with question and optional top_k
        
    Returns:
        QueryResponse: Answer with sources
    """
    import time
    start_time = time.time()
    
    try:
        pipeline = get_pipeline()
        logger.info(f"Processing query: {request.question[:100]}...")
        
        # Query the pipeline - returns (answer, sources) tuple
        answer, sources = pipeline.query(request.question)
        
        # Clean up sources - remove duplicates and format nicely
        unique_sources = []
        seen = set()
        for source in sources:
            # Extract just the filename for display
            if '(' in source and ')' in source:
                # Format: "filename (full_path)"
                display_name = source.split('(')[0].strip()
                full_path = source.split('(')[1].rstrip(')').strip()
            else:
                display_name = source.split('/')[-1] if '/' in source else source
                full_path = source
            
            if display_name and display_name not in seen:
                unique_sources.append({
                    "filename": display_name,
                    "path": full_path
                })
                seen.add(display_name)
        
        processing_time = time.time() - start_time
        
        return QueryResponse(
            answer=answer,
            sources=[s["filename"] for s in unique_sources] if unique_sources else [],
            processing_time=round(processing_time, 2)
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and index a document.
    
    Args:
        file: Document file (PDF, DOCX, or TXT)
        
    Returns:
        dict: Upload and indexing status
    """
    try:
        pipeline = get_pipeline()
        
        # Save uploaded file
        data_dir = "/var/www/chatbot_FC/data/documents"
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = os.path.join(data_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Uploaded file: {file.filename} ({len(content)} bytes)")
        
        # Index the document
        num_chunks = pipeline.index_documents(file_paths=[file_path])
        
        return {
            "status": "success",
            "filename": file.filename,
            "size": len(content),
            "chunks_indexed": num_chunks
        }
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents():
    """List all indexed documents."""
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        
        # Get document list from data directory
        data_dir = "/var/www/chatbot_FC/data/documents"
        documents = []
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                file_path = os.path.join(data_dir, filename)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    documents.append({
                        "filename": filename,
                        "size": size,
                        "path": file_path
                    })
        
        return {
            "documents": documents,
            "total_chunks": stats.get("documents_indexed", 0)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """
    Delete a document from the index and filesystem.
    
    Args:
        filename: Name of the document to delete
        
    Returns:
        dict: Deletion status
    """
    try:
        import urllib.parse
        filename = urllib.parse.unquote(filename)
        
        data_dir = "/var/www/chatbot_FC/data/documents"
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete file from filesystem
        os.remove(file_path)
        logger.info(f"Deleted document: {filename}")
        
        # Note: Document chunks remain in Qdrant. Full reindexing would be needed to remove them.
        # For now, we just delete the file. A reindex endpoint can be used to rebuild the index.
        
        return {
            "status": "success",
            "message": f"Document {filename} deleted. Note: Chunks remain in index. Use reindex to fully remove."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/image", response_model=QueryResponse)
async def query_image(image: UploadFile = File(...)):
    """
    Query the RAG pipeline with an image/screenshot.
    
    This endpoint accepts an image, extracts text/error information using vision model,
    and then queries the RAG pipeline for solutions.
    
    Args:
        image: Image file (screenshot of FlexCube error)
        
    Returns:
        QueryResponse: Answer with sources
    """
    import time
    start_time = time.time()
    
    try:
        # For now, return a placeholder message since vision support isn't implemented yet
        # This will be implemented in Phase 5 with LLaVA integration
        logger.info(f"Image query received: {image.filename} ({image.size} bytes)")
        
        return QueryResponse(
            answer="Image query support is coming soon! This feature will use LLaVA vision model to analyze screenshots and extract error information, then search the documentation for solutions. Currently, please use the text query tab.",
            sources=[],
            processing_time=round(time.time() - start_time, 2)
        )
    except Exception as e:
        logger.error(f"Error processing image query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

