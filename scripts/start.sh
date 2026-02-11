#!/bin/bash

# E-Commerce Recommendation Engine - Startup Script
# This script sets up and starts all services

set -e

echo "======================================"
echo "E-Commerce Recommendation Engine"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration before proceeding"
    exit 1
fi

# Load environment variables
source .env

echo "1. Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✓ Python 3 found"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found (optional for local setup)"
fi

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis client not found (optional for local setup)"
fi

echo ""
echo "2. Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "3. Setting up database..."
python src/database.py

echo ""
echo "4. Generating sample data (optional)..."
read -p "Generate sample data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/generate_data.py
fi

echo ""
echo "5. Starting services..."
echo ""

# Choose startup method
echo "Select startup method:"
echo "1) Docker Compose (recommended)"
echo "2) Manual (requires Redis & PostgreSQL running)"
read -p "Choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed"
        exit 1
    fi
    
    echo "Starting services with Docker Compose..."
    docker-compose up -d
    
    echo ""
    echo "✓ Services started!"
    echo ""
    echo "Access points:"
    echo "  API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Dashboard: http://localhost:8501"
    echo ""
    echo "View logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "Stop services:"
    echo "  docker-compose down"
    
elif [ "$choice" = "2" ]; then
    echo "Starting services manually..."
    echo ""
    echo "Make sure Redis and PostgreSQL are running!"
    echo ""
    
    # Start API in background
    echo "Starting API on port 8000..."
    uvicorn src.api:app --host 0.0.0.0 --port 8000 &
    API_PID=$!
    
    # Wait a bit
    sleep 2
    
    # Start Dashboard in background
    echo "Starting Dashboard on port 8501..."
    streamlit run src/dashboard.py --server.port 8501 &
    DASHBOARD_PID=$!
    
    echo ""
    echo "✓ Services started!"
    echo ""
    echo "Access points:"
    echo "  API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Dashboard: http://localhost:8501"
    echo ""
    echo "Stop services:"
    echo "  kill $API_PID $DASHBOARD_PID"
    
    # Save PIDs
    echo $API_PID > .api.pid
    echo $DASHBOARD_PID > .dashboard.pid
    
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Wait for Ctrl+C
    trap "kill $API_PID $DASHBOARD_PID; exit" INT
    wait
    
else
    echo "Invalid choice"
    exit 1
fi
