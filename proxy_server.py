import logging
from flask import Flask, request, jsonify, Response
import requests
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proxy_requests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Target URL where the Qwen model is running
TARGET_URL_QWEN = "http://localhost:1088"
# Target URL where the DeepSeek-VL model is running
TARGET_URL_DEEPSEEK = "http://localhost:9089"

@app.route('/', methods=['GET'])
def home():
    return "Multi-Model LLM Proxy Server is running. Send requests to /v1/chat/completions"

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    # Log the incoming request details
    logger.info(f"Received {request.method} request to /{path}")
    logger.info(f"Headers: {dict(request.headers)}")

    # Get the request data once
    request_data = request.get_data()
    data_str = request_data.decode('utf-8') # Decode for logging/parsing

    # Determine target URL based on model in body (for relevant paths/methods)
    target_url = TARGET_URL_QWEN  # Default to Qwen
    model_name = "N/A"

    if request.method == 'POST' and path == 'v1/chat/completions' and request_data:
        try:
            data_json = json.loads(data_str) if data_str else {}
            model_name = data_json.get("model", "N/A")
            logger.info(f"Body: {json.dumps(data_json, indent=2)}")

            # Routing logic
            if model_name.startswith("deepseek"):
                target_url = TARGET_URL_DEEPSEEK
                logger.info(f"Routing to DeepSeek ({target_url}) based on model: {model_name}")
            else:
                # Default to Qwen for other models or if model field is missing
                target_url = TARGET_URL_QWEN
                logger.info(f"Routing to Qwen ({target_url}) based on model: {model_name}")

        except json.JSONDecodeError:
            logger.info(f"Body (non-JSON): {data_str}")
            # Keep default target_url (Qwen) for non-JSON POSTs to this path
            logger.info(f"Routing to default Qwen ({target_url}) due to non-JSON body")
    elif request_data:
         logger.info(f"Body: {data_str}") # Log body for other requests too
         # Keep default target_url (Qwen) for other paths/methods
         logger.info(f"Routing to default Qwen ({target_url}) for path /{path}")
    else:
        logger.info("Body: None")
        # Keep default target_url (Qwen) if no body
        logger.info(f"Routing to default Qwen ({target_url}) due to no body")

    # Construct the full URL for the target server
    url = f"{target_url}/{path}"
    logger.info(f"Forwarding {request.method} request to: {url}")
    
    # Get all the headers from the request
    headers = {key: value for (key, value) in request.headers if key != 'Host'}
    
    # Use the original request_data bytes for forwarding
    
    # Make the request to the target server
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request_data, # Use the original bytes data
            cookies=request.cookies,
            stream=True
        )
        
        # Create a Flask response object
        response = Response(
            resp.iter_content(chunk_size=10*1024),
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'text/plain')
        )
        
        # Add headers from the response
        for key, value in resp.headers.items():
            if key.lower() not in ('content-length', 'connection', 'content-encoding', 'transfer-encoding'):
                response.headers[key] = value
                
        return response
    except requests.RequestException as e:
        logger.error(f"Error forwarding request: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8989, debug=False)