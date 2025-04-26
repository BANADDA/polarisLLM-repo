#!/usr/bin/env python3
import requests
import json
import base64
import argparse
from PIL import Image
import io
import os

class LLMClient:
    def __init__(self, text_model_url=None, vision_model_url=None):
        """Initialize with the tunnel URLs for both models."""
        self.text_model_url = text_model_url
        self.vision_model_url = vision_model_url
        self.conversation_history = {
            "text": [],
            "vision": []
        }
    
    def text_query(self, message, temperature=0.7, stream=True, new_conversation=False):
        """Send a text query to the Qwen model with conversation history."""
        if new_conversation:
            self.conversation_history["text"] = []
            
        # Add user message to history
        self.conversation_history["text"].append({"role": "user", "content": message})
        
        url = f"{self.text_model_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        
        data = {
            "model": "Qwen2.5-7B-Instruct",
            "messages": self.conversation_history["text"],
            "temperature": temperature,
            "max_tokens": 500,
            "stream": stream
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=stream)
            
            if stream:
                full_content = ""
                print("\nResponse:")
                print("-"*80)
                
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
                
                # Add assistant response to history
                self.conversation_history["text"].append({"role": "assistant", "content": full_content})
                return full_content
            else:
                if response.status_code == 200:
                    result = response.json()
                    response_text = result['choices'][0]['message']['content']
                    
                    # Add assistant response to history
                    self.conversation_history["text"].append({"role": "assistant", "content": response_text})
                    return response_text
                else:
                    print(f"Error: {response.status_code}")
                    print(response.text)
                    return None
        except Exception as e:
            print(f"Error connecting to the model: {e}")
            return None
    
    def vision_query(self, message, image_path=None, temperature=0.7, stream=True, new_conversation=False):
        """Send a vision query to the DeepSeek model with conversation history."""
        if new_conversation:
            self.conversation_history["vision"] = []
        
        url = f"{self.vision_model_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        
        # Prepare message content
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
                
                content = [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}}
                ]
            except Exception as e:
                print(f"Error processing image: {e}")
                content = message
        else:
            content = message
        
        # Add user message to history
        self.conversation_history["vision"].append({
            "role": "user", 
            "content": content
        })
        
        data = {
            "model": "deepseek-vl-7b-chat",
            "messages": self.conversation_history["vision"],
            "temperature": temperature,
            "max_tokens": 500,
            "stream": stream
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=stream)
            
            if stream:
                full_content = ""
                print("\nResponse:")
                print("-"*80)
                
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
                
                # Add assistant response to history
                self.conversation_history["vision"].append({"role": "assistant", "content": full_content})
                return full_content
            else:
                if response.status_code == 200:
                    result = response.json()
                    response_text = result['choices'][0]['message']['content']
                    
                    # Add assistant response to history
                    self.conversation_history["vision"].append({"role": "assistant", "content": response_text})
                    return response_text
                else:
                    print(f"Error: {response.status_code}")
                    print(response.text)
                    return None
        except Exception as e:
            print(f"Error connecting to the model: {e}")
            return None
    
    def save_conversation(self, model_type, filename):
        """Save the conversation history to a file."""
        if model_type not in ["text", "vision"]:
            print("Error: model_type must be 'text' or 'vision'")
            return False
            
        with open(filename, 'w') as f:
            json.dump(self.conversation_history[model_type], f, indent=2)
        print(f"Conversation saved to {filename}")
        return True
    
    def load_conversation(self, model_type, filename):
        """Load a conversation history from a file."""
        if model_type not in ["text", "vision"]:
            print("Error: model_type must be 'text' or 'vision'")
            return False
            
        try:
            with open(filename, 'r') as f:
                self.conversation_history[model_type] = json.load(f)
            print(f"Conversation loaded from {filename}")
            return True
        except Exception as e:
            print(f"Error loading conversation: {e}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remote LLM Client")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Text model parser
    text_parser = subparsers.add_parser("text", help="Query the text model")
    text_parser.add_argument("--message", "-m", required=True, help="Message to send")
    text_parser.add_argument("--url", default=None, help="Model URL (from tunnel)")
    text_parser.add_argument("--new", action="store_true", help="Start a new conversation")
    text_parser.add_argument("--save", help="Save conversation to file")
    text_parser.add_argument("--load", help="Load conversation from file")
    
    # Vision model parser
    vision_parser = subparsers.add_parser("vision", help="Query the vision model")
    vision_parser.add_argument("--message", "-m", required=True, help="Message to send")
    vision_parser.add_argument("--image", "-i", help="Image path")
    vision_parser.add_argument("--url", default=None, help="Model URL (from tunnel)")
    vision_parser.add_argument("--new", action="store_true", help="Start a new conversation")
    vision_parser.add_argument("--save", help="Save conversation to file")
    vision_parser.add_argument("--load", help="Load conversation from file")
    
    args = parser.parse_args()
    
    # Default URLs (can be overridden by args)
    # Replace these with your actual tunnel URLs after running start_tunnels.sh
    text_url = args.url if args.command == "text" and args.url else "https://qwen-llm.loca.lt"
    vision_url = args.url if args.command == "vision" and args.url else "https://deepseek-vl.loca.lt"
    
    client = LLMClient(text_model_url=text_url, vision_model_url=vision_url)
    
    if args.command == "text":
        if args.load:
            client.load_conversation("text", args.load)
        
        client.text_query(args.message, new_conversation=args.new)
        
        if args.save:
            client.save_conversation("text", args.save)
    
    elif args.command == "vision":
        if args.load:
            client.load_conversation("vision", args.load)
        
        client.vision_query(args.message, image_path=args.image, new_conversation=args.new)
        
        if args.save:
            client.save_conversation("vision", args.save)