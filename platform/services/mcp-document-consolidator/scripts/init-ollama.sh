#!/bin/bash
# Initialize Ollama models for MCP Document Consolidator

set -e

echo "==================================="
echo "Initializing Ollama Models"
echo "==================================="

OLLAMA_HOST=${OLLAMA_BASE_URL:-http://localhost:11434}

# Check if Ollama is running
echo "Checking Ollama service at $OLLAMA_HOST..."
if ! curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
    echo "Error: Ollama is not running at $OLLAMA_HOST"
    echo "Please start Ollama first:"
    echo "  docker-compose up -d ollama"
    exit 1
fi
echo "✓ Ollama is running"

# Models to pull
MODELS=(
    "llama3.1:8b"
    "codellama:7b"
    "mistral:7b"
)

echo ""
echo "Pulling required models..."

for model in "${MODELS[@]}"; do
    echo ""
    echo "Pulling $model..."
    curl -X POST "$OLLAMA_HOST/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$model\"}" \
        --no-buffer
    echo "✓ $model ready"
done

echo ""
echo "==================================="
echo "All models initialized!"
echo "==================================="

# List available models
echo ""
echo "Available models:"
curl -s "$OLLAMA_HOST/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for model in data.get('models', []):
    print(f\"  - {model['name']}\")
"
