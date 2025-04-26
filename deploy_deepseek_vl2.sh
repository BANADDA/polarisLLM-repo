#!/bin/bash

# Create a clean virtual environment for deployment
echo "Creating virtual environment for model deployment..."
python -m venv ~/llm-deployment-server/llm_venv

# Activate the virtual environment
source ~/llm-deployment-server/llm_venv/bin/activate

# Install the required packages in the correct versions
echo "Installing required dependencies..."
pip install torch torchvision
pip install timm
pip install transformers==4.36.2
pip install peft==0.15.0
pip install ms-swift

# Create deployment directory if it doesn't exist
mkdir -p ~/llm-deployment-server/deepseek-vl-7b

# Stop any existing deployment processes
echo "Checking for existing processes on port 9089..."
if netstat -tuln | grep ":9089" > /dev/null; then
    echo "Stopping existing processes on port 9089..."
    fuser -k 9089/tcp
    sleep 5
fi

# Deploy DeepSeek-VL-7B-Chat on GPUs 4-7 with nohup to keep it running when terminal closes
echo "Deploying DeepSeek-VL-7B-Chat on GPUs 4-7..."
CUDA_VISIBLE_DEVICES=4,5,6,7 \
nohup ~/llm-deployment-server/llm_venv/bin/python ~/llm-deployment-server/llm_venv/bin/swift deploy \
    --model deepseek-ai/deepseek-vl-7b-chat \
    --infer_backend pt \
    --port 9089 \
    --host 0.0.0.0 > ~/llm-deployment-server/deepseek-vl-7b/deploy.log 2>&1 &

# Get and display the process ID
DEPLOY_PID=$!
echo "DeepSeek-VL-7B-Chat deployment started on port 9089 with PID: $DEPLOY_PID"
echo "Deployment log can be found at: ~/llm-deployment-server/deepseek-vl-7b/deploy.log"
echo "The model will continue running even if you close this terminal."
echo ""
echo "You can monitor the deployment with:"
echo "  tail -f ~/llm-deployment-server/deepseek-vl-7b/deploy.log"
echo ""
echo "To test when the model is ready, run:"
echo "  python ~/llm-deployment-server/test_specific_image.py"
echo ""
echo "To check if the process is still running later:"
echo "  ps -p $DEPLOY_PID"

# Deactivate the virtual environment
deactivate