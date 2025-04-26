#!/bin/bash

# Check if GPU count is provided
if [ "$1" == "1" ]; then
    GPU_COUNT=1
    DEVICES="0"
    TP_SIZE=1
    echo "Using 1 GPU for deployment (GPU 0)"
elif [ "$1" == "4" ]; then
    GPU_COUNT=4
    DEVICES="0,1,2,3"
    TP_SIZE=4
    echo "Using 4 GPUs for deployment (GPUs 0-3)"
else
    echo "Usage: $0 [1|4]"
    echo "  1: Use 1 GPU (GPU 0)"
    echo "  4: Use 4 GPUs (GPUs 0-3)"
    exit 1
fi

# Kill any existing deployments
pkill -f "swift deploy"
sleep 2

# Set up environment variables for better NCCL performance
export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=0
export NCCL_IB_GID_INDEX=3
export NCCL_SOCKET_IFNAME=eth0
export NCCL_DEBUG_SUBSYS=ALL

# Create deployment directory
mkdir -p ~/llm-deployment-server/qwen

echo "Deploying Qwen2.5-7B-Instruct with ${GPU_COUNT}-GPU configuration..."
CUDA_VISIBLE_DEVICES=${DEVICES} \
swift deploy \
    --model Qwen/Qwen2.5-7B-Instruct \
    --infer_backend vllm \
    --max_model_len 8192 \
    $([ $TP_SIZE -gt 1 ] && echo "--tensor_parallel_size $TP_SIZE") \
    --gpu_memory_utilization 0.75 \
    --port 1088 \
    --host 0.0.0.0 &> ~/llm-deployment-server/qwen/deploy.log &

DEPLOY_PID=$!
echo "Qwen deployment started with PID: $DEPLOY_PID"
echo "Deployment log: ~/llm-deployment-server/qwen/deploy.log"
echo "API will be available at: http://localhost:1088/v1"

# Create a simple function to test the deployment
cat > ~/llm-deployment-server/test_qwen.py << 'EOL'
#!/usr/bin/env python3
import requests
import json
import time
import sys

def test_model(max_attempts=20, timeout=300):
    """Test if the model is successfully deployed and responding."""
    url = "http://localhost:1088/v1/models"
    print(f"Testing connection to {url}")
    
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < timeout and attempts < max_attempts:
        try:
            attempts += 1
            print(f"Attempt {attempts}/{max_attempts}...")
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("\n✅ Model API is available!")
                print(f"Models: {response.json()}")
                return test_completion()
            
            print(f"Model not ready yet (status code: {response.status_code}), waiting...")
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
        
        # Wait before trying again
        time.sleep(15)
    
    print("\n❌ Model API did not become available within the timeout period.")
    return False

def test_completion():
    """Test a simple completion request."""
    url = "http://localhost:1088/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "user", "content": "What are three advantages of using tensor parallelism for LLM deployment?"}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    print("\nSending test query to the model...")
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Model responded successfully!")
            print("\nResponse content:")
            print("-" * 80)
            print(result['choices'][0]['message']['content'])
            print("-" * 80)
            return True
        else:
            print(f"\n❌ Error response: {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return False

if __name__ == "__main__":
    print("Waiting for the model to initialize...")
    print("This may take several minutes for large models with tensor parallelism.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        # Let the deployment initialize for 3 minutes before testing
        print("Waiting 3 minutes before testing...")
        time.sleep(180)
    
    test_model()
EOL

chmod +x ~/llm-deployment-server/test_qwen.py

echo "Created test script at ~/llm-deployment-server/test_qwen.py"
echo "Wait a few minutes, then run: python ~/llm-deployment-server/test_qwen.py" 