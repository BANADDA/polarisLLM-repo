#!/bin/bash

# Set up environment
echo "Setting up environment..."
pip install ms-swift -U

# Create deployment directories
mkdir -p ~/llm-deployment-server/qwen
mkdir -p ~/llm-deployment-server/deepseek-vl

# Deploy Qwen2.5-7B-Instruct on GPUs 0-3
echo "Deploying Qwen2.5-7B-Instruct on GPUs 0-3..."
CUDA_VISIBLE_DEVICES=0,1,2,3 \
swift deploy \
    --model Qwen/Qwen2.5-7B-Instruct \
    --infer_backend vllm \
    --max_model_len 8192 \
    --tensor_parallel_size 4 \
    --port 9088 \
    --host 0.0.0.0 &> ~/llm-deployment-server/qwen/deploy.log &

echo "Qwen2.5-7B-Instruct deployment started on port 9088"

# Deploy DeepSeek-VL2 on GPUs 4-7
echo "Deploying DeepSeek-VL2 on GPUs 4-7..."
CUDA_VISIBLE_DEVICES=4,5,6,7 \
swift deploy \
    --model deepseek-ai/deepseek-vl2 \
    --infer_backend vllm \
    --max_model_len 8192 \
    --tensor_parallel_size 4 \
    --port 9089 \
    --host 0.0.0.0 &> ~/llm-deployment-server/deepseek-vl/deploy.log &

echo "DeepSeek-VL2 deployment started on port 9089"

echo "Both models are now being deployed."
echo "Qwen2.5-7B-Instruct API available at: http://localhost:9088/v1"
echo "DeepSeek-VL2 API available at: http://localhost:9089/v1"
echo "You can use these endpoints with OpenAI-compatible clients."
echo "Check the log files in ~/llm-deployment-server/{qwen,deepseek-vl}/deploy.log for deployment progress."

# Add a simple test script
cat > ~/llm-deployment-server/test_deployment.py << 'EOL'
import requests
import json
import base64
import sys
import argparse

def test_text_model():
    print("Testing Qwen2.5-7B-Instruct...")
    url = "http://localhost:9088/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "user", "content": "What are the advantages of distributed LLM deployment?"}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("Success! Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_multimodal_model(image_path=None):
    print("Testing DeepSeek-VL2...")
    url = "http://localhost:9089/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Default image content if no image is provided
    image_content = ""
    if image_path:
        with open(image_path, "rb") as image_file:
            image_content = base64.b64encode(image_file.read()).decode('utf-8')
    else:
        print("No image provided, sending text-only query")
    
    # Prepare message with or without image
    if image_content:
        data = {
            "model": "deepseek-ai/deepseek-vl2",
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
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("Success! Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test LLM deployments")
    parser.add_argument("--model", choices=["text", "multimodal", "both"], default="both",
                        help="Which model to test (text, multimodal, or both)")
    parser.add_argument("--image", type=str, help="Path to an image file for testing the multimodal model")
    
    args = parser.parse_args()
    
    if args.model in ["text", "both"]:
        test_text_model()
        print("\n" + "-"*50 + "\n")
    
    if args.model in ["multimodal", "both"]:
        test_multimodal_model(args.image)
EOL

echo "Created test script at ~/llm-deployment-server/test_deployment.py"
echo "Run it with: python ~/llm-deployment-server/test_deployment.py"
echo "To test with an image: python ~/llm-deployment-server/test_deployment.py --model multimodal --image /path/to/image.jpg"