import requests
import json
import time
import sys

url = "http://127.0.0.1:8000/agent/chat/stream"
payload = {
    "question": "Explain RAG in detail.",
    "agent_id": "doc_analyzer",
    "session_id": "test_sess_v2"
}

print(f"Calling {url}...")
start_time = time.time()
try:
    # Use -N in curl equivalent: stream=True
    with requests.post(url, json=payload, stream=True, timeout=60) as response:
        print(f"Response status: {response.status_code}")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                elapsed = time.time() - start_time
                print(f"[{elapsed:.2f}s] {decoded_line}")
                sys.stdout.flush()
except Exception as e:
    print(f"Error: {e}")
