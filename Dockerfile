# ============================================
# SHOPIFY EMBEDDED APP - DOCKERFILE
# ============================================
# This Dockerfile creates a production-ready container for a Shopify embedded app
# that runs both FastAPI (OAuth gateway) and Streamlit (UI) on Render's free tier.
# 
# Architecture:
# - FastAPI: Handles Shopify OAuth flow and proxies requests
# - Streamlit: Provides the application UI
# - Single port exposure: Required for Render free tier
# ============================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# - curl: For health checks
# - openssl: For generating session secrets
RUN apt-get update && apt-get install -y \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for Shopify integration
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    httpx==0.25.1 \
    python-multipart==0.0.6 \
    itsdangerous==2.1.2

# Copy application files
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Create logs directory
RUN mkdir -p /app/logs

# Expose the port (Render will assign PORT environment variable)
# Note: Render's free tier only allows one exposed port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start the application using the startup script
CMD ["./start.sh"]
