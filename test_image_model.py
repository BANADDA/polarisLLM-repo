#!/usr/bin/env python3
import requests
import json
import base64
import os
import time
import argparse
from PIL import Image
import io

def test_multimodal_model(image_path="WhatsApp Image 2025-04-19 at 07.51.36_5ada77f4.jpg", message="What do you see in this image? Describe it in detail.", temperature=0.7, max_tokens=500):
    """Test the DeepSeek-VL-7B-Chat multimodal model with an image and a message."""
    
    print("\n" + "="*80)
    print("Testing DeepSeek-VL-7B-Chat...")
    print(f"Using image: {image_path}")
    print(f"Sending message: '{message}'")
    print("="*80)
    
    url = "http://localhost:9089/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Check if the model is available
    try:
        response = requests.get("http://localhost:9089/v1/models")
        if response.status_code == 200:
            models = response.json()
            print(f"Available models: {models}")
        else:
            print(f"Model API returned status code {response.status_code}. It might still be loading.")
            print("Waiting 10 seconds before testing...")
            time.sleep(10)
    except Exception as e:
        print(f"Error connecting to model API: {e}")
        print("The model might still be loading. Waiting 10 seconds before testing...")
        time.sleep(10)
    
    # Prepare content based on whether we have an image
    if image_path and os.path.exists(image_path):
        try:
            # Resize image if it's too large
            with Image.open(image_path) as img:
                max_size = (1024, 1024)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                # Convert to JPEG in memory
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                image_bytes = buffer.getvalue()
                
            image_content = base64.b64encode(image_bytes).decode('utf-8')
            
            data = {
                "model": "deepseek-vl-7b-chat",
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": message},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}}
                        ]
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        except Exception as e:
            print(f"Error processing image: {e}")
            # Fallback to text-only query
            data = {
                "model": "deepseek-vl-7b-chat",
                "messages": [
                    {"role": "user", "content": "Error processing image. What visual capabilities do you have?"}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
    else:
        print(f"Error: Image file '{image_path}' does not exist.")
        return False
    
    try:
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
    parser = argparse.ArgumentParser(description="Test the DeepSeek-VL-7B-Chat multimodal model")
    parser.add_argument("--image", type=str, default="WhatsApp Image 2025-04-19 at 07.51.36_5ada77f4.jpg", 
                      help="Path to an image file for testing")
    parser.add_argument("--prompt", type=str, default="What do you see in this image? Describe it in detail.",
                      help="Text prompt to send with the image")
    parser.add_argument("--temperature", type=float, default=0.7,
                      help="Temperature for response generation (0.0-1.0)")
    parser.add_argument("--max-tokens", type=int, default=500,
                      help="Maximum tokens to generate")
    
    args = parser.parse_args()
    
    test_multimodal_model(args.image, args.prompt, args.temperature, args.max_tokens)