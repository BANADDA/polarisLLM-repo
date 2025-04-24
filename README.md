# PolarisLLM Deployment Server

A lightweight deployment server for running large language models with [Swift](https://github.com/modelscope/swift) and vLLM.

## Features

- Simple CLI for deploying and managing models
- Support for text and multimodal models (vision, audio, etc.)
- OpenAI-compatible endpoints
- Isolated environments for different models
- GPU acceleration with vLLM

## Requirements

- Docker with NVIDIA container toolkit
- Docker Compose
- NVIDIA GPU with sufficient VRAM (8GB+ recommended)

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/BANADDA/polarisLLM.git
   cd polarisLLM
   ```

2. Start the server:
   ```bash
   docker-compose up -d
   ```
   
   This will build the Docker image locally and start the server. 
   The first build may take some time as it downloads all dependencies.

## Usage

Once the server is running, you can use the following commands:

### List available models:
```bash
docker-compose exec polarisllm polarisLLM list models
```

### Deploy a model:
```bash
docker-compose exec polarisllm polarisLLM deploy Qwen/Qwen2-VL-7B-Instruct
```

Optional parameters:
```bash
docker-compose exec polarisllm polarisLLM deploy Qwen/Qwen2-VL-7B-Instruct --gpu 0 --max-len 4096 --port 8005
```

### List active deployments:
```bash
docker-compose exec polarisllm polarisLLM list deployments
```

### View deployment logs:
```bash
docker-compose exec polarisllm polarisLLM logs Qwen/Qwen2-VL-7B-Instruct
```

### Test a model:
```bash
# Text model
docker-compose exec polarisllm polarisLLM test text Qwen/Qwen2-VL-7B-Instruct

# Vision model (first copy an image into the container)
docker cp /path/to/image.jpg polarisllm:/tmp/image.jpg
docker-compose exec polarisllm polarisLLM test vision Qwen/Qwen2-VL-7B-Instruct /tmp/image.jpg
```

### Stop a deployment:
```bash
docker-compose exec polarisllm polarisLLM stop Qwen/Qwen2-VL-7B-Instruct
```

## API Usage

Each deployed model exposes an OpenAI-compatible API endpoint. For example, if you deploy a model on port 8001:

```bash
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "stream": false
  }'
```

## Customizing the Models

The available models are defined in `models_config.json`. You can modify this file to add or remove models.

## Troubleshooting

- If a model fails to deploy, check the logs with `polarisLLM logs <model_id>`
- For multimodal models, ensure you have the required dependencies in requirements.txt
- If you encounter CUDA out of memory errors, reduce the `--max-len` parameter or try a smaller model

## License

MIT
