#!/bin/bash
# Setup script for MCP Document Consolidator

set -e

echo "==================================="
echo "MCP Document Consolidator Setup"
echo "==================================="

# Check Node.js version
NODE_VERSION=$(node -v 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1)
if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" -lt 20 ]; then
    echo "Error: Node.js 20 or higher is required"
    echo "Current version: $(node -v 2>/dev/null || echo 'not installed')"
    exit 1
fi
echo "✓ Node.js version: $(node -v)"

# Check Python
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ -z "$PYTHON_VERSION" ]; then
    echo "Warning: Python 3 not found. Embedding service will not work."
else
    echo "✓ Python version: $PYTHON_VERSION"
fi

# Check Docker
if command -v docker &> /dev/null; then
    echo "✓ Docker: $(docker --version)"
else
    echo "Warning: Docker not found. Required for running services."
fi

# Install Node dependencies
echo ""
echo "Installing Node.js dependencies..."
npm install

# Setup Python virtual environment
if [ -n "$PYTHON_VERSION" ]; then
    echo ""
    echo "Setting up Python virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r python/requirements.txt
    deactivate
    echo "✓ Python dependencies installed"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created. Please update with your settings."
fi

# Build TypeScript
echo ""
echo "Building TypeScript..."
npm run build

echo ""
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Update .env with your configuration"
echo "2. Start services: docker-compose up -d"
echo "3. Wait for services to be healthy"
echo "4. Run the server: npm start"
echo ""
echo "For development:"
echo "  npm run dev"
echo ""
echo "To pull Ollama models:"
echo "  docker exec consolidator-ollama ollama pull llama3.1:8b"
echo "  docker exec consolidator-ollama ollama pull codellama:7b"
echo "  docker exec consolidator-ollama ollama pull mistral:7b"
