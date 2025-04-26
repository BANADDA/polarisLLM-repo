# Save the script
cat > ~/llm-deployment-server/deploy_deepseek_pt.sh << 'EOL'
#!/bin/bash

# Create deployment directory if it doesn't exist
mkdir -p ~/llm-deployment-server/deepseek-vl

# Stop any existing deployment processes
echo "Checking for existing DeepSeek-VL2 processes..."
if pgrep -f "deepseek-ai/deepseek-vl2" > /dev/null; then
    echo "Stopping existing DeepSeek-VL2 processes..."
    pkill -f "deepseek-ai/deepseek-vl2"
    sleep 5
fi

# Deploy DeepSeek-VL2 on GPUs 4-7 using PyTorch backend instead of vLLM
echo "Deploying DeepSeek-VL2 on GPUs 4-7 with PyTorch backend..."
CUDA_VISIBLE_DEVICES=4,5,6,7 \
swift deploy \
    --model deepseek-ai/deepseek-vl2 \
    --infer_backend pt \
    --port 9089 \
    --host 0.0.0.0 &> ~/llm-deployment-server/deepseek-vl/deploy.log &

echo "DeepSeek-VL2 deployment started on port 9089 with PyTorch backend"
echo "Deployment log can be found at: ~/llm-deployment-server/deepseek-vl/deploy.log"
echo "The model may take several minutes to load completely."
echo ""
echo "You can monitor the deployment with:"
echo "  tail -f ~/llm-deployment-server/deepseek-vl/deploy.log"
echo ""
echo "To test when the model is ready, run:"
echo "  python ~/llm-deployment-server/test_image_model.py"
EOL

# Make the script executable
chmod +x ~/llm-deployment-server/deploy_deepseek_pt.sh