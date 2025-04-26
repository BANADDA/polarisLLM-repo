#!/bin/bash

# Check if GPU count for Qwen is provided
if [ "$1" == "--qwen-gpus" ] && ([ "$2" == "1" ] || [ "$2" == "4" ]); then
    QWEN_GPU_COUNT=$2
    echo "Configuring Qwen deployment for $QWEN_GPU_COUNT GPU(s)."
    shift 2 # Remove --qwen-gpus and the count from arguments
elif [ "$1" == "--qwen-gpus" ]; then
    echo "Error: Invalid GPU count for --qwen-gpus. Please specify 1 or 4."
    exit 1
else
    # Default to 4 GPUs if not specified
    echo "Defaulting Qwen deployment to 4 GPUs. Use --qwen-gpus [1|4] to specify."
    QWEN_GPU_COUNT=4
fi

# Set up environment
echo "Setting up environment..."
pip install ms-swift -U

# Deploy Qwen using the dedicated script
echo "Starting Qwen deployment using deploy_qwen_multi_gpu.sh..."
bash /home/ubuntu/llm-deployment-server/deploy_qwen_multi_gpu.sh $QWEN_GPU_COUNT

# Wait a moment for the deployment script to output initial info
sleep 3

# --- DeepSeek VL Deployment (Currently commented out) ---
# Create deployment directory
# mkdir -p /home/ubuntu/llm-deployment-server/deepseek-vl
# Deploy DeepSeek-VL2 on GPUs 4-7
# echo "Deploying DeepSeek-VL2 on GPUs 4-7..."
# CUDA_VISIBLE_DEVICES=4,5,6,7 \
# swift deploy \
#     --model deepseek-ai/deepseek-vl2 \
#     --infer_backend vllm \
#     --max_model_len 8192 \
#     --tensor_parallel_size 4 \
#     --port 9089 \
#     --host 0.0.0.0 &> /home/ubuntu/llm-deployment-server/deepseek-vl/deploy.log &
# echo "DeepSeek-VL2 deployment started on port 9089"
# echo "DeepSeek-VL2 API available at: http://localhost:9089/v1"
# --------------------------------------------------------

# --- Test Script Generation --- 
echo "Generating test script..."
# Add a simple test script (Note: this tests Qwen on port 1088)
cat > /home/ubuntu/llm-deployment-server/test_deployment.py << 'EOL'
import requests
import json
import base64
import sys
import argparse
import time # Added for polling

def poll_model(url, timeout=300, interval=15):
    """Poll the model API until it's ready or timeout."""
    print(f"Polling {url} for readiness (timeout: {timeout}s)...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("\n✅ Model API is available!")
                print(f"Models: {response.json()}")
                return True
            else:
                print(f". (Status: {response.status_code})", end='', flush=True)
        except requests.exceptions.RequestException as e:
            print(f". (Error: {e})", end='', flush=True)
        time.sleep(interval)
    print("\n❌ Model API did not become available within the timeout.")
    return False

def test_text_model():
    print("Testing Qwen2.5-7B-Instruct...")
    model_url = "http://localhost:1088/v1/models"
    if not poll_model(model_url):
        return
        
    url = "http://localhost:1088/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": "Qwen/Qwen2.5-7B-Instruct", # Make sure model name matches deployment
        "messages": [
            {"role": "user", "content": "What are the advantages of distributed LLM deployment?"}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            print("\nSuccess! Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"\nRequest Error: {e}")

# --- Multimodal test function (Currently points to non-deployed port 9089) ---
def test_multimodal_model(image_path=None):
    print("Testing DeepSeek-VL2 (Note: Not deployed by default)...")
    model_url = "http://localhost:9089/v1/models"
    # if not poll_model(model_url): # Uncomment if deploying DeepSeek
    #     return
        
    url = "http://localhost:9089/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Default image content if no image is provided
    image_content = ""
    if image_path:
        try:
            with open(image_path, "rb") as image_file:
                image_content = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading image {image_path}: {e}")
            return
    else:
        print("No image provided, sending text-only query")
    
    # Prepare message with or without image
    if image_content:
        data = {
            "model": "deepseek-ai/deepseek-vl2", # Model name might need adjustment
            "messages": [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "What do you see in this image?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}}
                    ]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
    else:
        data = {
            "model": "deepseek-ai/deepseek-vl2",
            "messages": [
                {"role": "user", "content": "What capabilities do you have for processing images?"}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            print("\nSuccess! Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"\nRequest Error: {e}")
# ----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test LLM deployments")
    parser.add_argument("--model", choices=["text", "multimodal", "both"], default="text",
                        help="Which model to test (text, multimodal, or both)")
    parser.add_argument("--image", type=str, help="Path to an image file for testing the multimodal model")
    
    args = parser.parse_args()
    
    if args.model in ["text", "both"]:
        test_text_model()
        
    if args.model in ["multimodal", "both"]:
        print("\n" + "-"*50 + "\n")
        test_multimodal_model(args.image)
EOL

chmod +x /home/ubuntu/llm-deployment-server/test_deployment.py
echo "Created test script at /home/ubuntu/llm-deployment-server/test_deployment.py"
echo "Usage: ./deploy_models.sh [--qwen-gpus 1|4]"
echo "Run the test script after waiting a few minutes: python /home/ubuntu/llm-deployment-server/test_deployment.py"