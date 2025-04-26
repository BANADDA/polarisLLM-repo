import os
import json
import subprocess
import uvicorn
import random
import datetime
import socket
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import traceback
import shlex

# Initialize FastAPI app
app = FastAPI(title="Swift Model Deployment API")

# Load models config from JSON file
with open("models_config.json", "r") as f:
    models_config = json.load(f)

class DeployRequest(BaseModel):
    model_id: str
    gpu_id: int = 0
    max_model_len: Optional[int] = None
    vision_batch_size: Optional[int] = None
    gpu_memory_utilization: float = 0.9
    port: Optional[int] = None  # Make port optional
    isolate_env: bool = True    # New parameter to request isolated environment
    use_all_gpus: bool = True   # New parameter to use all available GPUs (default: True)
    architecture_override: Optional[str] = None  # New parameter to override model architecture
    tensor_parallel_size: Optional[int] = None   # New parameter for tensor parallelism

class DeploymentStatus(BaseModel):
    status: str
    model_id: str
    deployment_command: str
    log_file: str
    port: int
    gpu_id: int
    env_path: Optional[str] = None
    use_all_gpus: bool = False
    architecture_override: Optional[str] = None  # Field for architecture override
    tensor_parallel_size: Optional[int] = None   # Field for tensor parallelism

# Track deployments
active_deployments = {}

# Port range for model servers
MIN_PORT = 8001
MAX_PORT = 9999  # Expanded port range

