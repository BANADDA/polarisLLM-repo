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
