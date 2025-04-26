#!/usr/bin/env python3
import requests
import json
import argparse
import sys
import base64
import os
from PIL import Image
import io

def test_image_stream(proxy_url, model_name, prompt, image_path):
    """Sends a multimodal request with stream=True and prints text chunks."""
    
    print(f"--- Testing Image Streaming ---")
    print(f"Proxy URL : {proxy_url}")
    print(f"Model     : {model_name}")
    print(f"Prompt    : {prompt}")
    print(f"Image Path: {image_path}")
    print("-" * 25)
    
    # Construct the full API endpoint
    api_url = f"{proxy_url}/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # --- Image Processing and Payload Creation ---
    image_content = None
    if image_path and os.path.exists(image_path):
        try:
            # Resize image if it's potentially large (optional but recommended)
            with Image.open(image_path) as img:
                max_size = (1024, 1024) # Example max size
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                # Convert to JPEG in memory (often smaller than PNG for photos)
                buffer = io.BytesIO()
                # Determine format based on original or default to JPEG
                img_format = Image.registered_extensions().get(os.path.splitext(image_path)[1].lower(), "JPEG")
                if img_format == "PNG" and img.mode == "RGBA":
                    # Handle transparency if needed, e.g., fill with white
                    img = img.convert("RGB")
                elif img_format not in ["JPEG", "PNG", "GIF", "WEBP"]:
                     img_format = "JPEG" # Default if unsupported

                img.save(buffer, format=img_format, quality=85)
                image_bytes = buffer.getvalue()
                
            image_content = base64.b64encode(image_bytes).decode('utf-8')
            image_mime_type = f"image/{img_format.lower()}"
            
            # Multimodal payload structure
            data = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_content}"}}
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "stream": True # Explicitly enable streaming
            }
        except FileNotFoundError:
            print(f"Error: Image file not found at {image_path}", file=sys.stderr)
            return
        except Exception as e:
            print(f"Error processing image: {e}", file=sys.stderr)
            # Fallback to text-only query or handle error appropriately
            # For now, we'll just exit
            return
    else:
        print(f"Error: Image path '{image_path}' is missing or invalid.", file=sys.stderr)
        return
    # --- End Image Processing ---

    full_response_content = ""
    
    try:
        print("Response Stream:")
        # Make the request with stream=True
        response = requests.post(api_url, headers=headers, json=data, stream=True)
        response.raise_for_status() # Raise an exception for bad status codes

        # --- Stream Handling (same as test_streaming.py) ---
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
                            full_response_content += content_chunk
                    except json.JSONDecodeError:
                        print(f"\n[Error decoding JSON chunk: {json_data_str}]", file=sys.stderr)
        # --- End Stream Handling ---
                        
        print("\n" + "-" * 25)
        print("Stream complete.")

    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to proxy or model: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test streaming responses for multimodal models via LLM proxy.")
    parser.add_argument("--url", type=str, default="http://localhost:8989", 
                        help="Proxy server base URL (e.g., http://localhost:8989 or localtunnel URL)")
    parser.add_argument("--model", type=str, default="deepseek-vl-7b-chat", 
                        help="Multimodal model name (e.g., deepseek-vl-7b-chat)")
    parser.add_argument("--prompt", type=str, default="What age do you think the person in image is?",
                        help="Text prompt to send with the image")
    parser.add_argument("--image", type=str, default="Mubarak.png",
                        help="Path to the image file")
    
    args = parser.parse_args()
    
    # Check if Pillow is installed
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow library not found. Please install it using: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    test_image_stream(args.url, args.model, args.prompt, args.image) 