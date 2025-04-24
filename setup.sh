#!/bin/bash
set -e  # Exit on any error

echo "🚀 Setting up PolarisLLM Deployment Server..."
echo "=============================================="

# Process command line arguments
ENABLE_SSH=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --with-ssh)
      ENABLE_SSH=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Available options:"
      echo "  --with-ssh     Enable SSH/Mosh support (disabled by default)"
      exit 1
      ;;
  esac
done

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

# Create required directories
echo "📁 Creating required directories..."
mkdir -p cache logs
echo "✅ Directories created"

# Update the SSH settings in docker-compose.yml
if [ "$ENABLE_SSH" = "true" ]; then
    echo "🔐 Enabling SSH/Mosh support..."
    # Use sed to enable SSH in docker-compose.yml
    sed -i 's/SSH_ENABLED=false/SSH_ENABLED=true/' docker-compose.yml
    echo "✅ SSH/Mosh support enabled"
fi

# Stop any existing container
echo "🛑 Stopping any existing PolarisLLM containers..."
docker-compose down 2>/dev/null || true
echo "✅ Environment clean"

# Build and start the container with increased timeout
echo "🏗️ Building and starting PolarisLLM container..."
export COMPOSE_HTTP_TIMEOUT=180  # Increase timeout to 3 minutes
docker-compose up -d --build

# Wait for the server to start
echo "⏳ Waiting for server to start..."
api_port=8020  # Fixed API port

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

# Get public IP address if possible
PUBLIC_IP=$(curl -s https://api.ipify.org 2>/dev/null || echo "YOUR_PUBLIC_IP")

echo ""
echo "🎉 PolarisLLM Deployment Server is ready!"
echo "=============================================="
echo ""
echo "📋 Connection Information:"
echo "  - API: http://localhost:$api_port"
if [ "$PUBLIC_IP" != "YOUR_PUBLIC_IP" ]; then
    echo "  - Public API: http://$PUBLIC_IP:$api_port (if firewall allows)"
fi

echo ""
echo "🔌 Port Binding Instructions:"
echo "  Only the API port (8020) is bound by default. To expose other ports:"
echo ""
echo "  1. Stop the container:"
echo "     docker-compose down"
echo ""
echo "  2. Edit docker-compose.yml to add port mappings under the 'ports:' section:"
echo "     - \"9001:8001\"  # For model server port 8001"
echo "     - \"2222:22\"    # For SSH access"
echo "     - \"60000-61000:60000-61000/udp\"  # For Mosh (if needed)"
echo ""
echo "  3. Restart the container:"
echo "     docker-compose up -d"
echo ""

echo "🔐 SSH Access Instructions:"
echo "  SSH server is running inside the container. To access it:"
echo ""
echo "  1. Add your SSH public key to the container:"
echo "     docker cp ~/.ssh/id_rsa.pub polarisllm-deployment-server:/root/.ssh/authorized_keys"
echo "     docker exec polarisllm-deployment-server chmod 600 /root/.ssh/authorized_keys"
echo ""
echo "  2. Expose SSH port by updating docker-compose.yml and adding:"
echo "     - \"2222:22\"    # Map host port 2222 to container port 22"
echo ""
echo "  3. After restarting, connect with:"
echo "     ssh -p 2222 root@localhost"
echo "     Or for public access: ssh -p 2222 root@YOUR_PUBLIC_IP"
echo ""
echo "  4. For Mosh, add UDP port range to docker-compose.yml:"
echo "     - \"60000-61000:60000-61000/udp\"" 
echo "     Then connect with: mosh --ssh=\"ssh -p 2222\" root@YOUR_IP"
echo ""

echo "📋 Available Commands:"
echo "  • View server status:"
echo "    docker-compose ps"
echo ""
echo "  • List available models:"
echo "    docker-compose exec polarisllm polarisLLM list models"
echo ""
echo "  • Deploy a model:"
echo "    docker-compose exec polarisllm polarisLLM deploy Qwen/Qwen2-VL-7B-Instruct"
echo ""
echo "  • List active deployments:"
echo "    docker-compose exec polarisllm polarisLLM list deployments"
echo ""
echo "  • View logs:"
echo "    docker-compose logs -f"
echo ""
echo "  • Stop the server:"
echo "    docker-compose down"
echo ""

exit 0 