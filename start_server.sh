#!/bin/bash
set -e

# Check if SSH should be enabled
if [ "${SSH_ENABLED}" = "true" ]; then
  # Start SSH server in the background
  echo "Starting SSH server..."
  
  # Create the .ssh directory if it doesn't exist
  mkdir -p /root/.ssh
  chmod 700 /root/.ssh
  
  # Start SSH server
  /usr/sbin/sshd
  
  echo "SSH server is running on port 22 (container)"
  echo "SSH public key authentication is enabled"
  echo "Password authentication is disabled"
  echo ""
  echo "To add your SSH key to the container:"
  echo "docker cp ~/.ssh/id_rsa.pub polarisllm-deployment-server:/root/.ssh/authorized_keys"
  echo "docker exec polarisllm-deployment-server chmod 600 /root/.ssh/authorized_keys"
else
  echo "SSH server is disabled. To enable, set SSH_ENABLED=true in docker-compose.yml"
fi

# Start the API server
echo "Starting PolarisLLM API server..."
exec python /app/api.py 