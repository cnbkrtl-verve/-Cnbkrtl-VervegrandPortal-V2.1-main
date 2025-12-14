#!/bin/bash
# test-local.sh - Script to test the application locally before deploying

echo "🧪 Testing Shopify Embedded App Locally"
echo "========================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

echo "✅ Docker found"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your actual credentials"
    exit 1
fi

echo "✅ .env file found"

# Load environment variables
set -a
source .env
set +a

# Validate required environment variables
if [ -z "$SHOPIFY_API_KEY" ] || [ -z "$SHOPIFY_API_SECRET" ]; then
    echo "❌ SHOPIFY_API_KEY and SHOPIFY_API_SECRET must be set in .env file"
    exit 1
fi

echo "✅ Environment variables validated"

# Build Docker image
echo ""
echo "🏗️  Building Docker image..."
docker build -t shopify-app-test .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"

# Run container
echo ""
echo "🚀 Starting container..."
echo "Access the app at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

docker run -it --rm \
    -p 8000:8000 \
    -e SHOPIFY_API_KEY="$SHOPIFY_API_KEY" \
    -e SHOPIFY_API_SECRET="$SHOPIFY_API_SECRET" \
    -e APP_URL="http://localhost:8000" \
    -e SHOPIFY_SCOPES="$SHOPIFY_SCOPES" \
    -e SESSION_SECRET="test-secret-key-for-local-development" \
    -e PORT=8000 \
    -e STREAMLIT_PORT=8501 \
    --name shopify-app-test \
    shopify-app-test

echo ""
echo "🛑 Container stopped"
