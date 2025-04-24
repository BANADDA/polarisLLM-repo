#!/bin/bash

# Initialize the PolarisLLM repo
echo "Initializing PolarisLLM deployment server..."

# Create required directories
mkdir -p cache logs

# Check for Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check for NVIDIA Docker support
if ! docker info | grep -i nvidia &> /dev/null; then
    echo "Warning: NVIDIA Docker support not detected. GPU acceleration may not be available."
    echo "See https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
fi

# Ready to go
echo "Initialization complete!"
echo "You can now start the server with: docker-compose up -d"
echo "To see available models, run: docker-compose exec polarisllm polarisLLM list models"

exit 0 