#!/bin/bash
# start.sh - Startup script for Shopify Embedded App on Render
# This script starts both FastAPI (OAuth gateway) and Streamlit (app UI) on a single port

set -e  # Exit on any error

echo "================================================"
echo "🚀 Starting Vervegrand Shopify Embedded App"
echo "================================================"

# Environment validation
if [ -z "$SHOPIFY_API_KEY" ] || [ -z "$SHOPIFY_API_SECRET" ]; then
    echo "❌ ERROR: SHOPIFY_API_KEY and SHOPIFY_API_SECRET must be set"
    exit 1
fi

echo "✅ Environment variables validated"

# Port configuration
export FASTAPI_PORT=${PORT:-8000}
export STREAMLIT_PORT=8501
export APP_URL=${APP_URL:-"https://your-app.onrender.com"}

echo "📡 FastAPI Gateway will run on port: $FASTAPI_PORT"
echo "🎨 Streamlit UI will run on port: $STREAMLIT_PORT"
echo "🌐 App URL: $APP_URL"

# Generate session secret if not provided
if [ -z "$SESSION_SECRET" ]; then
    export SESSION_SECRET=$(openssl rand -hex 32)
    echo "🔐 Generated session secret"
fi

# Create logs directory
mkdir -p /app/logs

# Function to handle shutdown gracefully
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $STREAMLIT_PID 2>/dev/null || true
    kill $FASTAPI_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start Streamlit in the background
echo "================================================"
echo "🎨 Starting Streamlit on port $STREAMLIT_PORT..."
echo "================================================"

streamlit run streamlit_app.py \
    --server.port=$STREAMLIT_PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false \
    --theme.base=light \
    --theme.primaryColor=#008060 \
    --theme.backgroundColor=#f6f6f7 \
    --theme.secondaryBackgroundColor=#ffffff \
    --theme.textColor=#202223 \
    --theme.font=sans-serif \
    > /app/logs/streamlit.log 2>&1 &

STREAMLIT_PID=$!
echo "✅ Streamlit started (PID: $STREAMLIT_PID)"

# Wait for Streamlit to be ready
echo "⏳ Waiting for Streamlit to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$STREAMLIT_PORT/_stcore/health > /dev/null 2>&1; then
        echo "✅ Streamlit is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ ERROR: Streamlit failed to start within 30 seconds"
        cat /app/logs/streamlit.log
        exit 1
    fi
    sleep 1
    echo -n "."
done

# Start FastAPI gateway on the exposed port
echo "================================================"
echo "🚪 Starting FastAPI Gateway on port $FASTAPI_PORT..."
echo "================================================"

uvicorn main:app \
    --host 0.0.0.0 \
    --port $FASTAPI_PORT \
    --log-level info \
    --no-access-log \
    > /app/logs/fastapi.log 2>&1 &

FASTAPI_PID=$!
echo "✅ FastAPI Gateway started (PID: $FASTAPI_PID)"

# Wait for FastAPI to be ready
echo "⏳ Waiting for FastAPI to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$FASTAPI_PORT/health > /dev/null 2>&1; then
        echo "✅ FastAPI is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ ERROR: FastAPI failed to start within 30 seconds"
        cat /app/logs/fastapi.log
        exit 1
    fi
    sleep 1
    echo -n "."
done

echo "================================================"
echo "✅ All services running successfully!"
echo "================================================"
echo "📊 Service Status:"
echo "   - FastAPI Gateway: http://localhost:$FASTAPI_PORT (PID: $FASTAPI_PID)"
echo "   - Streamlit UI: http://localhost:$STREAMLIT_PORT (PID: $STREAMLIT_PID)"
echo "================================================"
echo "📝 Logs are available at:"
echo "   - FastAPI: /app/logs/fastapi.log"
echo "   - Streamlit: /app/logs/streamlit.log"
echo "================================================"
echo "🔗 Public URL: $APP_URL"
echo "================================================"

# Monitor both processes and restart if either crashes
while true; do
    if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "❌ ERROR: Streamlit process died (PID: $STREAMLIT_PID)"
        cat /app/logs/streamlit.log | tail -50
        exit 1
    fi
    
    if ! kill -0 $FASTAPI_PID 2>/dev/null; then
        echo "❌ ERROR: FastAPI process died (PID: $FASTAPI_PID)"
        cat /app/logs/fastapi.log | tail -50
        exit 1
    fi
    
    sleep 10
done
