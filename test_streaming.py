#!/usr/bin/env python3
import requests
import json
import argparse
import sys

def test_stream(proxy_url, model_name, prompt):
    """Sends a request with stream=True and prints chunks as they arrive."""
    
    print(f"--- Testing Streaming ---")
    print(f"Proxy URL: {proxy_url}")
    print(f"Model    : {model_name}")
    print(f"Prompt   : {prompt}")
    print("-" * 25)
    
    # Construct the full API endpoint
    api_url = f"{proxy_url}/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Basic payload structure
    data = {
        "model": model_name,
        "messages": [
            # Add system message for Qwen? (Optional, but good practice)
            # {"role": "system", "content": "You are a helpful assistant."}, 
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True # Explicitly enable streaming
    }
    
    full_response_content = ""
    
    try:
        print("Response Stream:")
        # Make the request with stream=True
        response = requests.post(api_url, headers=headers, json=data, stream=True)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Iterate over the response stream line by line
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                
                # Check if it's a Server-Sent Event (SSE) data line
                if decoded_line.startswith('data: '):
                    # Strip the 'data: ' prefix
                    json_data_str = decoded_line[6:]
                    
                    # Check for the stream termination signal
                    if json_data_str.strip() == '[DONE]':
                        # print("\n[STREAM FINISHED]") # Optional: print stream end (Fixed newline in string)
                        break
                        
                    try:
                        # Parse the JSON chunk
                        chunk = json.loads(json_data_str)
                        
                        # Extract content from the 'delta' field if present
                        if (chunk.get('choices') and 
                            len(chunk['choices']) > 0 and 
                            chunk['choices'][0].get('delta') and 
                            chunk['choices'][0]['delta'].get('content')):
                            
                            content_chunk = chunk['choices'][0]['delta']['content']
                            
                            # Print the chunk immediately to show streaming
                            print(content_chunk, end='', flush=True)
                            
                            # Append to the full response
                            full_response_content += content_chunk
                            
                    except json.JSONDecodeError:
                        print(f"\n[Error decoding JSON chunk: {json_data_str}]", file=sys.stderr)
                        
        print("\n" + "-" * 25) # Newline after stream finishes
        print("Stream complete.")
        # Optional: Print the fully assembled response
        # print("\n--- Full Response ---")
        # print(full_response_content)
        # print("-" * 21)

    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to proxy or model: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test streaming responses via LLM proxy.")
    parser.add_argument("--url", type=str, default="https://lemon-tips-know.loca.lt", 
                        help="Proxy server base URL (e.g., http://localhost:8989 or localtunnel URL)")
    parser.add_argument("--model", type=str, default="Qwen2.5-7B-Instruct", 
                        help="Model name to request (e.g., Qwen2.5-7B-Instruct, deepseek-vl-7b-chat)")
    parser.add_argument("--prompt", type=str, default="Write a short story about a curious robot exploring a garden.",
                        help="Text prompt to send to the model")
    
    args = parser.parse_args()
    
    test_stream(args.url, args.model, args.prompt) 