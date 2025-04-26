#!/bin/bash

# Kill any existing localtunnel processes
pkill -f "pylt port"

# Start tunnel for the text model (Qwen)
nohup pylt port 9088 -s qwen-llm > ~/llm-deployment-server/qwen-tunnel.log 2>&1 &
QWEN_TUNNEL_PID=$!
echo "Started tunnel for Qwen model with PID: $QWEN_TUNNEL_PID"

# Start tunnel for the multimodal model (DeepSeek)
nohup pylt port 9089 -s deepseek-vl > ~/llm-deployment-server/deepseek-tunnel.log 2>&1 &
DEEPSEEK_TUNNEL_PID=$!
echo "Started tunnel for DeepSeek model with PID: $DEEPSEEK_TUNNEL_PID"

# Display tunnel URLs (wait a moment for them to start)
sleep 5
echo "Checking tunnel logs for URLs..."
echo "Qwen Text Model URL:"
grep -o "https://.*" ~/llm-deployment-server/qwen-tunnel.log | head -1
echo "DeepSeek Vision Model URL:"
grep -o "https://.*" ~/llm-deployment-server/deepseek-tunnel.log | head -1

echo "To check tunnel status later:"
echo "  cat ~/llm-deployment-server/qwen-tunnel.log"
echo "  cat ~/llm-deployment-server/deepseek-tunnel.log" 