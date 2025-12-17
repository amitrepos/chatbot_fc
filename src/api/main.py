"""
FastAPI Main Application

Main FastAPI application with endpoints for:
- Querying the RAG pipeline
- Document management
- Health checks
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
from loguru import logger
import sys
import os
import json
import csv
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.rag.pipeline import FlexCubeRAGPipeline
from src.database.database import get_db
from src.database.models import (
    User, Permission, UserPermission, RoleTemplate, RoleTemplatePermission,
    Conversation, QAPair, Feedback, TrainingDataExport
)
from src.database.crud import (
    get_user_by_username, get_user_by_email, create_user,
    get_user_permissions, assign_role_template_to_user,
    update_user_last_login,
    create_conversation, get_user_conversations,
    create_qa_pair, get_user,
    get_all_permissions, grant_permission, revoke_permission,
    get_permission_by_name, get_role_template_by_name,
    get_user_qa_pairs, get_qa_pair_feedback
)
from src.auth.password import hash_password, verify_password, validate_password_strength
from src.auth.auth import create_access_token, decode_access_token
from src.auth.dependencies import get_current_user, get_current_user_permissions, require_permission

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
    qa_pair_id: Optional[int] = None  # ID of stored Q&A pair for feedback


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    pipeline_ready: bool
    stats: Optional[dict] = None


# ============================================================================
# Authentication Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class RegisterResponse(BaseModel):
    """User registration response."""
    user_id: int
    username: str
    email: str
    message: str


class LoginRequest(BaseModel):
    """User login request."""
    username: str  # Can be username or email
    password: str


class LoginResponse(BaseModel):
    """User login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict


class UserInfoResponse(BaseModel):
    """Current user info response."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    user_type: str
    permissions: List[str]
    is_active: bool


class FeedbackRequest(BaseModel):
    """Feedback request model."""
    qa_pair_id: int
    rating: int  # 1 = dislike, 2 = like
    feedback_text: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback response model."""
    feedback_id: int
    message: str


class FeedbackDetailResponse(BaseModel):
    """Detailed feedback response model."""
    id: int
    qa_pair_id: int
    user_id: int
    username: str
    rating: int
    feedback_text: Optional[str]
    created_at: datetime


class FeedbackListResponse(BaseModel):
    """List of feedback responses."""
    feedbacks: List[FeedbackDetailResponse]
    total: int


# ============================================================================
# Admin Request/Response Models
# ============================================================================

