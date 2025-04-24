#!/usr/bin/env python3
import sys
import os
import json
import requests
import subprocess
from tabulate import tabulate  # Add tabulate dependency

API_URL = "http://localhost:8020"

def load_models_from_file():
    """Load models from the config file"""
    try:
        with open('models_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading models: {e}")
        return {}

def list_models():
    """List all available models with detailed formatting"""
    try:
        # First try to get models from API
        response = requests.get(f"{API_URL}/models")
        response.raise_for_status()
        models = response.json()
        
        # Group models by family and type
        multimodal_families = {}
        text_families = {}
        
        # Try to load family information
        try:
            config = load_models_from_file()
            # Add family information if available
            models = add_family_info(models, config)
        except Exception as e:
            # Continue without family grouping if config can't be loaded
            pass
        
        # Group models by family and type
        for model in models:
            family_raw = model.get('family', model.get('category', ''))
            family = family_raw.replace('_models', '').capitalize() if family_raw else 'Other'
            
            # Check if model is multimodal
            is_multimodal = model.get('is_multimodal', False)
            
            if is_multimodal:
                if family not in multimodal_families:
                    multimodal_families[family] = []
                multimodal_families[family].append(model)
            else:
                if family not in text_families:
                    text_families[family] = []
                text_families[family].append(model)
        
        print("\n=== Available Models ===\n")
        
        # Display multimodal models
        if multimodal_families:
            print("=== MULTIMODAL MODELS ===\n")
            for family, family_models in multimodal_families.items():
                print(f"{family} Family:")
                
                headers = ["Name", "Type", "Parameters", "Model ID"]
                table_data = []
                
                for model in family_models:
                    name = model.get('name', model.get('id', 'Unknown'))
                    model_id = model.get('model_id', 'Unknown')
                    params = model.get('parameters', 'Unknown')
                    model_type = model.get('type', 'Unknown')
                    table_data.append([name, model_type, params, model_id])
                
                print(tabulate(table_data, headers=headers, tablefmt="pretty"))
                print()
        
        # Display text-only models
        if text_families:
            print("=== TEXT-ONLY MODELS ===\n")
            for family, family_models in text_families.items():
                print(f"{family} Family:")
                
                headers = ["Name", "Type", "Parameters", "Model ID"]
                table_data = []
                
                for model in family_models:
                    name = model.get('name', model.get('id', 'Unknown'))
                    model_id = model.get('model_id', 'Unknown')
                    params = model.get('parameters', 'Unknown')
                    model_type = model.get('type', 'Unknown')
                    table_data.append([name, model_type, params, model_id])
                
                print(tabulate(table_data, headers=headers, tablefmt="pretty"))
                print()
                
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Try to load from file as fallback
        print("Attempting to load models from config file...")
        config = load_models_from_file()
        if config:
            display_models_from_config(config)
        else:
            print("No models found.")

def add_family_info(models, config):
    """Add family information to models based on config file"""
    model_to_family = {}
    
    # Create mapping from model_id to family
    for category in ['multimodal_models', 'text_only_models']:
        if category in config:
            for family, family_models in config[category].items():
                for model in family_models:
                    model_id = model.get('model_id')
                    if model_id:
                        model_to_family[model_id] = family
    
    # Add family info to each model
    for model in models:
        model_id = model.get('model_id')
        if model_id in model_to_family:
            model['family'] = model_to_family[model_id]
    
    return models

def display_models_from_config(config):
    """Display models directly from config file with proper organization"""
    print("\n=== Available Models ===\n")
    
    # Process multimodal models
    if 'multimodal_models' in config:
        print("=== MULTIMODAL MODELS ===\n")
        for family, models in config['multimodal_models'].items():
            if not models:  # Skip empty families
                continue
                
            family_name = family.replace('_models', '').capitalize()
            print(f"{family_name} Family:")
            
            headers = ["Name", "Type", "Parameters", "Model ID"]
            table_data = []
            
            for model in models:
                name = model.get('name', 'Unknown')
                model_id = model.get('model_id', 'Unknown')
                params = model.get('parameters', 'Unknown')
                model_type = model.get('type', 'Unknown')
                table_data.append([name, model_type, params, model_id])
            
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            print()
    
    # Process text-only models
    if 'text_only_models' in config:
        print("=== TEXT-ONLY MODELS ===\n")
        for family, models in config['text_only_models'].items():
            if not models:  # Skip empty families
                continue
                
            family_name = family.replace('_models', '').capitalize()
            print(f"{family_name} Family:")
            
            headers = ["Name", "Type", "Parameters", "Model ID"]
            table_data = []
            
            for model in models:
                name = model.get('name', 'Unknown')
                model_id = model.get('model_id', 'Unknown')
                params = model.get('parameters', 'Unknown')
                model_type = model.get('type', 'Unknown')
                table_data.append([name, model_type, params, model_id])
            
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            print()

def deploy_model(model_id, gpu_id=0, max_model_len=None, port=None, isolate_env=True):
    """Deploy a model"""
    try:
        payload = {
            "model_id": model_id,
            "gpu_id": int(gpu_id),
            "isolate_env": bool(isolate_env)
        }
        if max_model_len:
            payload["max_model_len"] = int(max_model_len)
        if port:
            payload["port"] = int(port)
        
        response = requests.post(f"{API_URL}/deploy", json=payload)
        response.raise_for_status()
        result = response.json()
        
        if result["status"] == "already_deployed":
            print(f"Model {model_id} is already deployed on port {result['port']}")
        else:
            print(f"Deploying {model_id} on port {result['port']}...")
            print(f"Check logs with: polarisLLM logs {model_id}")
    except Exception as e:
        print(f"Error: {str(e)}")

def list_deployments():
    """List active deployments"""
    try:
        response = requests.get(f"{API_URL}/deployments")
        response.raise_for_status()
        deployments = response.json()
        
        print("\n=== Active Deployments ===\n")
        
        if not deployments:
            print("No active deployments found.\n")
            return
        
        print("+---------------------------+-----------+------+-----+----------+")
        print("| Model ID                  | Status    | Port | GPU | Type     |")
        print("+---------------------------+-----------+------+-----+----------+")
        
        for deployment in deployments:
            model_id = deployment.get("model_id", "Unknown")
            status = deployment.get("status", "Unknown")
            port = deployment.get("port", 0)
            gpu_id = deployment.get("gpu_id", 0)
            env_type = "Isolated" if deployment.get("env_path") else "System"
            
            status_display = f"● Running" if status == "running" else status
            print(f"| {model_id:<25} | {status_display:<9} | {port:<4} | {gpu_id:<3} | {env_type:<8} |")
        
        print("+---------------------------+-----------+------+-----+----------+")
        
        print("\n=== Monitoring Options ===\n")
        print("• To view deployment logs:")
        print("  polarisLLM logs <model_id>\n")
        
        print("• To test a deployed model:")
        print("  polarisLLM test text <model_id>")
        print("  polarisLLM test vision <model_id> <image_path> (for vision models)")
        print("  polarisLLM test audio <model_id> <audio_path> (for audio models)\n")
        
        print("• To stop a deployment:")
        print("  polarisLLM stop <model_id>")
    except Exception as e:
        print(f"Error: {str(e)}")

def view_logs(model_id):
    """View deployment logs for a model"""
    try:
        # First get the deployment info to find the log file
        response = requests.get(f"{API_URL}/deployments")
        response.raise_for_status()
        deployments = response.json()
        
        log_file = None
        for deployment in deployments:
            if deployment.get("model_id") == model_id:
                log_file = deployment.get("log_file")
                break
        
        if not log_file:
            print(f"No deployment found for model {model_id}")
            return
        
        # Use tail to follow the log file
        print(f"Showing logs for {model_id} (press Ctrl+C to exit):")
        try:
            subprocess.run(["tail", "-f", log_file])
        except KeyboardInterrupt:
            print("\nExiting log view")
    except Exception as e:
        print(f"Error: {str(e)}")

def stop_deployment(model_id):
    """Stop a deployment"""
    try:
        response = requests.delete(f"{API_URL}/deployments/{model_id}")
        response.raise_for_status()
        result = response.json()
        print(f"Deployment of {model_id} stopped successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_text_model(model_id):
    """Test a text model with an interactive prompt"""
    try:
        # Find the port
        response = requests.get(f"{API_URL}/deployments")
        response.raise_for_status()
        deployments = response.json()
        
        port = None
        for deployment in deployments:
            if deployment.get("model_id") == model_id:
                port = deployment.get("port")
                break
        
        if not port:
            print(f"No active deployment found for model {model_id}")
            return
        
        print(f"Testing model {model_id} (Enter 'exit' to quit)\n")
        
        while True:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
                
            data = {
                "messages": [
                    {"role": "user", "content": user_input}
                ],
                "stream": False
            }
            
            response = requests.post(f"http://localhost:{port}/v1/chat/completions", json=data)
            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"\nAssistant: {assistant_message}\n")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_vision_model(model_id, image_path):
    """Test a vision model with an image"""
    try:
        # Find the port
        response = requests.get(f"{API_URL}/deployments")
        response.raise_for_status()
        deployments = response.json()
        
        port = None
        for deployment in deployments:
            if deployment.get("model_id") == model_id:
                port = deployment.get("port")
                break
        
        if not port:
            print(f"No active deployment found for model {model_id}")
            return
            
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return
        
        print(f"Testing vision model {model_id} with image {image_path}\n")
        
        user_input = input("Prompt (describe what you want to know about the image): ")
        
        # Encode image as base64
        import base64
        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")
        
        # Create message with image
        data = {
            "messages": [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_input},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                        }
                    ]
                }
            ],
            "stream": False
        }
        
        response = requests.post(f"http://localhost:{port}/v1/chat/completions", json=data)
        if response.status_code == 200:
            result = response.json()
            assistant_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\nAssistant: {assistant_message}\n")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

