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

# Check for Docker Compose and install if not present
install_docker_compose() {
    echo "🔄 Installing Docker Compose..."
    
    # Detect OS
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    
    case "$OS" in
        Linux)
            echo "📋 Installing Docker Compose for Linux ($ARCH)..."
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$OS-$ARCH" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose 2>/dev/null || true
            ;;
        Darwin)
            echo "📋 Installing Docker Compose for macOS..."
            if command -v brew &> /dev/null; then
                brew install docker-compose
            else
                echo "❌ Homebrew not found. Please install Docker Compose manually: https://docs.docker.com/compose/install/"
                exit 1
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "📋 For Windows, please install Docker Desktop which includes Docker Compose."
            echo "   Download from: https://docs.docker.com/desktop/install/windows-install/"
            exit 1
            ;;
        *)
            echo "❌ Unsupported operating system: $OS. Please install Docker Compose manually: https://docs.docker.com/compose/install/"
            exit 1
            ;;
    esac
    
    echo "✅ Docker Compose installed successfully"
}

if ! command -v docker-compose &> /dev/null; then
    echo "⚠️ Docker Compose is not installed."
    install_docker_compose
else
    echo "✅ Docker Compose is installed"
fi

# Verify Docker Compose installation
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose installation failed. Please install Docker Compose manually: https://docs.docker.com/compose/install/"
    exit 1
fi

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

# Helper function to check if a port is available
is_port_available() {
    ! (netstat -tuln | grep -q ":$1 ")
}

# Function to find an available random port
find_available_port() {
    local attempts=30
    local port
    
    for ((i=1; i<=attempts; i++)); do
        # Generate a random port between 10000 and 65000
        port=$((RANDOM % 55000 + 10000))
        
        if is_port_available "$port"; then
            echo "$port"
            return 0
        fi
    done
    
    echo "0"  # Return 0 if no port is found
    return 1
}

# Find an available random port for the API
echo "🔍 Finding an available random port for the API..."
api_port=$(find_available_port)

if [ "$api_port" -eq 0 ]; then
    echo "❌ Could not find an available port after multiple attempts. Please free up some ports and try again."
    exit 1
fi

echo "✅ Found available port: $api_port"

# Update the docker-compose.yml file to use the random port
echo "🔧 Updating docker-compose.yml to use port $api_port..."
sed -i "s/1009:1009/$api_port:1009/g" docker-compose.yml

# Replace any other hardcoded ports in the docker-compose.yml file
# Find all port bindings in docker-compose.yml and replace them with random ports
echo "🔄 Replacing all hardcoded ports with random ports in docker-compose.yml..."

# Function to update a port binding in docker-compose.yml
update_port_binding() {
    local pattern=$1
    local container_port=$2
    
    # Extract all port bindings matching the pattern
    local bindings=$(grep -oE "$pattern" docker-compose.yml || echo "")
    
    if [ -n "$bindings" ]; then
        for binding in $bindings; do
            # Skip if it's the API port we already changed
            if [[ "$binding" == *"$api_port:1009"* ]]; then
                continue
            fi
            
            # Find an available random port
            local random_port=$(find_available_port)
            
            if [ "$random_port" -eq 0 ]; then
                echo "⚠️ Warning: Could not find an available port for $binding, skipping..."
                continue
            fi
            
            # Replace the port binding
            echo "   Replacing $binding with $random_port:$container_port"
            sed -i "s/$binding/$random_port:$container_port/g" docker-compose.yml
        done
    fi
}

# Extract all port mappings from docker-compose.yml
port_mappings=$(grep -oE "[0-9]+:[0-9]+" docker-compose.yml || echo "")

# Replace each port mapping with a random port
if [ -n "$port_mappings" ]; then
    for mapping in $port_mappings; do
        # Skip if it's the API port we already changed
        if [[ "$mapping" == "$api_port:1009" ]]; then
            continue
        fi
        
        # Extract container port (the part after the colon)
        container_port=$(echo "$mapping" | cut -d':' -f2)
        
        # Find an available random port
        random_port=$(find_available_port)
        
        if [ "$random_port" -eq 0 ]; then
            echo "⚠️ Warning: Could not find an available port for $mapping, skipping..."
            continue
        fi
        
        # Replace the port binding
        echo "   Replacing $mapping with $random_port:$container_port"
        sed -i "s/$mapping/$random_port:$container_port/g" docker-compose.yml
    done
fi

echo "🔌 Will use API port: $api_port"

# Start the containers
docker-compose up -d --build

# Wait for the server to start
echo "⏳ Waiting for server to start..."

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
echo "  The API port ($api_port) is bound. To expose other ports:"
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
