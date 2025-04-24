#!/bin/bash

# Make sure we're in the app directory
cd /app

echo "Starting Swift Model Deployment API Server..."
python /app/api.py &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"
echo ""
echo "=== PolarisLLM Deployment Server ==="
echo ""
echo "The server is now running on port 8020."
echo ""
echo "Available commands:"
echo "  * polarisLLM list models - List all available models"
echo "  * polarisLLM deploy <model_id> - Deploy a model"
echo "  * polarisLLM list deployments - List active deployments"
echo "  * polarisLLM logs <model_id> - View deployment logs"
echo "  * polarisLLM test text <model_id> - Test a text model"
echo "  * polarisLLM test vision <model_id> <image_path> - Test a vision model"
echo "  * polarisLLM stop <model_id> - Stop a deployment"
echo ""
echo "Use 'polarisLLM help' for more information."
echo ""
trap "kill $SERVER_PID; exit" INT TERM
wait $SERVER_PID 