def is_port_in_use(port):
    """Check if a port is in use on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(requested_port=None):
    """Find an available port for a new deployment.
    
    Args:
        requested_port: Optional port number requested by the user
        
    Returns:
        An available port number
    """
    # If user requested a specific port, check if it's available
    if requested_port:
        # Check if port is in active deployments
        for deployment in active_deployments.values():
            if deployment["port"] == requested_port:
                print(f"Port {requested_port} is already in use by another deployment")
                requested_port = None
                break
                
        # Check if port is in use on the system
        if requested_port and is_port_in_use(requested_port):
            print(f"Port {requested_port} is already in use on the system")
            requested_port = None
        
        # Return requested port if it's available
        if requested_port:
            return requested_port
    
    # Get currently used ports
    used_ports = set()
    for deployment in active_deployments.values():
        used_ports.add(deployment["port"])
    
    # Try a random approach first with 10 attempts
    for _ in range(10):
        # Pick a random port in our range
        port = random.randint(MIN_PORT, MAX_PORT)
        if port not in used_ports and not is_port_in_use(port):
            return port
    
    # If random approach fails, methodically try ports
    for port in range(MIN_PORT, MAX_PORT + 1):
        if port not in used_ports and not is_port_in_use(port):
            return port
    
    # If all ports are used, raise an error
    raise ValueError(f"No available ports in range {MIN_PORT}-{MAX_PORT}. Stop some deployments first.")

def find_model_config(model_id: str) -> Dict[str, Any]:
    """Find the model configuration by model_id"""
    # Search in multimodal models
    for category in models_config["multimodal_models"]:
        for model in models_config["multimodal_models"][category]:
            if model["model_id"] == model_id:
                model["is_multimodal"] = True
                return model
    
    # Search in text only models
    for category in models_config["text_only_models"]:
        for model in models_config["text_only_models"][category]:
            if model["model_id"] == model_id:
                model["is_multimodal"] = False
                return model
    
    raise ValueError(f"Model {model_id} not found in configuration")

def get_model_max_length(model_id: str) -> int:
    """Get the maximum sequence length for a model from its config file."""
    try:
        # Import here to avoid loading at startup
        from transformers import AutoConfig
        
        try:
            # Try to load config directly
            config = AutoConfig.from_pretrained(model_id)
            if hasattr(config, 'max_position_embeddings'):
                return config.max_position_embeddings
            elif hasattr(config, 'max_sequence_length'):
                return config.max_sequence_length
            elif hasattr(config, 'seq_length'):
                return config.seq_length
            elif hasattr(config, 'n_positions'):
                return config.n_positions
            
            # If no sequence length found, use default fallback value
            print(f"Warning: Could not determine max sequence length for {model_id}. Using default.")
            return 2048  # Safe default
        except Exception as e:
            print(f"Error loading model config: {e}")
            return 2048  # Safe default 
    except Exception as e:
        print(f"Error determining model max length: {e}")
        return 2048  # Safe default

def create_virtual_environment(model_id: str, requires: str) -> str:
    """Create a virtual environment for a model with its requirements."""
    # Create a sanitized model ID for the venv name
    env_name = f"env_{model_id.replace('/', '_').replace('-', '_').lower()}"
    env_path = f"/app/envs/{env_name}"
    
    try:
        # Ensure the base directory exists
        print(f"Ensuring base envs directory exists: /app/envs")
        os.makedirs("/app/envs", exist_ok=True)
        print(f"Base envs directory confirmed.")

        # First, try to create virtual environment with system packages
        print(f"Attempting venv creation for {model_id} at {env_path} using python -m venv...")
        try:
            # Use --system-site-packages to inherit the container's packages
            # Capture stderr to diagnose failures
            print("Running: python -m venv...")
            result = subprocess.run(
                f"python -m venv --system-site-packages {env_path}",
                shell=True,
                check=True,
                capture_output=True, # Capture stdout/stderr
                text=True           # Decode as text
            )
            print(f"Venv creation stdout (python -m venv):\n{result.stdout}")
            print("Completed: python -m venv.")
        except subprocess.CalledProcessError as e:
            print(f"Failed venv creation with python -m venv. Stderr:\n{e.stderr}")
            print(f"Attempting with python3.10 -m venv...")
            # Try with explicit Python version if first attempt fails
            # Capture stderr to diagnose failures
            print("Running: python3.10 -m venv...")
            result = subprocess.run(
                f"python3.10 -m venv --system-site-packages {env_path}",
                shell=True,
                check=True,
                capture_output=True, # Capture stdout/stderr
                text=True           # Decode as text
            )
            print(f"Venv creation stdout (python3.10):\n{result.stdout}")
            print("Completed: python3.10 -m venv.")

        # Install pip and wheel in the venv
        # Capture stderr to diagnose failures
        print("Running: pip install --upgrade pip wheel...")
        result = subprocess.run(
            f"{env_path}/bin/pip install --upgrade pip wheel",
            shell=True,
            check=True,
            capture_output=True, # Capture stdout/stderr
            text=True           # Decode as text
        )
        print(f"pip/wheel install stdout:\n{result.stdout}")
        print("Completed: pip install --upgrade pip wheel.")
        
        # Process the requirements
        if requires and requires != "-":
            print(f"Processing requirements: {requires}")
            
            # Use a more robust approach to parse the requirements
            # Handle quoted strings and special flags like -U
            processed_requires = []
            
            # Simple parsing of quoted strings and flags
            try:
                req_parts = shlex.split(requires)
                print(f"Requirements after parsing: {req_parts}")
                
                # Extract upgrade flag if present
                upgrade_flag = ""
                if "-U" in req_parts:
                    upgrade_flag = " -U"
                    req_parts.remove("-U")
                elif "--upgrade" in req_parts:
                    upgrade_flag = " --upgrade"
                    req_parts.remove("--upgrade")
                
                # Build the requirements string, preserving quotes for package names with version constraints
                if req_parts:
                    req_string = " ".join(req_parts) + upgrade_flag
                    print(f"Installing requirements: {req_string}")
                    
                    # Install processed requirements
                    # Capture stderr to diagnose failures
                    print(f"Running: pip install {req_string}...")
                    result = subprocess.run(
                        f"{env_path}/bin/pip install {req_string}",
                        shell=True,
                        check=True,
                        capture_output=True, # Capture stdout/stderr
                        text=True           # Decode as text
                    )
                    print(f"Requirements install stdout:\n{result.stdout}")
                    print(f"Completed: pip install {req_string}.")
                else:
                    print("No requirements to install after parsing.")
            except Exception as e:
                print(f"Error parsing requirements: {e}")
                print("Falling back to simple space-splitting")
                
                # Fallback to simple space-splitting if shlex fails
                processed_requires = requires.split()
                if processed_requires:
                    req_string = ' '.join(processed_requires)
                    print(f"Installing requirements (fallback method): {req_string}")
                    result = subprocess.run(
                        f"{env_path}/bin/pip install {req_string}",
                        shell=True,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print(f"Requirements install stdout (fallback):\n{result.stdout}")
        else:
            print("No requirements specified for this model.")
        
        print(f"Successfully created virtual environment for {model_id} at {env_path}")
        return env_path
    
    except subprocess.CalledProcessError as e: # Catch errors from venv/pip subprocess calls
        print(f"ERROR: Subprocess failed during virtual environment setup.")
        print(f"Command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"Stderr:\n{e.stderr}")
        print(f"Stdout:\n{e.stdout}") # Also print stdout for context
        print("Falling back to system Python.")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected exception during virtual environment creation for {model_id}.")
        # Print the full traceback for unexpected errors
        traceback.print_exc()
        print("Falling back to system Python.")
        return None

def deploy_model_task(model_id: str, gpu_id: int, max_model_len: Optional[int], 
                     vision_batch_size: Optional[int], gpu_memory_utilization: float,
                     port: int, isolate_env: bool, use_all_gpus: bool = False,
                     architecture_override: Optional[str] = None,
                     tensor_parallel_size: Optional[int] = None) -> None:
    """Background task to deploy the model"""
    # Create log file first so it exists even if there's an early failure
    log_file = f"deployment_{model_id.replace('/', '_')}_{port}.log"
    env_path = None
    
    # Store deployment information immediately so it's visible even during deployment
    # Start with status "deploying"
    active_deployments[model_id] = {
        "process": None,
        "command": "",
        "log_file": log_file,
        "port": port,
        "gpu_id": gpu_id,
        "env_path": None,
        "status": "deploying",
        "use_all_gpus": use_all_gpus,
        "architecture_override": architecture_override,
        "tensor_parallel_size": tensor_parallel_size
    }
    
    try:
        with open(log_file, "w") as f:
            f.write(f"Starting deployment for {model_id} on port {port}\n")
            f.write(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if use_all_gpus:
                f.write(f"Using all available GPUs\n")
                if tensor_parallel_size:
                    f.write(f"Tensor parallel size: {tensor_parallel_size}\n")
            else:
                f.write(f"GPU ID: {gpu_id}\n")
            f.write(f"Isolated environment: {isolate_env}\n\n")
        
        # Find model configuration
        model_config = find_model_config(model_id)
        requires = model_config.get("requires", "-")
        
        with open(log_file, "a") as f:
            f.write(f"Model configuration found. Requirements: {requires}\n")
        
        # Removed special case handling block for deepseek-vl2
        special_case = False # Ensure special_case is always False now
        python_cmd = "python" # Default to system python initially

        # Create isolated environment if requested
        if isolate_env:
            try:
                env_path = create_virtual_environment(model_id, requires)
                if env_path:
                    python_cmd = f"{env_path}/bin/python"
                    with open(log_file, "a") as f:
                        f.write(f"Created isolated environment at {env_path}\n")
                    
                    # Update deployment record with environment path
                    active_deployments[model_id]["env_path"] = env_path
                else:
                    # Fallback to system Python if venv creation failed
                    python_cmd = "python"
                    with open(log_file, "a") as f:
                        f.write("Failed to create virtual environment. Falling back to system Python.\n")
            except Exception as e:
                with open(log_file, "a") as f:
                    f.write(f"Error creating virtual environment: {str(e)}\n")
                    f.write("Falling back to system Python\n")
                python_cmd = "python"
        else:
            # Use system python
            python_cmd = "python"
            with open(log_file, "a") as f:
                f.write("Using system Python environment\n")
        
        # Determine if model is from HuggingFace
        use_hf = not model_id.startswith(("Qwen/", "modelscope/", "damo/", "iic/", "AI-ModelScope/"))
        
        # Get model's max length from config
        try:
            model_max_length = get_model_max_length(model_id)
            with open(log_file, "a") as f:
                f.write(f"Detected model max length: {model_max_length}\n")
        except Exception as e:
            model_max_length = 2048
            with open(log_file, "a") as f:
                f.write(f"Error detecting model max length: {str(e)}\n")
                f.write(f"Using default max length: {model_max_length}\n")
        
        # Set default max_model_len if not provided or ensure it doesn't exceed model's capability
        if max_model_len is None:
            # Use a safe default based on whether it's multimodal
            default_len = min(2048, model_max_length) if model_config["is_multimodal"] else min(4096, model_max_length)
            max_model_len = default_len
            with open(log_file, "a") as f:
                f.write(f"Using default max model length: {max_model_len}\n")
        else:
            # Ensure max_model_len doesn't exceed model's capabilities
            if max_model_len > model_max_length:
                with open(log_file, "a") as f:
                    f.write(f"Warning: Requested max_model_len ({max_model_len}) exceeds model's maximum ({model_max_length}). Using {model_max_length} instead.\n")
                max_model_len = model_max_length
        
        # Build command - use swift deploy directly
        # Add VLLM_USE_V1=0 for multimodal models to fix compatibility issues
        if use_all_gpus:
            if tensor_parallel_size:
                # Use specific tensor parallel size
                with open(log_file, "a") as f:
                    f.write(f"Setting tensor parallel size to {tensor_parallel_size}\n")
                env_vars = []  # Don't set CUDA_VISIBLE_DEVICES to use specified tensor parallel size
            else:
                # Try to detect number of GPUs for tensor parallelism
                try:
                    import subprocess
                    gpu_count_result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                                       capture_output=True, text=True)
                    available_gpus = len(gpu_count_result.stdout.strip().split('\n'))
                    tensor_parallel_size = available_gpus
                    with open(log_file, "a") as f:
                        f.write(f"Auto-detected {available_gpus} GPUs for tensor parallelism\n")
                    env_vars = []
                except Exception as e:
                    with open(log_file, "a") as f:
                        f.write(f"Error detecting GPU count: {str(e)}\n")
                        f.write(f"Using default CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7\n")
                    env_vars = ["CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7"]
        else:
            env_vars = [f"CUDA_VISIBLE_DEVICES={gpu_id}"]
            
        # Add PyTorch CUDA allocation configuration for large models
        if tensor_parallel_size and tensor_parallel_size > 1:
            env_vars.append("PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True")
            
        if model_config["is_multimodal"]:
            env_vars.append("VLLM_USE_V1=0")
            
        cmd = [
            " ".join(env_vars),  # Join all environment variables
            "swift deploy",  # Use swift deploy directly
            "--model", model_id,
            "--infer_backend", "vllm",
            "--max_model_len", str(max_model_len),
            "--gpu_memory_utilization", str(gpu_memory_utilization),
            "--port", str(port),
            "--host", "0.0.0.0"  # Ensure accessible from outside container
        ]
        
        # Add tensor parallelism if specified
        if tensor_parallel_size and tensor_parallel_size > 1:
            cmd.extend(["--tensor-parallel-size", str(tensor_parallel_size)])
            with open(log_file, "a") as f:
                f.write(f"Using tensor parallel size: {tensor_parallel_size}\n")
        
        # Add architecture_override if provided
        if architecture_override:
            cmd.extend(["--hf-overrides", f'{{"architectures": ["{architecture_override}"]}}'])
            with open(log_file, "a") as f:
                f.write(f"Using architecture override: {architecture_override}\n")
        
        # Add vision_batch_size for multimodal models
        if model_config["is_multimodal"]:
            if vision_batch_size is None:
                vision_batch_size = 2
            cmd.extend(["--vision_batch_size", str(vision_batch_size)])
        
        # Add use_hf flag if needed
        if use_hf:
            cmd.extend(["--use_hf", "true"])
        
        # Execute deployment command
        cmd_str = " ".join(cmd)
        with open(log_file, "a") as f:
            f.write(f"Executing: {cmd_str}\n\n")
            f.write("=== Deployment Output ===\n\n")
            
            # Update deployment command in record
            active_deployments[model_id]["command"] = cmd_str
            
            deployment_process = subprocess.Popen(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Store deployment process in record
            active_deployments[model_id]["process"] = deployment_process
            
            # Stream output to log file
            for line in deployment_process.stdout:
                f.write(line)
                f.flush()
            
            # Wait for process to complete if it's a fast failure
            return_code = deployment_process.wait()
            
            # Update deployment status based on return code
            if return_code != 0:
                f.write(f"\nProcess exited with code {return_code}\n")
                f.write("Deployment failed. Check error messages above.\n")
                active_deployments[model_id]["status"] = "failed"
            else:
                f.write(f"\nProcess exited with code {return_code}\n")
                f.write("Deployment completed successfully.\n")
                active_deployments[model_id]["status"] = "completed"
        
    except Exception as e:
        error_msg = f"Error deploying model {model_id}: {str(e)}"
        print(error_msg)
        
        # Write error to log even if something went wrong
        try:
            with open(log_file, "a") as f:
                f.write(f"\n\nERROR: {error_msg}\n")
        except:
            pass
            
        # Update deployment status to failed
        if model_id in active_deployments:
            active_deployments[model_id]["status"] = "failed"
            
def install_requirements(model_id: str) -> None:
    """Install required packages for the model - now only used for system-wide installation"""
    try:
        model_config = find_model_config(model_id)
        requires = model_config.get("requires", "-")
        
        if requires != "-" and requires:
            # Log the requirements
            print(f"Model requirements for {model_id}: {requires}")
        
    except Exception as e:
        print(f"Error processing requirements for {model_id}: {str(e)}")
        raise

@app.post("/deploy", response_model=DeploymentStatus)
async def deploy_model(deploy_request: DeployRequest, background_tasks: BackgroundTasks):
    """Deploy a model with the specified parameters"""
    try:
        model_id = deploy_request.model_id
        
        # Check if model is already deployed
        if model_id in active_deployments:
            return DeploymentStatus(
                status="already_deployed",
                model_id=model_id,
                deployment_command=active_deployments[model_id]["command"],
                log_file=active_deployments[model_id]["log_file"],
                port=active_deployments[model_id]["port"],
                gpu_id=active_deployments[model_id]["gpu_id"],
                env_path=active_deployments[model_id].get("env_path"),
                use_all_gpus=active_deployments[model_id].get("use_all_gpus", False),
                architecture_override=active_deployments[model_id].get("architecture_override"),
                tensor_parallel_size=active_deployments[model_id].get("tensor_parallel_size")
            )
        
        # Find model in config
        model_config = find_model_config(model_id)
        
        # Select port - either user-specified or auto-assigned
        requested_port = deploy_request.port
        try:
            port = find_available_port(requested_port)
            # Log if we had to change the port
            if requested_port and port != requested_port:
                print(f"Requested port {requested_port} was unavailable. Using port {port} instead.")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        # Start deployment in background
        background_tasks.add_task(
            deploy_model_task,
            model_id=model_id,
            gpu_id=deploy_request.gpu_id,
            max_model_len=deploy_request.max_model_len,
            vision_batch_size=deploy_request.vision_batch_size,
            gpu_memory_utilization=deploy_request.gpu_memory_utilization,
            port=port,
            isolate_env=deploy_request.isolate_env,
            use_all_gpus=deploy_request.use_all_gpus,
            architecture_override=deploy_request.architecture_override,
            tensor_parallel_size=deploy_request.tensor_parallel_size
        )
        
        # Build the command for display
        if deploy_request.use_all_gpus:
            if deploy_request.tensor_parallel_size:
                env_vars = []  # Don't set CUDA_VISIBLE_DEVICES 
            else:
                env_vars = ["CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7"]  # Default to 8 GPUs
        else:
            env_vars = [f"CUDA_VISIBLE_DEVICES={deploy_request.gpu_id}"]
        
        # Add PyTorch CUDA allocation configuration for large models
        if deploy_request.tensor_parallel_size and deploy_request.tensor_parallel_size > 1:
            env_vars.append("PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True")
        
        # Add VLLM_USE_V1=0 for multimodal models
        if model_config["is_multimodal"]:
            env_vars.append("VLLM_USE_V1=0")
        
        cmd_parts = [
            " ".join(env_vars),
            "swift deploy",
            "--model", model_id,
            "--infer_backend", "vllm",
            "--max_model_len", str(deploy_request.max_model_len or (2048 if model_config["is_multimodal"] else 4096)),
            "--gpu_memory_utilization", str(deploy_request.gpu_memory_utilization),
            "--port", str(port),
            "--host", "0.0.0.0"  # Ensure the model server accepts connections from all interfaces
        ]
        
        # Add tensor parallelism if specified
        if deploy_request.tensor_parallel_size and deploy_request.tensor_parallel_size > 1:
            cmd_parts.extend(["--tensor-parallel-size", str(deploy_request.tensor_parallel_size)])
        
        # Add architecture_override if provided
        if deploy_request.architecture_override:
            cmd_parts.extend(["--hf-overrides", f'{{"architectures": ["{deploy_request.architecture_override}"]}}'])
        
        if model_config["is_multimodal"]:
            cmd_parts.extend(["--vision_batch_size", str(deploy_request.vision_batch_size or 2)])
            
        # Determine if model is from HuggingFace
        use_hf = not model_id.startswith(("Qwen/", "modelscope/", "damo/", "iic/", "AI-ModelScope/"))
        if use_hf:
            cmd_parts.extend(["--use_hf", "true"])
        
        command = " ".join(cmd_parts)
        log_file = f"deployment_{model_id.replace('/', '_')}_{port}.log"
        
        return DeploymentStatus(
            status="deploying",
            model_id=model_id,
            deployment_command=command,
            log_file=log_file,
            port=port,
            gpu_id=deploy_request.gpu_id,
            use_all_gpus=deploy_request.use_all_gpus,
            architecture_override=deploy_request.architecture_override,
            tensor_parallel_size=deploy_request.tensor_parallel_size
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment error: {str(e)}")

@app.get("/deployments")
async def get_deployments():
    """Get all active deployments"""
    result = []
    for model_id, deployment in active_deployments.items():
        # If process exists, check its status; otherwise use stored status
        status = deployment.get("status", "unknown")
        if deployment.get("process") is not None:
            if deployment["process"].poll() is None:
                status = "running"
            elif status == "deploying":  # Only update if it was previously "deploying"
                status = f"exited (code: {deployment['process'].returncode})"
                
        result.append({
            "status": status,
            "model_id": model_id,
            "deployment_command": deployment["command"],
            "log_file": deployment["log_file"],
            "port": deployment["port"],
            "gpu_id": deployment["gpu_id"],
            "env_path": deployment.get("env_path"),
            "use_all_gpus": deployment.get("use_all_gpus", False),
            "architecture_override": deployment.get("architecture_override"),
            "tensor_parallel_size": deployment.get("tensor_parallel_size")
        })
    
    return result

@app.delete("/deployments/{model_id}")
async def stop_deployment(model_id: str):
    """Stop a running deployment"""
    if model_id not in active_deployments:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found in active deployments")
    
    try:
        # Terminate the process
        deployment = active_deployments[model_id]
        if deployment["process"].poll() is None:
            deployment["process"].terminate()
            deployment["process"].wait(timeout=30)
        
        # Remove from active deployments
        del active_deployments[model_id]
        
        return {"status": "stopped", "model_id": model_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping deployment: {str(e)}")

@app.get("/models", response_model=List[Dict[str, Any]])
async def list_models():
    """List all available models with enhanced metadata"""
    all_models = []
    
    # Add multimodal models
    for category in models_config["multimodal_models"]:
        for model in models_config["multimodal_models"][category]:
            model_copy = model.copy()
            model_copy["category"] = category
            model_copy["is_multimodal"] = True
            # Add family information
            model_copy["family"] = category
            all_models.append(model_copy)
    
    # Add text only models
    for category in models_config["text_only_models"]:
        for model in models_config["text_only_models"][category]:
            model_copy = model.copy()
            model_copy["category"] = category
            model_copy["is_multimodal"] = False
            # Add family information
            model_copy["family"] = category
            all_models.append(model_copy)
    
    return all_models

@app.get("/")
async def root():
    return {
        "name": "Swift Model Deployment API",
        "version": "1.0.0",
        "endpoints": [
            "/deploy - Deploy a model",
            "/deployments - List active deployments",
            "/deployments/{model_id} - Stop a deployment",
            "/models - List all available models"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1009)