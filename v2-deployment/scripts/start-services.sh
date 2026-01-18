#!/bin/bash
# Direct service startup (fallback when Docker fails)

cd "$(dirname "$0")/../.."

# Activate virtual environment if exists
[ -d ".venv" ] && source .venv/bin/activate

echo "Starting platform services directly..."
cd ./platform/src

# Start each layer in background
for layer in L01_data_layer L02_runtime L03_tool_execution L04_model_gateway L05_planning L06_evaluation L07_learning L09_api_gateway L10_human_interface L11_integration; do
    if [ -d "$layer" ]; then
        PORT=$(echo $layer | sed 's/L0\([0-9]\).*/800\1/' | sed 's/L\([0-9]\{2\}\).*/80\1/')
        echo "Starting $layer on port $PORT..."
        cd $layer
        if [ -f "main.py" ]; then
            nohup uvicorn main:app --host 0.0.0.0 --port $PORT > ../../../v2-deployment/logs/$layer.log 2>&1 &
            echo "  PID: $!"
        else
            echo "  Warning: main.py not found in $layer"
        fi
        cd ..
    fi
done

echo ""
echo "Services starting in background. Check logs in v2-deployment/logs/"
echo "To check status: ps aux | grep uvicorn"
