#!/bin/bash

# AI Appointment Booking Chatbot - Startup Script
# This script starts all services and initializes the system

set -e

echo "🤖 AI Appointment Booking Chatbot - Startup Script"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists for chatbot
if [ ! -f "chatbot-service/.env" ]; then
    echo "⚠️  Chatbot .env file not found. Creating from template..."
    cp chatbot-service/env.example chatbot-service/.env
    echo "📝 Please edit chatbot-service/.env and add your OPENAI_API_KEY"
    echo "   Then run this script again."
    exit 1
fi

# Check if OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" chatbot-service/.env; then
    echo "⚠️  OpenAI API key not found in chatbot-service/.env"
    echo "   Please add your OPENAI_API_KEY to the .env file"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Start all services
echo "🚀 Starting all services with Docker Compose..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is healthy"
            return 0
        fi
        echo "⏳ Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    echo "❌ $service_name failed to start"
    return 1
}

# Check each service
check_service "Calendar Service" "http://localhost:8000/health"
check_service "Chatbot Service" "http://localhost:8001/api/v1/health/"
check_service "Frontend" "http://localhost:3000"

echo ""
echo "🎉 All services are running!"
echo ""
echo "📋 Service URLs:"
echo "   • Chatbot UI:     http://localhost:3000"
echo "   • Calendar API:   http://localhost:8000/docs"
echo "   • Chatbot API:    http://localhost:8001/docs"
echo ""
echo "🛠️  Useful commands:"
echo "   • View logs:      docker-compose logs -f"
echo "   • Stop services:  docker-compose down"
echo "   • Restart:        docker-compose restart"
echo ""
echo "🧪 Run integration tests:"
echo "   docker-compose exec chatbot-service python ../test_integration.py"
echo ""
echo "Happy chatting! 🤖✨"