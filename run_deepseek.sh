cat > ~/llm-deployment-server/run_deepseek.sh << 'EOL'
#!/bin/bash

# Create a clean virtual environment for deployment
echo "Creating virtual environment for model deployment..."
python -m venv ~/llm-deployment-server/llm_venv

# Activate the virtual environment
source ~/llm-deployment-server/llm_venv/bin/activate

# Install the required packages in the correct versions
echo "Installing dependencies with compatible versions..."
pip install torch torchvision
pip install transformers==4.45.0
pip install peft==0.5.0
pip install timm
pip install ms-swift

# Create deployment directory
echo "Creating deployment directory..."
mkdir -p ~/llm-deployment-server/deepseek-vl-7b

# Stop any existing processes on the port
echo "Checking for existing processes..."
if netstat -tuln | grep ":9089" > /dev/null; then
    echo "Stopping processes on port 9089..."
    fuser -k 9089/tcp
    sleep 5
fi

# Deploy DeepSeek-VL-7B-Chat on GPUs 4-7
echo "Deploying DeepSeek-VL-7B-Chat on GPUs 4-7..."
echo "Showing logs in real-time..."

CUDA_VISIBLE_DEVICES=4,5,6,7 \
swift deploy \
    --model deepseek-ai/deepseek-vl-7b-chat \
    --infer_backend pt \
    --port 9089 \
    --host 0.0.0.0

echo "Deployment process has completed."
echo "Model should be available at: http://localhost:9089/v1"
echo ""
echo "To exit the virtual environment when done, type 'deactivate'"
EOL

chmod +x ~/llm-deployment-server/run_deepseek.sh