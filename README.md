# PolarisLLM Server Components

This directory contains the core components of the PolarisLLM deployment server.

## Important Files

- `api.py` - FastAPI server for model deployment management
- `polarisLLM.py` - Command-line client for interacting with the API
- `models_config.json` - Configuration of available models
- `Dockerfile` - Container definition
- `start_server.sh` - Container startup script
- `setup.sh` - Installation and configuration script

## Installation

First, clone the repository:
```bash
git clone https://github.com/BANADDA/polarisLLM-repo.git
cd polarisLLM-repo
```

Then, run the setup script:
```bash
./setup.sh
```

**DO NOT** run the components in this directory directly. Always use the setup script.

The setup script will:
1. Configure the Docker environment properly
2. Set up required directories
3. Start the container with appropriate settings
4. Provide usage instructions

## Development

If you're developing or modifying these components:

1. Make your changes to the relevant files
2. Stop any running containers with `docker-compose down`
3. Run the setup script again to rebuild and restart

## Documentation

For full documentation on using the PolarisLLM deployment server, refer to the README.md file in the parent directory.

## Proxy Server (proxy_server.py)

This directory also contains `proxy_server.py`, a Flask-based proxy server that can act as a single entry point for multiple underlying LLM API servers.

### Purpose

- **Routing:** Directs incoming requests (e.g., to `/v1/chat/completions`) to the appropriate backend LLM server based on the `model` field in the request body.
- **Logging:** Logs details of incoming requests and responses.
- **Unified Endpoint:** Provides a single URL for clients to interact with multiple different models.

### Running for Development (Simple)

For basic testing, you can run the server directly using Flask's built-in development server:

```bash
# Ensure any process using port 8989 is stopped first
# sudo lsof -t -i:8989 | xargs --no-run-if-empty sudo kill -9

python proxy_server.py
```

**Note:** This method is NOT recommended for production or concurrent use as it handles requests sequentially.

### Running for Production/Concurrency (Recommended)

To handle multiple requests concurrently and run the server reliably in the background, use a production WSGI server like Gunicorn managed by `systemd`.

**1. Install Gunicorn:**
```bash
pip install gunicorn
```

**2. Create systemd Service File:**
Create a file named `/etc/systemd/system/llm_proxy.service` using `sudo nano` or another editor with `sudo`:
```ini
[Unit]
Description=Gunicorn instance to serve LLM Proxy
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/llm-deployment-server/polarisLLM-repo # <-- IMPORTANT: Update if your path is different
ExecStart=/usr/bin/python -m gunicorn -w 4 -b 0.0.0.0:8989 proxy_server:app
Restart=always

[Install]
WantedBy=multi-user.target
```
*(Ensure `User`, `Group`, `WorkingDirectory`, and the python path in `ExecStart` match your system setup.)*

**3. Manage the Service:**
```bash
# Ensure port 8989 is free
sudo lsof -t -i:8989 | xargs --no-run-if-empty sudo kill -9

# Reload systemd to recognize the new file
sudo systemctl daemon-reload

# Start the service
sudo systemctl start llm_proxy.service

# Enable the service to start on boot
sudo systemctl enable llm_proxy.service

# Check the status
sudo systemctl status llm_proxy.service

# View logs (if not redirected to journald)
# Logs from the python logging module will still go to proxy_requests.log
# Gunicorn logs (startup, errors) can be viewed with:
sudo journalctl -u llm_proxy.service -f

# Stop the service
sudo systemctl stop llm_proxy.service
```

### Testing Scripts

Several Python scripts are included for testing the proxy and models:
- `test_text_model.py`: Tests text models (e.g., Qwen).
- `test_image_model.py`: Tests multimodal models (e.g., DeepSeek-VL) with images.
- `test_streaming.py`: Demonstrates streaming responses for text models.
- `test_image_streaming.py`: Demonstrates streaming responses for multimodal models.
- `chain_models.py`: Demonstrates chaining the vision and language models.
- `agent_simulation.py`: Demonstrates a Planner-Executor agent simulation.

Remember to update the target URLs (`--url`) in these scripts to point to your proxy endpoint (`http://localhost:8989` or your `localtunnel` URL).
