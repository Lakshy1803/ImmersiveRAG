import os
import sys
import time
import logging
import platform

# Add the current directory to sys.path to allow imports from 'app'
sys.path.append(os.getcwd())

from app.core.config import config
from app.engine.agents.llm_client import get_llm_client

# Simple colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_step(msg):
    print(f"\n{Colors.BLUE}>>> {msg}{Colors.END}")

def print_success(msg):
    print(f"  {Colors.GREEN}[PASS]{Colors.END} {msg}")

def print_warning(msg):
    print(f"  {Colors.WARNING}[WARN]{Colors.END} {msg}")

def print_error(msg, tip=None):
    print(f"  {Colors.FAIL}[FAIL]{Colors.END} {msg}")
    if tip:
        print(f"         Tip: {tip}")

def check_network(host, port=443):
    import socket
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def main():
    print("\n" + "="*60)
    print(f"{Colors.HEADER}{Colors.BOLD}      IMMERSIVERAG END-TO-END DIAGNOSTICS (SYNC)      {Colors.END}")
    print("="*60 + "\n")

    # STEP 1: System Info
    print_step("Checking System & Environment...")
    print(f"  - Platform: {platform.system()} {platform.release()}")
    print(f"  - Python: {platform.python_version()}")
    print(f"  - Bypass SSL: {config.bypass_ssl_verify}")
    print(f"  - LLM Model: {config.llm_model}")
    
    # Check for proxies
    proxy = os.environ.get('HTTP_PROXY') or os.environ.get('https_proxy')
    print(f"  - Proxy Detected: {proxy or 'None'}")

    # STEP 2: File System & Qdrant Lock
    print_step("Checking File System Permissions...")
    qdrant_path = os.path.join(os.getcwd(), "data", "qdrant")
    lock_file = os.path.join(qdrant_path, ".lock")
    
    if os.path.exists(lock_file):
        print_error(f"Qdrant Lock File Found: {lock_file}", 
                    "This causes 'PermissionError: [Errno 13]'. Kill any stale python.exe processes!")
    else:
        print_success("Qdrant storage is clear of stale locks.")

    # STEP 3: Network Connectivity
    print_step("Checking Network Connectivity...")
    connectivity = {
        "HuggingFace (Models)": "huggingface.co",
        "Groq (LLM)": "api.groq.com",
        "OpenAI (Direct)": "api.openai.com"
    }
    for name, host in connectivity.items():
        if check_network(host):
            print_success(f"Network: Reachable to {name} ({host})")
        else:
            print_warning(f"Network: {name} ({host}) is unreachable. Check your VPN/Proxy.")

    # STEP 4: Vector Store (Qdrant)
    print_step("Testing Vector Store (Qdrant)...")
    try:
        from app.storage.vector_db import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        print_success(f"Connected to Qdrant. Found {len(collections.collections)} collections.")
    except Exception as e:
        print_error(f"Vector DB Connection Failed: {e}")

    # STEP 5: Embedding Generation (Corporate vs Local)
    print_step("Testing Embedding Generation...")
    try:
        from app.engine.ingestion.embedder import get_corporate_embeddings
        test_text = ["This is a diagnostic test."]
        start = time.time()
        
        has_api_key = bool(config.embedding_api_key)
        mode = "corporate" if has_api_key else "local_fastembed"
        
        print(f"  - Testing Mode: {mode}")
        embs = get_corporate_embeddings(test_text, embedding_mode=mode)
        
        print_success(f"Generated embeddings ({mode}) (Dim: {len(embs[0])}) in {time.time()-start:.2f}s")
    except Exception as e:
        print_error(f"Embedding Generation Failed in {mode} mode: {e}", 
                    "Check API keys/Base URL if in corporate mode, or fastembed install if local.")

    # STEP 6: LLM Generation Test (Sync)
    print_step("Testing LLM generation (Sync Client)...")
    try:
        start = time.time()
        client = get_llm_client()
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": "Write a 5 paragraph essay about AI. Be descriptive."}],
            max_tokens=2000,
            temperature=0.7
        )
        
        # LOGGING FOR DEEP DEBUGGING
        if not response.choices:
            print_error("LLM returned NO choices.", f"Full Response: {response}")
            return
            
        content = response.choices[0].message.content
        if content is None:
            print_warning("LLM returned 'None' content. Check safety filters or proxy ceiling.")
            print(f"  - Finish Reason: {response.choices[0].finish_reason}")
            print(f"  - Refusal: {getattr(response.choices[0].message, 'refusal', 'None')}")
            print(f"  - Raw Message: {response.choices[0].message}")
        else:
            print_success(f"LLM Response Received (Length: {len(content)} chars)")
            print(f"  - Finish Reason: {response.choices[0].finish_reason}")
            print(f"  - First 100 chars: {content[:100].strip()}...")
            if response.choices[0].finish_reason == 'length':
                print_warning("Truncation detected. The response was cut off by the provider/proxy.")
            
    except Exception as e:
        print_error(f"LLM Connection Failed: {e}")
        if hasattr(e, 'response'):
             print(f"  - Raw API Error Response: {e.response}")

    print("\n" + "="*60)
    print(f"{Colors.BOLD}DIAGNOSTICS COMPLETE.{Colors.END}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