def show_help():
    """Show help message"""
    print("\n=== PolarisLLM CLI Help ===\n")
    print("Available commands:")
    print("  polarisLLM list models                       - List all available models")
    print("  polarisLLM deploy <model_id> [options]       - Deploy a model")
    print("    Options:")
    print("      --gpu <id>                               - GPU ID (default: 0)")
    print("      --max-len <length>                       - Maximum sequence length")
    print("      --port <port>                            - Port number")
    print("      --no-isolate                             - Don't use isolated environment")
    print("  polarisLLM list deployments                  - List active deployments")
    print("  polarisLLM logs <model_id>                   - View deployment logs")
    print("  polarisLLM test text <model_id>              - Test a text model interactively")
    print("  polarisLLM test vision <model_id> <img_path> - Test a vision model with an image")
    print("  polarisLLM stop <model_id>                   - Stop a deployment")
    print("  polarisLLM help                              - Show this help message\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "list" and len(sys.argv) > 2 and sys.argv[2].lower() == "models":
        list_models()
    elif command == "deploy" and len(sys.argv) > 2:
        model_id = sys.argv[2]
        gpu_id = 0
        max_model_len = None
        port = None
        isolate_env = True
        
        # Parse options
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--gpu" and i+1 < len(sys.argv):
                gpu_id = int(sys.argv[i+1])
                i += 2
            elif sys.argv[i] == "--max-len" and i+1 < len(sys.argv):
                max_model_len = int(sys.argv[i+1])
                i += 2
            elif sys.argv[i] == "--port" and i+1 < len(sys.argv):
                port = int(sys.argv[i+1])
                i += 2
            elif sys.argv[i] == "--no-isolate":
                isolate_env = False
                i += 1
            else:
                i += 1
        
        deploy_model(model_id, gpu_id, max_model_len, port, isolate_env)
    elif command == "list" and len(sys.argv) > 2 and sys.argv[2].lower() == "deployments":
        list_deployments()
    elif command == "logs" and len(sys.argv) > 2:
        view_logs(sys.argv[2])
    elif command == "stop" and len(sys.argv) > 2:
        stop_deployment(sys.argv[2])
    elif command == "test" and len(sys.argv) > 3:
        if sys.argv[2].lower() == "text":
            test_text_model(sys.argv[3])
        elif sys.argv[2].lower() == "vision" and len(sys.argv) > 4:
            test_vision_model(sys.argv[3], sys.argv[4])
        else:
            print("Invalid test command. Use 'text' or 'vision'.")
    elif command == "help":
        show_help()
    else:
        print("Invalid command. Use 'polarisLLM help' for usage information.") 