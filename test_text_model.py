#!/usr/bin/env python3
import requests
import json
import time
import argparse

def test_text_model(message, temperature=0.7, max_tokens=500):
    """Test the Qwen2.5-7B-Instruct text model with a chat message."""
    print("\n" + "="*80)
    print("Testing Qwen2.5-7B-Instruct...")
    print(f"Sending message: '{message}'")
    print("="*80)
    
    url = "http://localhost:8989/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": "Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": message}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    try:
        # Check if the model is available
        # try:
        #     response = requests.get("http://localhost:1088/v1/models")
        #     if response.status_code != 200:
        #         print(f"Model API returned status code {response.status_code}. It might still be loading.")
        #         print("Waiting 10 seconds before testing...")
        #         time.sleep(10)
        # except Exception as e:
        #     print(f"Error connecting to model API: {e}")
        #     print("The model might still be loading. Waiting 10 seconds before testing...")
        #     time.sleep(10)
            
        # Using stream=True for a better user experience
        response = requests.post(url, headers=headers, json=data, stream=True)
        
        if response.status_code == 200:
            print("\nResponse:")
            print("-"*80)
            
            full_content = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: ') and not line.startswith('data: [DONE]'):
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get('choices') and chunk['choices'][0].get('delta') and chunk['choices'][0]['delta'].get('content'):
                                content = chunk['choices'][0]['delta']['content']
                                full_content += content
                                print(content, end='', flush=True)
                        except json.JSONDecodeError:
                            pass
            
            print("\n" + "-"*80)
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"Error connecting to the model: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Qwen2.5-7B-Instruct text model")
    parser.add_argument("--prompt", type=str, default="Who was the first Muganda man?.",
                      help="Text prompt to send to the model")
    parser.add_argument("--temperature", type=float, default=0.7,
                      help="Temperature for response generation (0.0-1.0)")
    parser.add_argument("--max-tokens", type=int, default=500,
                      help="Maximum tokens to generate")
    
    args = parser.parse_args()
    
    test_text_model(args.prompt, args.temperature, args.max_tokens)