#!/usr/bin/env python3
import requests
import json
import argparse
import sys
import re # For parsing steps

def get_plan_from_planner(proxy_url, model_name, task):
    """Calls the Planner model to break down the task into steps."""
    print(f"--- Step 1: Planning --- ")
    print(f"Planner Model: {model_name}")
    print(f"Task         : {task}")
    
    api_url = f"{proxy_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Prompt asking the model to break down the task into numbered steps
    planning_prompt = f"Break down the following task into a sequence of clear, numbered steps. Only provide the numbered steps:\n\nTask: {task}"
    
    data = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": planning_prompt}
            # Note: DeepSeek-VL might work okay with text-only here, 
            # but a dedicated text model would be better if available.
        ],
        "temperature": 0.3, # Lower temp for more structured planning
        "max_tokens": 400,
        "stream": False # Need the full plan at once
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        
        # Extract the plan text
        if (response_json.get('choices') and 
            len(response_json['choices']) > 0 and 
            response_json['choices'][0].get('message') and 
            response_json['choices'][0]['message'].get('content')):
            
            plan_text = response_json['choices'][0]['message']['content']
            print(f"\nRaw Plan Received:\n{plan_text}")
            
            # --- Attempt to parse numbered steps --- 
            # This regex looks for lines starting with number(s) and a dot.
            steps = re.findall(r"^\s*\d+\.\s*(.*)", plan_text, re.MULTILINE)
            
            if not steps:
                # Fallback: If no numbered list, split by newline and filter empties
                print("[Warning] Could not parse numbered steps, attempting newline split.")
                steps = [line.strip() for line in plan_text.split('\n') if line.strip()]
            
            if steps:
                print(f"\nParsed Steps ({len(steps)}):\n" + "\n".join([f"  {i+1}. {s}" for i, s in enumerate(steps)]))
                return steps
            else:
                 print("Error: Planner response contained no parseable steps.", file=sys.stderr)
                 return None
        else:
            print("Error: Could not find plan in the planner response.", file=sys.stderr)
            print(f"Response JSON: {response_json}", file=sys.stderr)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error calling planner model: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from planner model.", file=sys.stderr)
        print(f"Response Text: {response.text}", file=sys.stderr)
        return None

def execute_step_by_executor(proxy_url, model_name, step_text, step_number, total_steps, original_task):
    """Calls the Executor model to provide details for a specific step and streams the answer."""
    print(f"\n--- Step 2: Executing Step {step_number}/{total_steps} --- ")
    print(f"Executor Model: {model_name}")
    print(f"Step to Execute: {step_text}")
    
    api_url = f"{proxy_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Prompt asking the model to execute or explain the specific step
    # Providing context of the original task might help
    # execution_prompt = f"Regarding the overall task '{original_task}', provide detailed instructions or information for completing the following step:\n\nStep: {step_text}"
    execution_prompt = f"Provide detailed instructions or information for the following step:\n\nStep: {step_text}"

    data = {
        "model": model_name,
        "messages": [
            # {"role": "system", "content": "You provide clear instructions for specific steps."}, 
            {"role": "user", "content": execution_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True # Stream the execution details
    }
    
    print("\nExecution Details Stream:")
    try:
        response = requests.post(api_url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        # --- Stream Handling --- 
        has_output = False
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    json_data_str = decoded_line[6:]
                    if json_data_str.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(json_data_str)
                        if (chunk.get('choices') and 
                            len(chunk['choices']) > 0 and 
                            chunk['choices'][0].get('delta') and 
                            chunk['choices'][0]['delta'].get('content')):
                            content_chunk = chunk['choices'][0]['delta']['content']
                            print(content_chunk, end='', flush=True)
                            has_output = True
                    except json.JSONDecodeError:
                        print(f"\n[Error decoding JSON chunk: {json_data_str}]", file=sys.stderr)
        # --- End Stream Handling ---
        if not has_output:
             print("[No content generated for this step]")
        print("\n" + "-" * 25)
        print(f"Execution for step {step_number} stream complete.")
        return True # Indicate success

    except requests.exceptions.RequestException as e:
        print(f"\nError calling executor model for step {step_number}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred during execution streaming for step {step_number}: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a Planner-Executor agent system.")
    parser.add_argument("--url", type=str, default="http://localhost:8989", 
                        help="Proxy server base URL")
    parser.add_argument("--planner-model", type=str, default="deepseek-vl-7b-chat", 
                        help="Model name for planning (text generation)")
    parser.add_argument("--executor-model", type=str, default="Qwen2.5-7B-Instruct", 
                        help="Model name for executing steps")
    parser.add_argument("--task", type=str, default="How do I make a simple web server using Python Flask?",
                        help="The overall task or question")
    
    args = parser.parse_args()
    
    # --- Step 1: Get Plan ---
    steps = get_plan_from_planner(args.url, args.planner_model, args.task)
    
    # --- Step 2: Execute Plan (if successful) ---
    if steps:
        print(f"\n=== Beginning Execution of {len(steps)} Steps ===")
        total_steps = len(steps)
        for i, step in enumerate(steps):
            print(f"\n>>> Requesting execution for Step {i+1}: '{step}'")
            success = execute_step_by_executor(args.url, args.executor_model, step, i + 1, total_steps, args.task)
            print(f"<<< Finished receiving execution for Step {i+1}")
            if not success:
                print(f"\nExecution failed at step {i+1}. Aborting.", file=sys.stderr)
                break
        print("\n=== Execution Finished ===")
    else:
        print("\nCould not get a plan. Cannot proceed with execution.", file=sys.stderr) 