#!/usr/bin/env python3
import requests
import json
import argparse
import sys
import base64
import os
from PIL import Image
import io

def get_image_description(proxy_url, model_name, image_path, description_prompt):
    """Calls the multimodal model to get a text description of the image."""
    print(f"--- Step 1: Getting Image Description --- ")
    print(f"Model: {model_name}, Prompt: '{description_prompt}'")
    
    api_url = f"{proxy_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # --- Image Processing (Simplified from test_image_streaming.py) ---
    if not (image_path and os.path.exists(image_path)):
        print(f"Error: Image path '{image_path}' is missing or invalid.", file=sys.stderr)
        return None
        
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img_format = Image.registered_extensions().get(os.path.splitext(image_path)[1].lower(), "JPEG")
            if img_format == "PNG" and img.mode == "RGBA":
                img = img.convert("RGB")
            elif img_format not in ["JPEG", "PNG", "GIF", "WEBP"]:
                img_format = "JPEG"
            img.save(buffer, format=img_format, quality=85)
            image_bytes = buffer.getvalue()
        image_content = base64.b64encode(image_bytes).decode('utf-8')
        image_mime_type = f"image/{img_format.lower()}"
    except Exception as e:
        print(f"Error processing image: {e}", file=sys.stderr)
        return None
    # --- End Image Processing ---

    data = {
        "model": model_name,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": description_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_content}"}}
                ]
            }
        ],
        "temperature": 0.5, # Lower temp for more objective description
        "max_tokens": 300,
        "stream": False # IMPORTANT: Get the full description at once
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        
        # Extract the description text
        if (response_json.get('choices') and 
            len(response_json['choices']) > 0 and 
            response_json['choices'][0].get('message') and 
            response_json['choices'][0]['message'].get('content')):
            
            description = response_json['choices'][0]['message']['content']
            print(f"Description received: {description[:100]}...") # Print start of description
            return description
        else:
            print("Error: Could not find description in the response.", file=sys.stderr)
            print(f"Response JSON: {response_json}", file=sys.stderr)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error calling vision model: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from vision model.", file=sys.stderr)
        print(f"Response Text: {response.text}", file=sys.stderr)
        return None

def get_final_answer(proxy_url, model_name, final_prompt):
    """Calls the language model with the combined prompt and streams the answer."""
    print(f"\n--- Step 2: Getting Final Answer --- ")
    print(f"Model: {model_name}")
    # print(f"Combined Prompt: {final_prompt}") # Uncomment to see full prompt
    
    api_url = f"{proxy_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model_name,
        "messages": [
            # {"role": "system", "content": "You answer questions based *only* on the provided description."}, 
            {"role": "user", "content": final_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True # Stream the final answer
    }
    
    print("Final Answer Stream:")
    try:
        response = requests.post(api_url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
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
                    except json.JSONDecodeError:
                        print(f"\n[Error decoding JSON chunk: {json_data_str}]", file=sys.stderr)
        # --- End Stream Handling ---
        print("\n" + "-" * 25) 
        print("Final answer stream complete.")

    except requests.exceptions.RequestException as e:
        print(f"\nError calling language model: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred during final answer streaming: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chain vision and language models via proxy.")
    parser.add_argument("--url", type=str, default="http://localhost:8989", 
                        help="Proxy server base URL")
    parser.add_argument("--vision-model", type=str, default="deepseek-vl-7b-chat", 
                        help="Multimodal model name for description")
    parser.add_argument("--language-model", type=str, default="Qwen2.5-7B-Instruct", 
                        help="Language model name for final answer")
    parser.add_argument("--image", type=str, default="Mubarak.png",
                        help="Path to the image file")
    parser.add_argument("--question", type=str, default="Based on the description, what age do you think the person in the image is?",
                        help="The final question to ask the language model")
    parser.add_argument("--desc-prompt", type=str, default="Describe the person in this image objectively, focusing on visual details relevant to age estimation.",
                        help="The prompt for the vision model to get the description")
    
    args = parser.parse_args()
    
    # --- Dependency Check ---
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow library not found. Please install it using: pip install Pillow", file=sys.stderr)
        sys.exit(1)
        
    # --- Step 1: Get Description ---
    description = get_image_description(args.url, args.vision_model, args.image, args.desc_prompt)
    
    if description:
        # --- Step 2: Combine and Ask Final Question ---
        final_combined_prompt = f"{args.question}\n\nDescription:\n{description}"
        get_final_answer(args.url, args.language_model, final_combined_prompt)
    else:
        print("\nCould not get image description. Aborting Step 2.", file=sys.stderr) 