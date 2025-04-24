#!/bin/bash
set -e  # Exit on any error

echo "🚀 Setting up PolarisLLM Deployment Server..."
echo "=============================================="

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker is installed"

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker Compose is installed"

# Check for NVIDIA Docker support
if ! docker info | grep -i nvidia &> /dev/null; then
    echo "⚠️ Warning: NVIDIA Docker support not detected. GPU acceleration may not be available."
    echo "   See https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
else
    echo "✅ NVIDIA Docker support detected"
fi

# Check for port conflicts
check_port() {
    local port=$1
    local service_name=$2
    
    # Check if port is in use
    if command -v netstat &> /dev/null; then
        # Use netstat if available
        if netstat -tuln | grep -q ":$port "; then
            echo "⚠️ Warning: Port $port is already in use by another service"
            netstat -tuln | grep ":$port " | head -1
            return 1
        fi
    elif command -v ss &> /dev/null; then
        # Fall back to ss if netstat is not available
        if ss -tuln | grep -q ":$port "; then
            echo "⚠️ Warning: Port $port is already in use by another service"
            ss -tuln | grep ":$port " | head -1
            return 1
        fi
    else
        # Simple check using lsof if available
        if command -v lsof &> /dev/null; then
            if lsof -i:$port -P -n | grep -q "LISTEN"; then
                echo "⚠️ Warning: Port $port is already in use by another service"
                lsof -i:$port -P -n | grep "LISTEN" | head -1
                return 1
            fi
        fi
    fi
    
    echo "✅ Port $port is available for $service_name"
    return 0
}

# Check API port
api_port_conflict=false
if ! check_port 8020 "PolarisLLM API"; then
    api_port_conflict=true
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p cache logs
echo "✅ Directories created"

# Stop any existing container
echo "🛑 Stopping any existing PolarisLLM containers..."
docker-compose down 2>/dev/null || true
echo "✅ Environment clean"

# Build and start the container
echo "🏗️ Building and starting PolarisLLM container..."
if [ "$api_port_conflict" = true ]; then
    echo "⚠️ API port conflict detected. Modifying docker-compose.yml to use a different port..."
    # Find an available port for the API
    for port in $(seq 8021 8099); do
        if check_port $port "PolarisLLM API" > /dev/null; then
            # Temporarily modify the docker-compose.yml file
            sed -i.bak "s/\"8020:8020\"/\"$port:8020\"/" docker-compose.yml
            echo "🔄 Using port $port for API instead"
            api_port=$port
            break
        fi
    done
fi

# Start the container
docker-compose up -d --build

# Wait for the server to start
echo "⏳ Waiting for server to start..."
api_port=${api_port:-8020}  # Default to 8020 if not set

for i in {1..30}; do
    if curl -s http://localhost:$api_port > /dev/null; then
        echo "✅ Server is running on port $api_port!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Server didn't start within expected time"
        echo "   Check logs with: docker-compose logs"
        exit 1
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "🎉 PolarisLLM Deployment Server is ready!"
echo "=============================================="
echo ""
echo "📋 Available commands:"
echo ""
echo "📊 View server status:"
echo "   docker-compose ps"
echo ""
echo "📋 List available models:"
echo "   docker-compose exec polarisllm polarisLLM list models"
echo ""
echo "🚀 Deploy a model:"
echo "   docker-compose exec polarisllm polarisLLM deploy Qwen/Qwen2-VL-7B-Instruct"
echo ""
echo "📋 List active deployments:"
echo "   docker-compose exec polarisllm polarisLLM list deployments"
echo ""
echo "📜 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop the server:"
echo "   docker-compose down"
echo ""
echo "For more information, see the README.md file"

exit 0 