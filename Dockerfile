FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    net-tools \
    openssh-server \
    mosh \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH server for public key auth
RUN mkdir -p /var/run/sshd /root/.ssh && \
    chmod 700 /root/.ssh && \
    echo 'AuthorizedKeysFile .ssh/authorized_keys' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config

# Set Python aliases
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create app directory
WORKDIR /app

# Install ModelScope Swift
RUN pip install "ms-swift[all]" -U

# Copy the application code
COPY . /app/

# Install additional Python dependencies
RUN pip install fastapi uvicorn requests tabulate

# Install required apps
RUN mkdir -p /app/envs

# Make the script executable
RUN chmod +x /app/polarisLLM.py
RUN ln -sf /app/polarisLLM.py /usr/local/bin/polarisLLM

# Create startup script with SSH
COPY ./start_server.sh /app/start_server.sh
RUN chmod +x /app/start_server.sh

# Expose the API port
EXPOSE 1009
# Expose model server ports
EXPOSE 8001-8099
# Expose SSH and Mosh ports
EXPOSE 22 60000-61000/udp

# Start the API server with SSH
CMD ["/app/start_server.sh"]

# Label the image
LABEL maintainer="PolarisLLM Team" \
      description="PolarisLLM Model Deployment Server - Deploy and serve large language models with ease" \
      version="1.0"

# Create README for the container
COPY README.md /app/README.md