class AdminCreateUserRequest(BaseModel):
    """Admin create user request."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    user_type: str = "general_user"
    notes: Optional[str] = None


class AdminUpdateUserRequest(BaseModel):
    """Admin update user request."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class UserDetailResponse(BaseModel):
    """User detail response for admin."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    user_type: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    created_by: Optional[int]
    notes: Optional[str]
    permissions: List[str]
    conversation_count: int = 0
    qa_pair_count: int = 0


class UserListResponse(BaseModel):
    """List of users response."""
    users: List[UserDetailResponse]
    total: int


class DashboardStatsResponse(BaseModel):
    """Admin dashboard statistics."""
    total_users: int
    active_users: int
    inactive_users: int
    total_conversations: int
    total_qa_pairs: int
    total_feedback: int
    likes_count: int
    dislikes_count: int
    average_response_time: Optional[float]
    most_active_users: List[dict]
    recent_activity: List[dict]


class AnalyticsResponse(BaseModel):
    """Analytics response."""
    query_analytics: dict
    user_analytics: dict
    feedback_analytics: dict
    time_series_data: List[dict]


class GrantPermissionRequest(BaseModel):
    """Grant permission request."""
    permission_name: str


class AssignTemplateRequest(BaseModel):
    """Assign role template request."""
    template_name: str


class TrainingDataExportRequest(BaseModel):
    """Training data export request."""
    format: str = "json"  # json or csv
    include_feedback: bool = True


# Endpoints

# Favicon endpoint to prevent 404 errors
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return empty response for favicon requests to avoid 404 errors."""
    # SVG favicon as data URI (magnifying glass icon)
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <circle cx="14" cy="14" r="10" fill="none" stroke="#667eea" stroke-width="3"/>
        <line x1="21" y1="21" x2="28" y2="28" stroke="#667eea" stroke-width="3" stroke-linecap="round"/>
    </svg>'''
    return Response(content=svg_icon, media_type="image/svg+xml")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Login and signup page."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Ask-NUO</title>
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
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .auth-container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 450px;
                width: 100%;
                padding: 40px;
            }
            .auth-header {
                text-align: center;
                margin-bottom: 30px;
            }
            .auth-header h1 {
                color: #667eea;
                font-size: 2em;
                margin-bottom: 10px;
            }
            .auth-header p {
                color: #6c757d;
                font-size: 0.95em;
            }
            .auth-tabs {
                display: flex;
                border-bottom: 2px solid #e9ecef;
                margin-bottom: 25px;
            }
            .auth-tab {
                flex: 1;
                padding: 12px;
                background: transparent;
                border: none;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                color: #6c757d;
                border-bottom: 3px solid transparent;
                transition: all 0.3s;
            }
            .auth-tab:hover {
                color: #667eea;
            }
            .auth-tab.active {
                color: #667eea;
                border-bottom-color: #667eea;
            }
            .auth-form {
                display: none;
            }
            .auth-form.active {
                display: block;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                font-weight: 600;
                margin-bottom: 8px;
                color: #495057;
                font-size: 14px;
            }
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            .password-strength {
                margin-top: 8px;
                font-size: 12px;
                height: 20px;
            }
            .password-strength.weak { color: #dc3545; }
            .password-strength.medium { color: #ffc107; }
            .password-strength.strong { color: #28a745; }
            .password-requirements {
                margin-top: 8px;
                font-size: 12px;
                color: #6c757d;
                list-style: none;
                padding-left: 0;
            }
            .password-requirements li {
                margin: 4px 0;
            }
            .password-requirements li.valid {
                color: #28a745;
            }
            .password-requirements li.valid::before {
                content: "✓ ";
            }
            .remember-me {
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }
            .remember-me input {
                margin-right: 8px;
            }
            .remember-me label {
                font-size: 14px;
                color: #495057;
                cursor: pointer;
            }
            .auth-button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .auth-button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            .auth-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .error-message {
                background: #f8d7da;
                color: #721c24;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-size: 14px;
                border-left: 4px solid #dc3545;
                display: none;
            }
            .error-message.show {
                display: block;
            }
            .success-message {
                background: #d4edda;
                color: #155724;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-size: 14px;
                border-left: 4px solid #28a745;
                display: none;
            }
            .success-message.show {
                display: block;
            }
            .loading {
                text-align: center;
                padding: 20px;
                color: #667eea;
            }
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>🔍 Ask-NUO</h1>
                <p>AI Assistant for FlexCube Banking Software</p>
            </div>
            
            <div class="auth-tabs">
                <button class="auth-tab active" onclick="switchAuthTab('login')">Login</button>
                <button class="auth-tab" onclick="switchAuthTab('signup')">Sign Up</button>
            </div>
            
            <div id="error-message" class="error-message"></div>
            <div id="success-message" class="success-message"></div>
            
            <!-- Login Form -->
            <form id="login-form" class="auth-form active" onsubmit="handleLogin(event)">
                <div class="form-group">
                    <label for="login-username">Username or Email</label>
                    <input type="text" id="login-username" name="username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="login-password">Password</label>
                    <input type="password" id="login-password" name="password" required autocomplete="current-password">
                </div>
                <div class="remember-me">
                    <input type="checkbox" id="remember-me" name="remember">
                    <label for="remember-me">Remember me</label>
                </div>
                <button type="submit" class="auth-button" id="login-button">Login</button>
            </form>
            
            <!-- Signup Form -->
            <form id="signup-form" class="auth-form" onsubmit="handleSignup(event)">
                <div class="form-group">
                    <label for="signup-username">Username</label>
                    <input type="text" id="signup-username" name="username" required autocomplete="username" minlength="3">
                </div>
                <div class="form-group">
                    <label for="signup-email">Email</label>
                    <input type="email" id="signup-email" name="email" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label for="signup-fullname">Full Name (Optional)</label>
                    <input type="text" id="signup-fullname" name="full_name" autocomplete="name">
                </div>
                <div class="form-group">
                    <label for="signup-password">Password</label>
                    <input type="password" id="signup-password" name="password" required autocomplete="new-password" oninput="checkPasswordStrength(this.value)">
                    <div id="password-strength" class="password-strength"></div>
                    <ul id="password-requirements" class="password-requirements">
                        <li id="req-length">At least 8 characters</li>
                        <li id="req-upper">One uppercase letter</li>
                        <li id="req-lower">One lowercase letter</li>
                        <li id="req-number">One number</li>
                    </ul>
                </div>
                <div class="form-group">
                    <label for="signup-confirm">Confirm Password</label>
                    <input type="password" id="signup-confirm" name="confirm_password" required autocomplete="new-password" oninput="checkPasswordMatch()">
                    <div id="password-match" style="margin-top: 8px; font-size: 12px; color: #dc3545; display: none;">Passwords do not match</div>
                </div>
                <button type="submit" class="auth-button" id="signup-button">Sign Up</button>
            </form>
        </div>
        
        <script>
            // Tab switching
            function switchAuthTab(tab) {
                document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(tab + '-form').classList.add('active');
                hideMessages();
            }
            
            // Password strength checking
            function checkPasswordStrength(password) {
                const strengthDiv = document.getElementById('password-strength');
                const requirements = {
                    length: password.length >= 8,
                    upper: /[A-Z]/.test(password),
                    lower: /[a-z]/.test(password),
                    number: /[0-9]/.test(password)
                };
                
                // Update requirement indicators
                document.getElementById('req-length').classList.toggle('valid', requirements.length);
                document.getElementById('req-upper').classList.toggle('valid', requirements.upper);
                document.getElementById('req-lower').classList.toggle('valid', requirements.lower);
                document.getElementById('req-number').classList.toggle('valid', requirements.number);
                
                // Calculate strength
                const strength = Object.values(requirements).filter(Boolean).length;
                if (strength === 0) {
                    strengthDiv.textContent = '';
                    strengthDiv.className = 'password-strength';
                } else if (strength <= 2) {
                    strengthDiv.textContent = 'Weak';
                    strengthDiv.className = 'password-strength weak';
                } else if (strength === 3) {
                    strengthDiv.textContent = 'Medium';
                    strengthDiv.className = 'password-strength medium';
                } else {
                    strengthDiv.textContent = 'Strong';
                    strengthDiv.className = 'password-strength strong';
                }
            }
            
            function checkPasswordMatch() {
                const password = document.getElementById('signup-password').value;
                const confirm = document.getElementById('signup-confirm').value;
                const matchDiv = document.getElementById('password-match');
                
                if (confirm && password !== confirm) {
                    matchDiv.style.display = 'block';
                    return false;
                } else {
                    matchDiv.style.display = 'none';
                    return true;
                }
            }
            
            // Message handling
            function showError(message) {
                const errorDiv = document.getElementById('error-message');
                errorDiv.textContent = message;
                errorDiv.classList.add('show');
                document.getElementById('success-message').classList.remove('show');
            }
            
            function showSuccess(message) {
                const successDiv = document.getElementById('success-message');
                successDiv.textContent = message;
                successDiv.classList.add('show');
                document.getElementById('error-message').classList.remove('show');
            }
            
            function hideMessages() {
                document.getElementById('error-message').classList.remove('show');
                document.getElementById('success-message').classList.remove('show');
            }
            
            // Login handler
            async function handleLogin(event) {
                event.preventDefault();
                const button = document.getElementById('login-button');
                button.disabled = true;
                button.textContent = 'Logging in...';
                hideMessages();
                
                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            username: document.getElementById('login-username').value,
                            password: document.getElementById('login-password').value
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        // Store token and user info
                        localStorage.setItem('auth_token', data.access_token);
                        localStorage.setItem('user_info', JSON.stringify(data.user));
                        
                        // Redirect to main app
                        window.location.href = '/';
                    } else {
                        showError(data.detail || 'Login failed');
                    }
                } catch (error) {
                    showError('Error: ' + error.message);
                } finally {
                    button.disabled = false;
                    button.textContent = 'Login';
                }
            }
            
            // Signup handler
            async function handleSignup(event) {
                event.preventDefault();
                
                // Check password match
                if (!checkPasswordMatch()) {
                    showError('Passwords do not match');
                    return;
                }
                
                const button = document.getElementById('signup-button');
                button.disabled = true;
                button.textContent = 'Creating account...';
                hideMessages();
                
                try {
                    const response = await fetch('/api/auth/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            username: document.getElementById('signup-username').value,
                            email: document.getElementById('signup-email').value,
                            password: document.getElementById('signup-password').value,
                            full_name: document.getElementById('signup-fullname').value || null
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showSuccess('Account created successfully! Please login.');
                        setTimeout(() => {
                            switchAuthTab('login');
                            document.querySelector('.auth-tab').click();
                        }, 1500);
                    } else {
                        showError(data.detail || 'Registration failed');
                    }
                } catch (error) {
                    showError('Error: ' + error.message);
                } finally {
                    button.disabled = false;
                    button.textContent = 'Sign Up';
                }
            }
            
            // Check if already logged in
            if (localStorage.getItem('auth_token')) {
                window.location.href = '/';
            }
        </script>
    </body>
    </html>
    """
    return html_content


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
            let currentUser = null;
            let authToken = null;
            
            // Authentication check
            function checkAuth() {
                authToken = localStorage.getItem('auth_token');
                const userInfo = localStorage.getItem('user_info');
                
                if (!authToken || !userInfo) {
                    window.location.href = '/login';
                    return false;
                }
                
                try {
                    currentUser = JSON.parse(userInfo);
                    // If permissions are missing, refresh from API
                    if (!currentUser.permissions || currentUser.permissions.length === 0) {
                        refreshUserInfo();
                    } else {
                        updateUserProfile();
                    }
                    return true;
                } catch (e) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                    return false;
                }
            }
            
            // API request interceptor
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                // Add auth token to all API requests
                if (url.startsWith('/api/')) {
                    if (!options.headers) {
                        options.headers = {};
                    }
                    if (authToken) {
                        options.headers['Authorization'] = `Bearer ${authToken}`;
                    }
                }
                
                return originalFetch(url, options).then(response => {
                    // Handle 401 (unauthorized) - redirect to login
                    if (response.status === 401) {
                        localStorage.removeItem('auth_token');
                        localStorage.removeItem('user_info');
                        window.location.href = '/login';
                    }
                    return response;
                });
            };
            
            // Update user profile display
            function updateUserProfile() {
                if (!currentUser) return;
                
                // Add user profile to header if not exists
                let profileDiv = document.getElementById('user-profile');
                if (!profileDiv) {
                    const header = document.querySelector('.header');
                    profileDiv = document.createElement('div');
                    profileDiv.id = 'user-profile';
                    profileDiv.style.cssText = 'position: absolute; top: 20px; right: 20px; display: flex; align-items: center; gap: 15px;';
                    header.style.position = 'relative';
                    header.appendChild(profileDiv);
                }
                
                // Check if user has admin permissions
                const isAdmin = currentUser.user_type === 'operational_admin' || 
                               (currentUser.permissions && currentUser.permissions.includes('view_admin_dashboard'));
                
                profileDiv.innerHTML = `
                    <div style="text-align: right; color: white;">
                        <div style="font-weight: 600;">${escapeHtml(currentUser.username)}</div>
                        <div style="font-size: 0.85em; opacity: 0.9;">${currentUser.user_type === 'operational_admin' ? '👑 Admin' : '👤 User'}</div>
                    </div>
                    ${isAdmin ? `<a href="/admin/dashboard" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; text-decoration: none;">👑 Admin</a>` : ''}
                    <button onclick="logout()" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px;">Logout</button>
                `;
            }
            
            // Logout function
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    fetch('/api/auth/logout', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    }).finally(() => {
                        localStorage.removeItem('auth_token');
                        localStorage.removeItem('user_info');
                        window.location.href = '/login';
                    });
                }
            }
            
            // Permission checking utility
            function hasPermission(permission) {
                if (!currentUser) return false;
                // Check user type first
                if (currentUser.user_type === 'operational_admin') return true;
                // Then check permissions array
                return currentUser.permissions && currentUser.permissions.includes(permission);
            }
            
            // Refresh user info from API to ensure permissions are up to date
            async function refreshUserInfo() {
                try {
                    const response = await fetch('/api/auth/me', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (response.ok) {
                        const userData = await response.json();
                        currentUser = {
                            id: userData.id,
                            username: userData.username,
                            email: userData.email,
                            full_name: userData.full_name,
                            user_type: userData.user_type,
                            permissions: userData.permissions || []
                        };
                        localStorage.setItem('user_info', JSON.stringify(currentUser));
                        updateUserProfile();
                    }
                } catch (error) {
                    console.error('Error refreshing user info:', error);
                }
            }
            
            // Navigate to admin dashboard
            function navigateToAdmin() {
                // Simply navigate to the admin dashboard
                // The cookie-based auth will handle authentication
                window.location.href = '/admin/dashboard';
            }
            
            // Utility function for escaping HTML
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Initialize
            window.addEventListener('DOMContentLoaded', function() {
                if (!checkAuth()) return;
                
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
                answerDiv.innerHTML = '<div class="loading">Analyzing image and searching for solutions... This may take 30-120 seconds</div>';
                
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
                        html += '</div>';
                        
                        // Add feedback buttons if qa_pair_id is available
                        if (data.qa_pair_id) {
                            html += '<div class="feedback-section" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e9ecef;">';
                            html += '<div style="display: flex; align-items: center; gap: 10px;">';
                            html += '<span style="font-weight: 600; color: #495057;">Was this helpful?</span>';
                            html += '<button onclick="submitFeedback(' + data.qa_pair_id + ', 2)" class="feedback-btn like-btn" id="like-btn-' + data.qa_pair_id + '" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px;">👍 Like</button>';
                            html += '<button onclick="submitFeedback(' + data.qa_pair_id + ', 1)" class="feedback-btn dislike-btn" id="dislike-btn-' + data.qa_pair_id + '" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px;">👎 Dislike</button>';
                            html += '</div>';
                            html += '<div id="feedback-comment-' + data.qa_pair_id + '" style="margin-top: 10px; display: none;">';
                            html += '<textarea id="comment-text-' + data.qa_pair_id + '" placeholder="Optional: Add a comment..." style="width: 100%; padding: 8px; border: 1px solid #e9ecef; border-radius: 6px; font-size: 14px; min-height: 60px;"></textarea>';
                            html += '<button onclick="submitFeedbackWithComment(' + data.qa_pair_id + ')" style="margin-top: 8px; background: #667eea; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">Submit Comment</button>';
                            html += '</div>';
                            html += '</div>';
                        }
                        
                        html += '</div>';
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
            async function loadConversationHistory() {
                const historyDiv = document.getElementById('conversation-history');
                const historyItems = document.getElementById('history-items');
                
                // Show loading state
                historyItems.innerHTML = '<p style="color: #6c757d; text-align: center; padding: 20px;">Loading conversation history...</p>';
                
                try {
                    // Fetch user-specific conversation history from API
                    const response = await fetch('/api/conversations/history', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    
                    if (response.status === 401) {
                        // Not authenticated - clear and redirect
                        localStorage.removeItem('auth_token');
                        localStorage.removeItem('user_info');
                        window.location.href = '/login';
                        return;
                    }
                    
                    if (!response.ok) {
                        throw new Error('Failed to load conversation history');
                    }
                    
                    const data = await response.json();
                    const history = data.history || [];
                    
                    if (history.length > 0) {
                        historyDiv.style.display = 'block';
                        historyItems.innerHTML = history.map(item => {
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
                        historyItems.innerHTML = '<p style="color: #6c757d; text-align: center; padding: 20px;">No conversation history yet.</p>';
                    }
                } catch (error) {
                    console.error('Error loading conversation history:', error);
                    historyItems.innerHTML = '<p style="color: #dc3545; text-align: center; padding: 20px;">Error loading conversation history.</p>';
                }
            }
            
            function addToHistory(question, answer, sources, processingTime, qaPairId) {
                // Q&A pairs are already stored in database via the API
                // Just reload the history from the API to get the latest
                // This ensures we're showing user-specific data
                loadConversationHistory();
            }
            
            function clearHistory() {
                if (confirm('Clear all conversation history? This will only clear the display - your data in the database will remain.')) {
                    // Clear localStorage cache
                    localStorage.removeItem('flexcube_conversation_history');
                    // Reload from API (which will show empty if no data)
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
                answerDiv.innerHTML = '<div class="loading">Processing your question... This may take 20-90 seconds</div>';
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
                        html += '</div>';
                        
                        // Add feedback buttons if qa_pair_id is available
                        if (data.qa_pair_id) {
                            html += '<div class="feedback-section" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e9ecef;">';
                            html += '<div style="display: flex; align-items: center; gap: 10px;">';
                            html += '<span style="font-weight: 600; color: #495057;">Was this helpful?</span>';
                            html += '<button onclick="submitFeedback(' + data.qa_pair_id + ', 2)" class="feedback-btn like-btn" id="like-btn-' + data.qa_pair_id + '" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px;">👍 Like</button>';
                            html += '<button onclick="submitFeedback(' + data.qa_pair_id + ', 1)" class="feedback-btn dislike-btn" id="dislike-btn-' + data.qa_pair_id + '" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px;">👎 Dislike</button>';
                            html += '</div>';
                            html += '<div id="feedback-comment-' + data.qa_pair_id + '" style="margin-top: 10px; display: none;">';
                            html += '<textarea id="comment-text-' + data.qa_pair_id + '" placeholder="Optional: Add a comment..." style="width: 100%; padding: 8px; border: 1px solid #e9ecef; border-radius: 6px; font-size: 14px; min-height: 60px;"></textarea>';
                            html += '<button onclick="submitFeedbackWithComment(' + data.qa_pair_id + ')" style="margin-top: 8px; background: #667eea; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">Submit Comment</button>';
                            html += '</div>';
                            html += '</div>';
                        }
                        
                        html += '</div>';
                        answerDiv.innerHTML = html;
                        addToHistory(question, data.answer, data.sources, data.processing_time, data.qa_pair_id);
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
            
            // Feedback functions
            async function submitFeedback(qaPairId, rating) {
                try {
                    const response = await fetch('/api/feedback', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            qa_pair_id: qaPairId,
                            rating: rating
                        })
                    });
                    
                    if (response.ok) {
                        // Update button styles to show selected state
                        const likeBtn = document.getElementById('like-btn-' + qaPairId);
                        const dislikeBtn = document.getElementById('dislike-btn-' + qaPairId);
                        
                        if (rating === 2) {
                            likeBtn.style.background = '#155724';
                            likeBtn.style.opacity = '0.8';
                            dislikeBtn.style.background = '#dc3545';
                            dislikeBtn.style.opacity = '1';
                            // Show comment section
                            document.getElementById('feedback-comment-' + qaPairId).style.display = 'block';
                        } else {
                            dislikeBtn.style.background = '#721c24';
                            dislikeBtn.style.opacity = '0.8';
                            likeBtn.style.background = '#28a745';
                            likeBtn.style.opacity = '1';
                            // Show comment section
                            document.getElementById('feedback-comment-' + qaPairId).style.display = 'block';
                        }
                    } else {
                        const data = await response.json();
                        alert('Error submitting feedback: ' + (data.detail || 'Unknown error'));
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            async function submitFeedbackWithComment(qaPairId) {
                const comment = document.getElementById('comment-text-' + qaPairId).value;
                const likeBtn = document.getElementById('like-btn-' + qaPairId);
                const dislikeBtn = document.getElementById('dislike-btn-' + qaPairId);
                
                // Determine rating from button states
                let rating = 2; // Default to like
                if (dislikeBtn.style.opacity === '0.8') {
                    rating = 1; // Dislike
                }
                
                try {
                    const response = await fetch('/api/feedback', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            qa_pair_id: qaPairId,
                            rating: rating,
                            feedback_text: comment || null
                        })
                    });
                    
                    if (response.ok) {
                        document.getElementById('comment-text-' + qaPairId).value = '';
                        document.getElementById('feedback-comment-' + qaPairId).style.display = 'none';
                        alert('Thank you for your feedback!');
                    } else {
                        const data = await response.json();
                        alert('Error submitting feedback: ' + (data.detail || 'Unknown error'));
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
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
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_chat")),
    db: Session = Depends(get_db)
):
    """
    Query the RAG pipeline with a question.
    
    Requires authentication and 'view_chat' permission.
    Stores Q&A pair in database and links to conversation.
    
    Args:
        request: Query request with question and optional top_k
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        QueryResponse: Answer with sources
    """
    import time
    start_time = time.time()
    
    try:
        pipeline = get_pipeline()
        logger.info(f"User {current_user.username} querying: {request.question[:100]}...")
        
        # Query the pipeline - returns (answer, sources) tuple
        answer, sources = pipeline.query(request.question)
        
        # Clean up sources - remove duplicates and format nicely
        unique_sources = []
        seen = set()
        source_filenames = []
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
                source_filenames.append(display_name)
                seen.add(display_name)
        
        processing_time = time.time() - start_time
        
        # Determine answer source type
        answer_source_type = "rag" if source_filenames else "general_knowledge"
        
        # Get or create conversation for user
        conversation = create_conversation(
            db=db,
            user_id=current_user.id,
            title=request.question[:50] + "..." if len(request.question) > 50 else request.question
        )
        
        # Store Q&A pair in database
        qa_pair = create_qa_pair(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation.id,
            question=request.question,
            answer=answer,
            question_type="text",
            sources=source_filenames if source_filenames else None,
            answer_source_type=answer_source_type,
            query_expansion=None,  # Placeholder for future enhancement
            processing_time_seconds=round(processing_time, 2)
        )
        
        logger.info(f"Stored Q&A pair {qa_pair.id} for user {current_user.username}")
        
        return QueryResponse(
            answer=answer,
            sources=source_filenames if source_filenames else [],
            processing_time=round(processing_time, 2),
            qa_pair_id=qa_pair.id
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


@app.get("/api/conversations/history")
async def get_user_conversation_history(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_chat")),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get user's conversation history (Q&A pairs).
    
    Returns user-specific Q&A pairs ordered by most recent first.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Maximum number of Q&A pairs to return
        
    Returns:
        List of Q&A pairs with question, answer, sources, and metadata
    """
    from src.database.crud import get_user_qa_pairs
    
    # Get user's Q&A pairs from database
    qa_pairs = get_user_qa_pairs(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=0
    )
    
    # Format response
    history = []
    for qa in qa_pairs:
        history.append({
            "id": qa.id,
            "question": qa.question,
            "answer": qa.answer,
            "sources": qa.sources if qa.sources else [],
            "processing_time": qa.processing_time_seconds,
            "qa_pair_id": qa.id,
            "timestamp": qa.created_at.isoformat() if qa.created_at else None,
            "conversation_id": qa.conversation_id
        })
    
    return {
        "history": history,
        "total": len(history)
    }


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
async def query_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_image_query")),
    db: Session = Depends(get_db)
):
    """
    Query the RAG pipeline with an image/screenshot.
    
    Requires authentication and 'view_image_query' permission.
    Uses LLaVA vision model to analyze screenshot and extract error information,
    then queries the RAG pipeline for solutions.
    Stores Q&A pair in database.
    
    Args:
        image: Image file (screenshot of FlexCube error)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        QueryResponse: Answer with sources
    """
    import time
    start_time = time.time()
    
    try:
        from src.rag.vision import FlexCubeVision
        
        logger.info(f"User {current_user.username} querying with image: {image.filename} ({image.size} bytes)")
        
        # Read image data
        image_data = await image.read()
        
        # Initialize vision module and analyze screenshot
        vision = FlexCubeVision()
        extraction = vision.analyze_screenshot(image_data)
        
        # Generate query from extracted information
        suggested_query = extraction.get("suggested_query", "")
        if not suggested_query:
            # Fallback: use error message or description
            suggested_query = extraction.get("error_message") or extraction.get("description", "FlexCube error")
        
        # Query RAG pipeline with extracted information
        pipeline = get_pipeline()
        answer, sources = pipeline.query(suggested_query)
        
        # Clean up sources
        unique_sources = []
        seen = set()
        source_filenames = []
        for source in sources:
            if '(' in source and ')' in source:
                display_name = source.split('(')[0].strip()
            else:
                display_name = source.split('/')[-1] if '/' in source else source
            
            if display_name and display_name not in seen:
                unique_sources.append({"filename": display_name})
                source_filenames.append(display_name)
                seen.add(display_name)
        
        processing_time = time.time() - start_time
        answer_source_type = "vision" if source_filenames else "general_knowledge"
        
        # Save image temporarily for storage reference
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{image.filename}") as tmp_file:
            tmp_file.write(image_data)
            image_path = tmp_file.name
        
        # Create conversation
        conversation = create_conversation(
            db=db,
            user_id=current_user.id,
            title=f"Image Query: {extraction.get('screen_name', 'Screenshot')}"
        )
        
        # Store Q&A pair
        qa_pair = create_qa_pair(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation.id,
            question=f"Image: {suggested_query}",
            answer=answer,
            question_type="image",
            image_path=image_path,
            sources=source_filenames if source_filenames else None,
            answer_source_type=answer_source_type,
            query_expansion={"extraction": extraction},
            processing_time_seconds=round(processing_time, 2)
        )
        
        logger.info(f"Stored image Q&A pair {qa_pair.id} for user {current_user.username}")
        
        return QueryResponse(
            answer=answer,
            sources=source_filenames if source_filenames else [],
            processing_time=round(processing_time, 2),
            qa_pair_id=qa_pair.id
        )
    except Exception as e:
        logger.error(f"Error processing image query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Args:
        request: Registration data (username, email, password, full_name)
        db: Database session
        
    Returns:
        RegisterResponse: User ID and confirmation message
        
    Raises:
        HTTPException: 400 if username/email already exists or password is weak
    """
    # Check if username already exists
    if get_user_by_username(db, request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    is_valid, error_message = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {error_message}"
        )
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Create user
    user = create_user(
        db=db,
        username=request.username,
        email=request.email,
        password_hash=password_hash,
        full_name=request.full_name,
        user_type="general_user"  # Default user type
    )
    
    # Assign general_user role template (grants default permissions)
    assign_role_template_to_user(db, user.id, "general_user")
    
    logger.info(f"New user registered: {user.username} (ID: {user.id})")
    
    return RegisterResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        message="User created successfully"
    )


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT token.
    
    Args:
        request: Login credentials (username/email, password)
        db: Database session
        
    Returns:
        LoginResponse: JWT token and user information
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Try to find user by username or email
    user = get_user_by_username(db, request.username)
    if not user:
        user = get_user_by_email(db, request.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Get user permissions (returns list of permission name strings)
    permission_names = get_user_permissions(db, user.id)
    
    # Create access token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "user_type": user.user_type,
        "permissions": permission_names
    }
    access_token = create_access_token(data=token_data)
    
    # Update last login
    update_user_last_login(db, user.id)
    
    logger.info(f"User {user.username} logged in successfully")
    
    # Create response
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 86400,  # 24 hours
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "permissions": permission_names
            }
        }
    )
    
    # Set HTTP-only cookie for HTML page authentication
    response.set_cookie(
        key="auth_token",
        value=access_token,
        max_age=86400,  # 24 hours
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return response


@app.post("/api/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user (invalidate token on client side).
    
    Note: JWT tokens are stateless, so actual invalidation requires
    client-side token removal. For full invalidation, implement token blacklist.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Logout confirmation message
    """
    logger.info(f"User {current_user.username} logged out")
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserInfoResponse: User information with permissions
    """
    # get_user_permissions returns list of permission name strings
    permission_names = get_user_permissions(db, current_user.id)
    
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        user_type=current_user.user_type,
        permissions=permission_names,
        is_active=current_user.is_active
    )


@app.post("/api/auth/refresh", response_model=LoginResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh JWT token.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        LoginResponse: New JWT token and user information
    """
    # Get user permissions (returns list of permission name strings)
    permission_names = get_user_permissions(db, current_user.id)
    
    # Create new access token
    token_data = {
        "sub": str(current_user.id),
        "username": current_user.username,
        "user_type": current_user.user_type,
        "permissions": permission_names
    }
    access_token = create_access_token(data=token_data)
    
    # Create response with login data
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,  # 24 hours
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "user_type": current_user.user_type,
            "permissions": permission_names
        }
    }
    
    # Create JSONResponse to set cookie
    response = JSONResponse(content=response_data)
    
    # Set HTTP-only cookie for HTML page authentication
    response.set_cookie(
        key="auth_token",
        value=access_token,
        max_age=86400,  # 24 hours
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return response


# ============================================================================
# Admin UI Pages
# ============================================================================

def get_authenticated_admin_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
    required_permission: Optional[str] = None
) -> Optional[User]:
    """
    Helper function to get authenticated admin user for HTML pages.
    
    Checks both Authorization header (for API) and cookie (for HTML pages).
    Returns None if not authenticated or lacks permission.
    This allows HTML pages to redirect to login instead of returning 404.
    """
    token = None
    
    # First check Authorization header (for API calls)
    if credentials:
        token = credentials.credentials
    else:
        # Check cookie (for HTML page navigation)
        token = request.cookies.get("auth_token")
    
    if not token:
        return None
    
    # Create temporary credentials object for get_current_user
    from fastapi.security import HTTPAuthorizationCredentials
    
    try:
        # Use the token to authenticate
        temp_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        current_user = get_current_user(temp_credentials, db)
    except HTTPException:
        return None
    
    # Check permission if required
    if required_permission:
        from src.database.crud import get_user_permissions
        from src.auth.permissions import has_permission
        
        permission_names = get_user_permissions(db, current_user.id)
        if not has_permission(permission_names, required_permission) and current_user.user_type != "operational_admin":
            return None
    
    return current_user

def get_admin_dashboard_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for admin dashboard page."""
    return get_authenticated_admin_user(request, credentials, db, "view_admin_dashboard")


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(
    current_user: Optional[User] = Depends(get_admin_dashboard_user)
):
    """
    Admin dashboard page.
    
    Shows system statistics, recent activity, and quick actions.
    Redirects to login if not authenticated or lacks permission.
    """
    if not current_user:
        return HTMLResponse(
            content='<script>window.location.href="/login";</script>',
            status_code=200
        )
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Dashboard - Ask-NUO</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
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
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 2em; margin: 0; }
            .nav-links { display: flex; gap: 15px; }
            .nav-links a {
                color: white;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 6px;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s;
            }
            .nav-links a:hover { background: rgba(255,255,255,0.3); }
            .content { padding: 30px; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .stat-card h3 {
                color: #6c757d;
                font-size: 0.9em;
                margin-bottom: 10px;
            }
            .stat-card .value {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .section {
                margin-bottom: 30px;
            }
            .section h2 {
                margin-bottom: 15px;
                color: #495057;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }
            table th, table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }
            table th {
                background: #f8f9fa;
                font-weight: 600;
                color: #495057;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                text-decoration: none;
                display: inline-block;
            }
            .btn-primary {
                background: #667eea;
                color: white;
            }
            .btn-primary:hover { background: #5568d3; }
            .loading { text-align: center; padding: 40px; color: #6c757d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>👑 Admin Dashboard</h1>
                    <p style="margin-top: 5px; opacity: 0.9;">System Overview & Statistics</p>
                </div>
                <div class="nav-links">
                    <a href="/">🏠 Home</a>
                    <a href="/admin/users">👥 Users</a>
                    <a href="/admin/analytics">📊 Analytics</a>
                    <a href="/admin/training-data">📥 Export</a>
                    <a href="/admin/settings">⚙️ Settings</a>
                    <a href="#" onclick="logout(); return false;">🚪 Logout</a>
                </div>
            </div>
            <div class="content">
                <div class="stats-grid" id="statsGrid">
                    <div class="loading">Loading statistics...</div>
                </div>
                <div class="section">
                    <h2>📈 Most Active Users</h2>
                    <div id="activeUsers" class="loading">Loading...</div>
                </div>
                <div class="section">
                    <h2>🕐 Recent Activity</h2>
                    <div id="recentActivity" class="loading">Loading...</div>
                </div>
            </div>
        </div>
        <script>
            let authToken = localStorage.getItem('auth_token');
            if (!authToken) {
                window.location.href = '/login';
            }
            
            async function loadDashboard() {
                try {
                    const response = await fetch('/api/admin/dashboard', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    if (!response.ok) throw new Error('Failed to load dashboard');
                    const data = await response.json();
                    
                    // Render stats
                    document.getElementById('statsGrid').innerHTML = `
                        <div class="stat-card">
                            <h3>Total Users</h3>
                            <div class="value">${data.total_users}</div>
                            <div style="margin-top: 5px; font-size: 0.85em; color: #6c757d;">
                                ${data.active_users} active, ${data.inactive_users} inactive
                            </div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Conversations</h3>
                            <div class="value">${data.total_conversations}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Q&A Pairs</h3>
                            <div class="value">${data.total_qa_pairs}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Feedback</h3>
                            <div class="value">${data.total_feedback}</div>
                            <div style="margin-top: 5px; font-size: 0.85em; color: #6c757d;">
                                👍 ${data.likes_count} likes, 👎 ${data.dislikes_count} dislikes
                            </div>
                        </div>
                        <div class="stat-card">
                            <h3>Avg Response Time</h3>
                            <div class="value">${data.average_response_time ? data.average_response_time.toFixed(2) + 's' : 'N/A'}</div>
                        </div>
                    `;
                    
                    // Render active users
                    if (data.most_active_users && data.most_active_users.length > 0) {
                        document.getElementById('activeUsers').innerHTML = `
                            <table>
                                <thead>
                                    <tr>
                                        <th>Username</th>
                                        <th>Conversations</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.most_active_users.map(u => `
                                        <tr>
                                            <td>${escapeHtml(u.username)}</td>
                                            <td>${u.conversation_count}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                    } else {
                        document.getElementById('activeUsers').innerHTML = '<p style="color: #6c757d;">No active users yet.</p>';
                    }
                    
                    // Render recent activity
                    if (data.recent_activity && data.recent_activity.length > 0) {
                        document.getElementById('recentActivity').innerHTML = `
                            <table>
                                <thead>
                                    <tr>
                                        <th>User</th>
                                        <th>Question</th>
                                        <th>Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.recent_activity.map(a => `
                                        <tr>
                                            <td>${escapeHtml(a.username)}</td>
                                            <td>${escapeHtml(a.question)}</td>
                                            <td>${new Date(a.created_at).toLocaleString()}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                    } else {
                        document.getElementById('recentActivity').innerHTML = '<p style="color: #6c757d;">No recent activity.</p>';
                    }
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                    document.getElementById('statsGrid').innerHTML = '<div class="loading" style="color: #dc3545;">Error loading dashboard data.</div>';
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                }
            }
            
            loadDashboard();
        </script>
    </body>
    </html>
    """
    return html_content


def get_admin_users_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for admin users page."""
    return get_authenticated_admin_user(request, credentials, db, "view_user_management")


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    current_user: Optional[User] = Depends(get_admin_users_user)
):
    """
    User management page.
    
    Allows admins to view, create, edit, and manage users.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>User Management - Ask-NUO</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
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
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 2em; margin: 0; }
            .nav-links { display: flex; gap: 15px; flex-wrap: wrap; }
            .nav-links a {
                color: white;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 6px;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s;
            }
            .nav-links a:hover { background: rgba(255,255,255,0.3); }
            .content { padding: 30px; }
            .filters {
                display: flex;
                gap: 15px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .filters input, .filters select {
                padding: 10px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 14px;
            }
            .filters input:focus, .filters select:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                text-decoration: none;
                display: inline-block;
            }
            .btn-primary { background: #667eea; color: white; }
            .btn-primary:hover { background: #5568d3; }
            .btn-success { background: #28a745; color: white; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }
            table th, table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }
            table th {
                background: #f8f9fa;
                font-weight: 600;
                color: #495057;
            }
            .badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: 600;
            }
            .badge-success { background: #d4edda; color: #155724; }
            .badge-danger { background: #f8d7da; color: #721c24; }
            .badge-info { background: #d1ecf1; color: #0c5460; }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
            }
            .modal-content {
                background: white;
                margin: 50px auto;
                padding: 30px;
                border-radius: 12px;
                max-width: 600px;
                max-height: 90vh;
                overflow-y: auto;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #495057;
            }
            .form-group input, .form-group select, .form-group textarea {
                width: 100%;
                padding: 10px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 14px;
            }
            .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            .loading { text-align: center; padding: 40px; color: #6c757d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>👥 User Management</h1>
                    <p style="margin-top: 5px; opacity: 0.9;">Manage users, permissions, and roles</p>
                </div>
                <div class="nav-links">
                    <a href="/">🏠 Home</a>
                    <a href="/admin/dashboard">📊 Dashboard</a>
                    <a href="/admin/analytics">📈 Analytics</a>
                    <a href="/admin/training-data">📥 Export</a>
                    <a href="/admin/settings">⚙️ Settings</a>
                    <a href="#" onclick="logout(); return false;">🚪 Logout</a>
                </div>
            </div>
            <div class="content">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Users</h2>
                    <button class="btn btn-success" onclick="showCreateUserModal()">+ Create User</button>
                </div>
                <div class="filters">
                    <input type="text" id="searchInput" placeholder="Search username or email..." style="flex: 1; min-width: 200px;">
                    <select id="userTypeFilter">
                        <option value="">All User Types</option>
                        <option value="operational_admin">Admin</option>
                        <option value="general_user">General User</option>
                    </select>
                    <select id="activeFilter">
                        <option value="">All Status</option>
                        <option value="true">Active</option>
                        <option value="false">Inactive</option>
                    </select>
                    <button class="btn btn-primary" onclick="loadUsers()">🔍 Filter</button>
                </div>
                <div id="usersTable" class="loading">Loading users...</div>
            </div>
        </div>
        
        <!-- Create/Edit User Modal -->
        <div id="userModal" class="modal">
            <div class="modal-content">
                <h2 id="modalTitle">Create User</h2>
                <form id="userForm" onsubmit="saveUser(event); return false;">
                    <input type="hidden" id="userId">
                    <div class="form-group">
                        <label>Username *</label>
                        <input type="text" id="username" required>
                    </div>
                    <div class="form-group">
                        <label>Email *</label>
                        <input type="email" id="email" required>
                    </div>
                    <div class="form-group" id="passwordGroup">
                        <label>Password *</label>
                        <input type="password" id="password" required>
                    </div>
                    <div class="form-group">
                        <label>Full Name</label>
                        <input type="text" id="fullName">
                    </div>
                    <div class="form-group">
                        <label>User Type *</label>
                        <select id="userType" required>
                            <option value="general_user">General User</option>
                            <option value="operational_admin">Operational Admin</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Notes</label>
                        <textarea id="notes" rows="3"></textarea>
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: flex-end;">
                        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">Save</button>
                    </div>
                </form>
            </div>
        </div>
        
        <script>
            let authToken = localStorage.getItem('auth_token');
            if (!authToken) {
                window.location.href = '/login';
            }
            
            async function loadUsers() {
                const search = document.getElementById('searchInput').value;
                const userType = document.getElementById('userTypeFilter').value;
                const isActive = document.getElementById('activeFilter').value;
                
                let url = '/api/admin/users?limit=100';
                if (search) url += `&search=${encodeURIComponent(search)}`;
                if (userType) url += `&user_type=${encodeURIComponent(userType)}`;
                if (isActive) url += `&is_active=${isActive === 'true'}`;
                
                try {
                    const response = await fetch(url, {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    if (!response.ok) throw new Error('Failed to load users');
                    const data = await response.json();
                    
                    if (data.users && data.users.length > 0) {
                        document.getElementById('usersTable').innerHTML = `
                            <table>
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Username</th>
                                        <th>Email</th>
                                        <th>Type</th>
                                        <th>Status</th>
                                        <th>Conversations</th>
                                        <th>Q&A Pairs</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.users.map(u => `
                                        <tr>
                                            <td>${u.id}</td>
                                            <td>${escapeHtml(u.username)}</td>
                                            <td>${escapeHtml(u.email)}</td>
                                            <td><span class="badge badge-info">${u.user_type}</span></td>
                                            <td><span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
                                            <td>${u.conversation_count}</td>
                                            <td>${u.qa_pair_count}</td>
                                            <td>
                                                <button class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;" onclick="editUser(${u.id})">Edit</button>
                                                ${u.is_active ? `<button class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="deactivateUser(${u.id})">Deactivate</button>` : ''}
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                            <p style="margin-top: 15px; color: #6c757d;">Total: ${data.total} users</p>
                        `;
                    } else {
                        document.getElementById('usersTable').innerHTML = '<p style="color: #6c757d; text-align: center; padding: 40px;">No users found.</p>';
                    }
                } catch (error) {
                    console.error('Error loading users:', error);
                    document.getElementById('usersTable').innerHTML = '<div class="loading" style="color: #dc3545;">Error loading users.</div>';
                }
            }
            
            function showCreateUserModal() {
                document.getElementById('modalTitle').textContent = 'Create User';
                document.getElementById('userForm').reset();
                document.getElementById('userId').value = '';
                document.getElementById('passwordGroup').style.display = 'block';
                document.getElementById('password').required = true;
                document.getElementById('userModal').style.display = 'block';
            }
            
            async function editUser(userId) {
                try {
                    const response = await fetch(`/api/admin/users/${userId}`, {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (!response.ok) throw new Error('Failed to load user');
                    const user = await response.json();
                    
                    document.getElementById('modalTitle').textContent = 'Edit User';
                    document.getElementById('userId').value = user.id;
                    document.getElementById('username').value = user.username;
                    document.getElementById('email').value = user.email;
                    document.getElementById('fullName').value = user.full_name || '';
                    document.getElementById('userType').value = user.user_type;
                    document.getElementById('notes').value = user.notes || '';
                    document.getElementById('passwordGroup').style.display = 'none';
                    document.getElementById('password').required = false;
                    document.getElementById('userModal').style.display = 'block';
                } catch (error) {
                    alert('Error loading user: ' + error.message);
                }
            }
            
            async function saveUser(event) {
                event.preventDefault();
                const userId = document.getElementById('userId').value;
                const data = {
                    username: document.getElementById('username').value,
                    email: document.getElementById('email').value,
                    full_name: document.getElementById('fullName').value || null,
                    user_type: document.getElementById('userType').value,
                    notes: document.getElementById('notes').value || null
                };
                
                if (!userId) {
                    // Create user
                    data.password = document.getElementById('password').value;
                    try {
                        const response = await fetch('/api/admin/users', {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${authToken}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(data)
                        });
                        if (!response.ok) {
                            const error = await response.json();
                            throw new Error(error.detail || 'Failed to create user');
                        }
                        alert('User created successfully!');
                        closeModal();
                        loadUsers();
                    } catch (error) {
                        alert('Error: ' + error.message);
                    }
                } else {
                    // Update user
                    try {
                        const response = await fetch(`/api/admin/users/${userId}`, {
                            method: 'PUT',
                            headers: {
                                'Authorization': `Bearer ${authToken}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(data)
                        });
                        if (!response.ok) {
                            const error = await response.json();
                            throw new Error(error.detail || 'Failed to update user');
                        }
                        alert('User updated successfully!');
                        closeModal();
                        loadUsers();
                    } catch (error) {
                        alert('Error: ' + error.message);
                    }
                }
            }
            
            async function deactivateUser(userId) {
                if (!confirm('Are you sure you want to deactivate this user?')) return;
                try {
                    const response = await fetch(`/api/admin/users/${userId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (!response.ok) throw new Error('Failed to deactivate user');
                    alert('User deactivated successfully!');
                    loadUsers();
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            function closeModal() {
                document.getElementById('userModal').style.display = 'none';
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                }
            }
            
            // Close modal on outside click
            window.onclick = function(event) {
                const modal = document.getElementById('userModal');
                if (event.target === modal) {
                    closeModal();
                }
            }
            
            loadUsers();
        </script>
    </body>
    </html>
    """
    return html_content


def get_admin_analytics_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for admin analytics page."""
    return get_authenticated_admin_user(request, credentials, db, "view_analytics")


@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics_page(
    current_user: Optional[User] = Depends(get_admin_analytics_user)
):
    """
    Analytics page.
    
    Shows system analytics, query statistics, and user analytics.
    Redirects to login if not authenticated or lacks permission.
    """
    if not current_user:
        return HTMLResponse(
            content='<script>window.location.href="/login";</script>',
            status_code=200
        )
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analytics - Ask-NUO</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
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
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 2em; margin: 0; }
            .nav-links { display: flex; gap: 15px; flex-wrap: wrap; }
            .nav-links a {
                color: white;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 6px;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s;
            }
            .nav-links a:hover { background: rgba(255,255,255,0.3); }
            .content { padding: 30px; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .stat-card h3 {
                color: #6c757d;
                font-size: 0.9em;
                margin-bottom: 10px;
            }
            .stat-card .value {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .section {
                margin-bottom: 30px;
            }
            .section h2 {
                margin-bottom: 15px;
                color: #495057;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }
            table th, table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }
            table th {
                background: #f8f9fa;
                font-weight: 600;
                color: #495057;
            }
            .loading { text-align: center; padding: 40px; color: #6c757d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>📊 Analytics & Reports</h1>
                    <p style="margin-top: 5px; opacity: 0.9;">System Analytics and Statistics</p>
                </div>
                <div class="nav-links">
                    <a href="/">🏠 Home</a>
                    <a href="/admin/dashboard">📈 Dashboard</a>
                    <a href="/admin/users">👥 Users</a>
                    <a href="/admin/training-data">📥 Export</a>
                    <a href="/admin/settings">⚙️ Settings</a>
                    <a href="#" onclick="logout(); return false;">🚪 Logout</a>
                </div>
            </div>
            <div class="content">
                <div class="section">
                    <h2>📈 Query Analytics</h2>
                    <div id="queryStats" class="loading">Loading...</div>
                </div>
                <div class="section">
                    <h2>👥 User Analytics</h2>
                    <div id="userStats" class="loading">Loading...</div>
                </div>
                <div class="section">
                    <h2>💬 Feedback Analytics</h2>
                    <div id="feedbackStats" class="loading">Loading...</div>
                </div>
            </div>
        </div>
        <script>
            let authToken = localStorage.getItem('auth_token');
            if (!authToken) {
                window.location.href = '/login';
            }
            
            async function loadAnalytics() {
                try {
                    const response = await fetch('/api/admin/analytics', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    if (!response.ok) throw new Error('Failed to load analytics');
                    const data = await response.json();
                    
                    // Query Analytics
                    document.getElementById('queryStats').innerHTML = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3>Total Queries</h3>
                                <div class="value">${data.query_analytics.total_queries}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Text Queries</h3>
                                <div class="value">${data.query_analytics.text_queries}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Image Queries</h3>
                                <div class="value">${data.query_analytics.image_queries}</div>
                            </div>
                        </div>
                        <h3 style="margin-top: 20px; margin-bottom: 10px;">Most Asked Questions</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Question</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.query_analytics.popular_questions.map(q => `
                                    <tr>
                                        <td>${escapeHtml(q.question)}</td>
                                        <td>${q.count}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                    
                    // User Analytics
                    document.getElementById('userStats').innerHTML = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3>Total Users</h3>
                                <div class="value">${data.user_analytics.total_users}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Active Users</h3>
                                <div class="value">${data.user_analytics.active_users}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Admin Users</h3>
                                <div class="value">${data.user_analytics.admin_users}</div>
                            </div>
                            <div class="stat-card">
                                <h3>General Users</h3>
                                <div class="value">${data.user_analytics.general_users}</div>
                            </div>
                        </div>
                    `;
                    
                    // Feedback Analytics
                    document.getElementById('feedbackStats').innerHTML = `
                        <div class="stats-grid">
                            <div class="stat-card">
                                <h3>Total Feedback</h3>
                                <div class="value">${data.feedback_analytics.total_feedback}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Likes</h3>
                                <div class="value">${data.feedback_analytics.likes}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Dislikes</h3>
                                <div class="value">${data.feedback_analytics.dislikes}</div>
                            </div>
                            <div class="stat-card">
                                <h3>Satisfaction Rate</h3>
                                <div class="value">${data.feedback_analytics.satisfaction_rate.toFixed(1)}%</div>
                            </div>
                            <div class="stat-card">
                                <h3>With Comments</h3>
                                <div class="value">${data.feedback_analytics.feedback_with_comments}</div>
                            </div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Error loading analytics:', error);
                    document.getElementById('queryStats').innerHTML = '<div class="loading" style="color: #dc3545;">Error loading analytics.</div>';
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                }
            }
            
            loadAnalytics();
        </script>
    </body>
    </html>
    """
    return html_content


def get_admin_training_data_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for admin training data page."""
    return get_authenticated_admin_user(request, credentials, db, "export_training_data")


@app.get("/admin/training-data", response_class=HTMLResponse)
async def admin_training_data_page(
    current_user: Optional[User] = Depends(get_admin_training_data_user)
):
    """
    Training data export page.
    
    Allows admins to export Q&A pairs for training purposes.
    Redirects to login if not authenticated or lacks permission.
    """
    if not current_user:
        return HTMLResponse(
            content='<script>window.location.href="/login";</script>',
            status_code=200
        )
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Training Data Export - Ask-NUO</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1000px;
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
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 2em; margin: 0; }
            .nav-links { display: flex; gap: 15px; flex-wrap: wrap; }
            .nav-links a {
                color: white;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 6px;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s;
            }
            .nav-links a:hover { background: rgba(255,255,255,0.3); }
            .content { padding: 30px; }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #495057;
            }
            .form-group select, .form-group input[type="checkbox"] {
                padding: 10px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 14px;
            }
            .form-group select {
                width: 100%;
            }
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                background: #667eea;
                color: white;
            }
            .btn:hover { background: #5568d3; }
            .info-box {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>📥 Training Data Export</h1>
                    <p style="margin-top: 5px; opacity: 0.9;">Export Q&A pairs for model training</p>
                </div>
                <div class="nav-links">
                    <a href="/">🏠 Home</a>
                    <a href="/admin/dashboard">📈 Dashboard</a>
                    <a href="/admin/users">👥 Users</a>
                    <a href="/admin/analytics">📊 Analytics</a>
                    <a href="/admin/settings">⚙️ Settings</a>
                    <a href="#" onclick="logout(); return false;">🚪 Logout</a>
                </div>
            </div>
            <div class="content">
                <div class="info-box">
                    <h3>Export Training Data</h3>
                    <p style="margin-top: 10px; color: #6c757d;">
                        Export all Q&A pairs from the system for model fine-tuning. 
                        You can choose to include or exclude user feedback.
                    </p>
                </div>
                <form id="exportForm" onsubmit="exportData(event); return false;">
                    <div class="form-group">
                        <label>Export Format *</label>
                        <select id="format" required>
                            <option value="json">JSON</option>
                            <option value="csv">CSV</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="includeFeedback" checked>
                            Include Feedback
                        </label>
                        <p style="margin-top: 5px; color: #6c757d; font-size: 0.9em;">
                            Include user feedback (likes/dislikes and comments) in the export
                        </p>
                    </div>
                    <button type="submit" class="btn">📥 Export Training Data</button>
                </form>
            </div>
        </div>
        <script>
            let authToken = localStorage.getItem('auth_token');
            if (!authToken) {
                window.location.href = '/login';
            }
            
            async function exportData(event) {
                event.preventDefault();
                const format = document.getElementById('format').value;
                const includeFeedback = document.getElementById('includeFeedback').checked;
                
                try {
                    const response = await fetch('/api/admin/training-data/export', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${authToken}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            format: format,
                            include_feedback: includeFeedback
                        })
                    });
                    
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    
                    if (!response.ok) {
                        throw new Error('Failed to export data');
                    }
                    
                    // Download file
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `training_data_${new Date().toISOString().split('T')[0]}.${format}`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    alert('Training data exported successfully!');
                } catch (error) {
                    alert('Error exporting data: ' + error.message);
                }
            }
            
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


def get_admin_settings_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for admin settings page."""
    return get_authenticated_admin_user(request, credentials, db, "manage_system_settings")


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(
    current_user: Optional[User] = Depends(get_admin_settings_user)
):
    """
    System settings page.
    
    Allows admins to view and update system settings.
    Redirects to login if not authenticated or lacks permission.
    """
    if not current_user:
        return HTMLResponse(
            content='<script>window.location.href="/login";</script>',
            status_code=200
        )
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>System Settings - Ask-NUO</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1000px;
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
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 2em; margin: 0; }
            .nav-links { display: flex; gap: 15px; flex-wrap: wrap; }
            .nav-links a {
                color: white;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 6px;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s;
            }
            .nav-links a:hover { background: rgba(255,255,255,0.3); }
            .content { padding: 30px; }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #495057;
            }
            .form-group input, .form-group select {
                width: 100%;
                padding: 10px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 14px;
            }
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                background: #667eea;
                color: white;
            }
            .btn:hover { background: #5568d3; }
            .info-box {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                margin-bottom: 20px;
            }
            .loading { text-align: center; padding: 40px; color: #6c757d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>⚙️ System Settings</h1>
                    <p style="margin-top: 5px; opacity: 0.9;">Manage system configuration</p>
                </div>
                <div class="nav-links">
                    <a href="/">🏠 Home</a>
                    <a href="/admin/dashboard">📈 Dashboard</a>
                    <a href="/admin/users">👥 Users</a>
                    <a href="/admin/analytics">📊 Analytics</a>
                    <a href="/admin/training-data">📥 Export</a>
                    <a href="#" onclick="logout(); return false;">🚪 Logout</a>
                </div>
            </div>
            <div class="content">
                <div id="settingsContent" class="loading">Loading settings...</div>
            </div>
        </div>
        <script>
            let authToken = localStorage.getItem('auth_token');
            if (!authToken) {
                window.location.href = '/login';
            }
            
            async function loadSettings() {
                try {
                    const response = await fetch('/api/admin/system/settings', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    if (!response.ok) throw new Error('Failed to load settings');
                    const settings = await response.json();
                    
                    document.getElementById('settingsContent').innerHTML = `
                        <div class="info-box">
                            <h3>System Configuration</h3>
                            <p style="margin-top: 10px; color: #6c757d;">
                                Configure system-wide settings and preferences.
                            </p>
                        </div>
                        <form id="settingsForm" onsubmit="saveSettings(event); return false;">
                            <div class="form-group">
                                <label>Max File Size (MB)</label>
                                <input type="number" id="maxFileSize" value="${settings.max_file_size_mb}" min="1" max="100">
                            </div>
                            <div class="form-group">
                                <label>Allowed File Types</label>
                                <input type="text" id="allowedFileTypes" value="${settings.allowed_file_types.join(', ')}" placeholder="pdf, docx, txt">
                                <p style="margin-top: 5px; color: #6c757d; font-size: 0.9em;">
                                    Comma-separated list of file extensions
                                </p>
                            </div>
                            <div class="form-group">
                                <label>Max Conversation History</label>
                                <input type="number" id="maxConversationHistory" value="${settings.max_conversation_history}" min="10" max="1000">
                            </div>
                            <div class="form-group">
                                <label>Session Timeout (minutes)</label>
                                <input type="number" id="sessionTimeout" value="${settings.session_timeout_minutes}" min="15" max="10080">
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="enableFeedback" ${settings.enable_feedback ? 'checked' : ''}>
                                    Enable Feedback System
                                </label>
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="enableAnalytics" ${settings.enable_analytics ? 'checked' : ''}>
                                    Enable Analytics
                                </label>
                            </div>
                            <button type="submit" class="btn">💾 Save Settings</button>
                        </form>
                    `;
                } catch (error) {
                    console.error('Error loading settings:', error);
                    document.getElementById('settingsContent').innerHTML = '<div class="loading" style="color: #dc3545;">Error loading settings.</div>';
                }
            }
            
            async function saveSettings(event) {
                event.preventDefault();
                const settings = {
                    max_file_size_mb: parseInt(document.getElementById('maxFileSize').value),
                    allowed_file_types: document.getElementById('allowedFileTypes').value.split(',').map(s => s.trim()),
                    max_conversation_history: parseInt(document.getElementById('maxConversationHistory').value),
                    session_timeout_minutes: parseInt(document.getElementById('sessionTimeout').value),
                    enable_feedback: document.getElementById('enableFeedback').checked,
                    enable_analytics: document.getElementById('enableAnalytics').checked
                };
                
                try {
                    const response = await fetch('/api/admin/system/settings', {
                        method: 'PUT',
                        headers: {
                            'Authorization': `Bearer ${authToken}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(settings)
                    });
                    
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    
                    if (!response.ok) {
                        throw new Error('Failed to save settings');
                    }
                    
                    alert('Settings saved successfully!');
                    loadSettings();
                } catch (error) {
                    alert('Error saving settings: ' + error.message);
                }
            }
            
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                }
            }
            
            loadSettings();
        </script>
    </body>
    </html>
    """
    return html_content


# ============================================================================
# Feedback Endpoints
# ============================================================================

@app.post("/api/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback (like/dislike) for a Q&A pair.
    
    Any authenticated user can provide feedback on any Q&A pair.
    If feedback already exists from this user, it will be updated.
    
    Args:
        request: Feedback data (qa_pair_id, rating, optional feedback_text)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        FeedbackResponse: Feedback ID and confirmation message
        
    Raises:
        HTTPException: 404 if Q&A pair not found, 400 if invalid rating
    """
    from src.database.crud import create_feedback, get_qa_pair
    
    # Verify Q&A pair exists
    qa_pair = get_qa_pair(db, request.qa_pair_id)
    if not qa_pair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Q&A pair not found"
        )
    
    # Validate rating
    if request.rating not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be 1 (dislike) or 2 (like)"
        )
    
    # Create or update feedback (create_feedback handles existing feedback update)
    feedback = create_feedback(
        db=db,
        qa_pair_id=request.qa_pair_id,
        user_id=current_user.id,
        rating=request.rating,
        feedback_text=request.feedback_text
    )
    
    logger.info(f"User {current_user.username} submitted feedback {feedback.id} (rating: {request.rating}) for Q&A pair {request.qa_pair_id}")
    
    return FeedbackResponse(
        feedback_id=feedback.id,
        message="Feedback submitted successfully"
    )


@app.get("/api/feedback/qa-pair/{qa_pair_id}", response_model=FeedbackListResponse)
async def get_feedback_for_qa_pair(
    qa_pair_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all feedback for a specific Q&A pair.
    
    Args:
        qa_pair_id: Q&A pair ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        FeedbackListResponse: List of feedback with user details
        
    Raises:
        HTTPException: 404 if Q&A pair not found
    """
    from src.database.crud import get_qa_pair_feedback, get_qa_pair
    
    # Verify Q&A pair exists
    qa_pair = get_qa_pair(db, qa_pair_id)
    if not qa_pair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Q&A pair not found"
        )
    
    # Get all feedback for this Q&A pair
    feedbacks = get_qa_pair_feedback(db, qa_pair_id)
    
    # Build response with user details
    feedback_details = []
    for feedback in feedbacks:
        feedback_details.append(FeedbackDetailResponse(
            id=feedback.id,
            qa_pair_id=feedback.qa_pair_id,
            user_id=feedback.user_id,
            username=feedback.user.username,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            created_at=feedback.created_at
        ))
    
    return FeedbackListResponse(
        feedbacks=feedback_details,
        total=len(feedback_details)
    )


@app.delete("/api/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete feedback.
    
    Users can only delete their own feedback.
    
    Args:
        feedback_id: Feedback ID to delete
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: 404 if feedback not found, 403 if user doesn't own the feedback
    """
    from src.database.crud import get_feedback, delete_feedback as crud_delete_feedback
    
    # Get feedback
    feedback = get_feedback(db, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Check ownership - users can only delete their own feedback
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own feedback"
        )
    
    # Delete feedback
    success = crud_delete_feedback(db, feedback_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete feedback"
        )
    
    logger.info(f"User {current_user.username} deleted feedback {feedback_id}")
    
    return None


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.get("/api/admin/dashboard", response_model=DashboardStatsResponse)
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_admin_dashboard")),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DashboardStatsResponse: Dashboard statistics
    """
    # Total users
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    inactive_users = total_users - active_users
    
    # Total conversations
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    
    # Total Q&A pairs
    total_qa_pairs = db.query(func.count(QAPair.id)).scalar()
    
    # Feedback statistics
    total_feedback = db.query(func.count(Feedback.id)).scalar()
    likes_count = db.query(func.count(Feedback.id)).filter(Feedback.rating == 2).scalar()
    dislikes_count = db.query(func.count(Feedback.id)).filter(Feedback.rating == 1).scalar()
    
    # Average response time
    avg_response_time = db.query(func.avg(QAPair.processing_time_seconds)).scalar()
    avg_response_time = float(avg_response_time) if avg_response_time else None
    
    # Most active users (by conversation count)
    most_active = db.query(
        User.id,
        User.username,
        func.count(Conversation.id).label('conv_count')
    ).join(
        Conversation, User.id == Conversation.user_id
    ).group_by(
        User.id, User.username
    ).order_by(
        desc('conv_count')
    ).limit(5).all()
    
    most_active_users = [
        {"user_id": u[0], "username": u[1], "conversation_count": u[2]}
        for u in most_active
    ]
    
    # Recent activity (last 10 Q&A pairs)
    recent_qa = db.query(
        QAPair.id,
        QAPair.question,
        QAPair.created_at,
        User.username
    ).join(
        User, QAPair.user_id == User.id
    ).order_by(
        desc(QAPair.created_at)
    ).limit(10).all()
    
    recent_activity = [
        {
            "type": "qa_pair",
            "id": q[0],
            "question": q[1][:100] + "..." if len(q[1]) > 100 else q[1],
            "created_at": q[2].isoformat() if q[2] else None,
            "username": q[3]
        }
        for q in recent_qa
    ]
    
    return DashboardStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_conversations=total_conversations,
        total_qa_pairs=total_qa_pairs,
        total_feedback=total_feedback,
        likes_count=likes_count,
        dislikes_count=dislikes_count,
        average_response_time=avg_response_time,
        most_active_users=most_active_users,
        recent_activity=recent_activity
    )


@app.get("/api/admin/users", response_model=UserListResponse)
async def list_all_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    user_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_user_management")),
    db: Session = Depends(get_db)
):
    """
    List all users with optional filters.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term for username/email
        is_active: Filter by active status
        user_type: Filter by user type
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserListResponse: List of users
    """
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if user_type:
        query = query.filter(User.user_type == user_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    # Build response with additional data
    user_list = []
    for user in users:
        # Get permissions
        permissions = get_user_permissions(db, user.id)
        
        # Get conversation count
        conv_count = db.query(func.count(Conversation.id)).filter(
            Conversation.user_id == user.id
        ).scalar()
        
        # Get Q&A pair count
        qa_count = db.query(func.count(QAPair.id)).filter(
            QAPair.user_id == user.id
        ).scalar()
        
        user_list.append(UserDetailResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            user_type=user.user_type,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            created_by=user.created_by,
            notes=user.notes,
            permissions=permissions,
            conversation_count=conv_count,
            qa_pair_count=qa_count
        ))
    
    return UserListResponse(users=user_list, total=total)


@app.post("/api/admin/users", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    request: AdminCreateUserRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("create_users")),
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only).
    
    Args:
        request: User creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserDetailResponse: Created user details
    """
    # Validate password strength
    validate_password_strength(request.password)
    
    # Check if username exists
    if get_user_by_username(db, request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    if get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Create user
    user = create_user(
        db=db,
        username=request.username,
        email=request.email,
        password_hash=password_hash,
        full_name=request.full_name,
        user_type=request.user_type,
        created_by=current_user.id
    )
    
    # Assign role template
    if request.user_type:
        assign_role_template_to_user(db, user.id, request.user_type)
    
    # Update notes if provided
    if request.notes:
        user.notes = request.notes
        db.commit()
        db.refresh(user)
    
    # Get permissions
    permissions = get_user_permissions(db, user.id)
    
    logger.info(f"Admin {current_user.username} created user {user.username}")
    
    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        created_by=user.created_by,
        notes=user.notes,
        permissions=permissions,
        conversation_count=0,
        qa_pair_count=0
    )


@app.get("/api/admin/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_user_management")),
    db: Session = Depends(get_db)
):
    """
    Get user details by ID.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserDetailResponse: User details
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get permissions
    permissions = get_user_permissions(db, user.id)
    
    # Get conversation count
    conv_count = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == user.id
    ).scalar()
    
    # Get Q&A pair count
    qa_count = db.query(func.count(QAPair.id)).filter(
        QAPair.user_id == user.id
    ).scalar()
    
    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        created_by=user.created_by,
        notes=user.notes,
        permissions=permissions,
        conversation_count=conv_count,
        qa_pair_count=qa_count
    )


@app.put("/api/admin/users/{user_id}", response_model=UserDetailResponse)
async def admin_update_user(
    user_id: int,
    request: AdminUpdateUserRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("edit_users")),
    db: Session = Depends(get_db)
):
    """
    Update user details (admin only).
    
    Args:
        user_id: User ID
        request: Update request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserDetailResponse: Updated user details
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if request.username is not None:
        # Check if new username exists
        existing = get_user_by_username(db, request.username)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = request.username
    
    if request.email is not None:
        # Check if new email exists
        existing = get_user_by_email(db, request.email)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = request.email
    
    if request.full_name is not None:
        user.full_name = request.full_name
    
    if request.user_type is not None:
        user.user_type = request.user_type
        # Reassign role template
        assign_role_template_to_user(db, user_id, request.user_type)
    
    if request.is_active is not None:
        user.is_active = request.is_active
    
    if request.notes is not None:
        user.notes = request.notes
    
    db.commit()
    db.refresh(user)
    
    # Get permissions
    permissions = get_user_permissions(db, user.id)
    
    # Get counts
    conv_count = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == user.id
    ).scalar()
    qa_count = db.query(func.count(QAPair.id)).filter(
        QAPair.user_id == user.id
    ).scalar()
    
    logger.info(f"Admin {current_user.username} updated user {user.username}")
    
    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        created_by=user.created_by,
        notes=user.notes,
        permissions=permissions,
        conversation_count=conv_count,
        qa_pair_count=qa_count
    )


@app.delete("/api/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("deactivate_users")),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user (admin only).
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database session
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    user.is_active = False
    db.commit()
    
    logger.info(f"Admin {current_user.username} deactivated user {user.username}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/admin/users/{user_id}/permissions")
async def get_user_permissions_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_user_management")),
    db: Session = Depends(get_db)
):
    """
    Get user permissions.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: User permissions and available permissions
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user permissions
    user_permissions = get_user_permissions(db, user_id)
    
    # Get all available permissions
    all_permissions = get_all_permissions(db)
    available_permissions = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "granted": p.name in user_permissions
        }
        for p in all_permissions
    ]
    
    return {
        "user_id": user_id,
        "username": user.username,
        "permissions": user_permissions,
        "available_permissions": available_permissions
    }


@app.post("/api/admin/users/{user_id}/permissions")
async def grant_user_permission(
    user_id: int,
    request: GrantPermissionRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("edit_users")),
    db: Session = Depends(get_db)
):
    """
    Grant a permission to a user.
    
    Args:
        user_id: User ID
        request: Permission grant request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get permission
    permission = get_permission_by_name(db, request.permission_name)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Check if already granted
    existing = db.query(UserPermission).filter(
        and_(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission.id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already granted"
        )
    
    # Grant permission
    grant_permission(db, user_id, permission.id, current_user.id)
    
    logger.info(f"Admin {current_user.username} granted permission {request.permission_name} to user {user.username}")
    
    return {"message": f"Permission {request.permission_name} granted successfully"}


@app.delete("/api/admin/users/{user_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_permission(
    user_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("edit_users")),
    db: Session = Depends(get_db)
):
    """
    Revoke a permission from a user.
    
    Args:
        user_id: User ID
        permission_id: Permission ID
        current_user: Current authenticated user
        db: Database session
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Revoke permission
    success = revoke_permission(db, user_id, permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found or not granted"
        )
    
    logger.info(f"Admin {current_user.username} revoked permission {permission_id} from user {user.username}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/admin/users/{user_id}/assign-template")
async def assign_role_template(
    user_id: int,
    request: AssignTemplateRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("edit_users")),
    db: Session = Depends(get_db)
):
    """
    Assign a role template to a user.
    
    Args:
        user_id: User ID
        request: Template assignment request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if template exists
    template = get_role_template_by_name(db, request.template_name)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role template not found"
        )
    
    # Assign template
    success = assign_role_template_to_user(db, user_id, request.template_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role template"
        )
    
    # Update user type
    user.user_type = request.template_name
    db.commit()
    
    logger.info(f"Admin {current_user.username} assigned template {request.template_name} to user {user.username}")
    
    return {"message": f"Role template {request.template_name} assigned successfully"}


@app.get("/api/admin/analytics", response_model=AnalyticsResponse)
async def get_admin_analytics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_analytics")),
    db: Session = Depends(get_db)
):
    """
    Get system analytics.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        AnalyticsResponse: System analytics
    """
    # Query analytics
    total_queries = db.query(func.count(QAPair.id)).scalar()
    text_queries = db.query(func.count(QAPair.id)).filter(QAPair.question_type == "text").scalar()
    image_queries = db.query(func.count(QAPair.id)).filter(QAPair.question_type == "image").scalar()
    
    # Most asked questions (top 10)
    popular_questions = db.query(
        QAPair.question,
        func.count(QAPair.id).label('count')
    ).group_by(
        QAPair.question
    ).order_by(
        desc('count')
    ).limit(10).all()
    
    query_analytics = {
        "total_queries": total_queries,
        "text_queries": text_queries,
        "image_queries": image_queries,
        "popular_questions": [
            {"question": q[0][:200], "count": q[1]}
            for q in popular_questions
        ]
    }
    
    # User analytics
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    admin_users = db.query(func.count(User.id)).filter(User.user_type == "operational_admin").scalar()
    general_users = db.query(func.count(User.id)).filter(User.user_type == "general_user").scalar()
    
    user_analytics = {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "general_users": general_users
    }
    
    # Feedback analytics
    total_feedback = db.query(func.count(Feedback.id)).scalar()
    likes = db.query(func.count(Feedback.id)).filter(Feedback.rating == 2).scalar()
    dislikes = db.query(func.count(Feedback.id)).filter(Feedback.rating == 1).scalar()
    feedback_with_comments = db.query(func.count(Feedback.id)).filter(
        Feedback.feedback_text.isnot(None)
    ).scalar()
    
    feedback_analytics = {
        "total_feedback": total_feedback,
        "likes": likes,
        "dislikes": dislikes,
        "feedback_with_comments": feedback_with_comments,
        "satisfaction_rate": (likes / total_feedback * 100) if total_feedback > 0 else 0
    }
    
    # Time series data (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_queries = db.query(
        func.date(QAPair.created_at).label('date'),
        func.count(QAPair.id).label('count')
    ).filter(
        QAPair.created_at >= thirty_days_ago
    ).group_by(
        func.date(QAPair.created_at)
    ).order_by(
        func.date(QAPair.created_at)
    ).all()
    
    time_series_data = [
        {
            "date": d[0].isoformat() if isinstance(d[0], datetime) else str(d[0]),
            "queries": d[1]
        }
        for d in daily_queries
    ]
    
    return AnalyticsResponse(
        query_analytics=query_analytics,
        user_analytics=user_analytics,
        feedback_analytics=feedback_analytics,
        time_series_data=time_series_data
    )


@app.post("/api/admin/training-data/export")
async def export_training_data(
    request: TrainingDataExportRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("export_training_data")),
    db: Session = Depends(get_db)
):
    """
    Export training data as JSON or CSV.
    
    Args:
        request: Export request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Response: File download
    """
    # Get all Q&A pairs
    qa_pairs = db.query(QAPair).order_by(QAPair.created_at).all()
    
    if request.include_feedback:
        # Include feedback for each Q&A pair
        export_data = []
        for qa in qa_pairs:
            feedback_list = get_qa_pair_feedback(db, qa.id)
            export_data.append({
                "id": qa.id,
                "question": qa.question,
                "answer": qa.answer,
                "sources": qa.sources,
                "question_type": qa.question_type,
                "answer_source_type": qa.answer_source_type,
                "created_at": qa.created_at.isoformat() if qa.created_at else None,
                "feedback": [
                    {
                        "rating": f.rating,
                        "feedback_text": f.feedback_text,
                        "created_at": f.created_at.isoformat() if f.created_at else None
                    }
                    for f in feedback_list
                ]
            })
    else:
        export_data = [
            {
                "id": qa.id,
                "question": qa.question,
                "answer": qa.answer,
                "sources": qa.sources,
                "question_type": qa.question_type,
                "answer_source_type": qa.answer_source_type,
                "created_at": qa.created_at.isoformat() if qa.created_at else None
            }
            for qa in qa_pairs
        ]
    
    if request.format == "csv":
        # Generate CSV
        output = StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            for row in export_data:
                # Flatten nested structures
                flat_row = {}
                for key, value in row.items():
                    if isinstance(value, (list, dict)):
                        flat_row[key] = json.dumps(value)
                    else:
                        flat_row[key] = value
                writer.writerow(flat_row)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=training_data_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
        )
    else:
        # Generate JSON
        return JSONResponse(
            content=export_data,
            headers={"Content-Disposition": f"attachment; filename=training_data_{datetime.utcnow().strftime('%Y%m%d')}.json"}
        )


@app.get("/api/admin/system/settings")
async def get_system_settings(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("manage_system_settings")),
    db: Session = Depends(get_db)
):
    """
    Get system settings.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: System settings
    """
    # Placeholder for system settings
    # In a real implementation, this would read from a settings table or config file
    return {
        "max_file_size_mb": 10,
        "allowed_file_types": ["pdf", "docx", "txt"],
        "max_conversation_history": 100,
        "session_timeout_minutes": 1440,
        "enable_feedback": True,
        "enable_analytics": True
    }


@app.put("/api/admin/system/settings")
async def update_system_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("manage_system_settings")),
    db: Session = Depends(get_db)
):
    """
    Update system settings.
    
    Args:
        settings: Settings dictionary
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Updated settings
    """
    # Placeholder for system settings update
    # In a real implementation, this would write to a settings table or config file
    logger.info(f"Admin {current_user.username} updated system settings")
    return {"message": "Settings updated successfully", "settings": settings}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

