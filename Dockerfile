# =============================================================================
# FlexCube AI Assistant - Dockerfile
# =============================================================================
# This Dockerfile creates a containerized version of the Ask-NUO application.
# It includes the FastAPI server, RAG pipeline, and all dependencies.
# 
# Note: This container requires external Ollama and Qdrant services.
# Use docker-compose.full.yml for complete deployment.
# =============================================================================
# Build: docker build -t flexcube-ai-assistant:latest .
# Run:   docker run -p 8000:8000 flexcube-ai-assistant:latest
# =============================================================================

FROM python:3.11-slim

# Set environment variables
# Prevents Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system dependencies
# - gcc and build tools for compiling Python packages
# - curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
# This way, dependencies are only reinstalled if requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir docx2txt

# Copy application source code
COPY src/ ./src/

# Create directories for data and logs
RUN mkdir -p /app/data/documents /app/logs

# Set environment variables for the application
# These can be overridden at runtime with -e flag
ENV OLLAMA_BASE_URL=http://ollama:11434
ENV QDRANT_HOST=qdrant
ENV QDRANT_PORT=6333
ENV DATA_DIR=/app/data/documents
ENV LOG_LEVEL=INFO

# Expose the FastAPI port
EXPOSE 8000

# Health check - verifies the application is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application with Uvicorn
# - host 0.0.0.0 allows connections from outside the container
# - workers 1 to conserve memory (CPU inference is heavy)
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

