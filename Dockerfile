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
    && rm -rf /var/lib/apt/lists/*

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

# Expose the API port
EXPOSE 8020
# Expose model server ports
EXPOSE 8001-8099

# Start the API server
CMD ["python", "api.py"]

# Label the image
LABEL maintainer="PolarisLLM Team" \
      description="PolarisLLM Model Deployment Server - Deploy and serve large language models with ease" \
      version="1.0"

# Create README for the container
COPY README.md /app/README.md
