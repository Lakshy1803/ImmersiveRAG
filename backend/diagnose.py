import os
import sys
import logging
import time
import asyncio
import socket
import platform
from pathlib import Path

# Ensure backend/ directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import config
from app.storage.vector_db import get_qdrant_client
from app.engine.ingestion.embedder import get_corporate_embeddings
from app.engine.agents.llm_client import get_llm_client

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_step(msg):
    print(f"\n{Colors.BLUE}>>> {msg}{Colors.END}")

def print_success(msg):
    print(f"{Colors.GREEN}  [PASS] {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}  [WARN] {msg}{Colors.END}")

def print_error(msg, tip=None):
    print(f"{Colors.RED}  [FAIL] {msg}{Colors.END}")
    if tip:
        print(f"         💡 Tip: {tip}")

async def run_diagnostics():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("="*60)
    print("      🔍 IMMERSIVERAG END-TO-END DIAGNOSTICS      ")
    print("="*60)
    print(f"{Colors.END}")

    # 🟢 STEP 1: OS & Environment
    print_step("Checking System & Environment...")
    print(f"  - Platform: {platform.system()} {platform.release()}")
    print(f"  - Python: {sys.version.split()[0]}")
    print(f"  - Bypass SSL: {config.bypass_ssl_verify}")
    print(f"  - LLM Model: {config.llm_model}")
    print(f"  - Proxy Detected: {os.environ.get('HTTPS_PROXY', 'None')}")

    # 🟢 STEP 2: Directory & Permission Check (For PermissionError [Errno 13])
    print_step("Checking File System Permissions...")
    data_dir = Path(config.data_dir)
    qdrant_dir = Path(config.qdrant_path)
    
    if not data_dir.exists():
        print_warning(f"Data directory missing. Creating: {data_dir}")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for Qdrant lock file
    lock_file = qdrant_dir / ".lock"
    if lock_file.exists():
        print_error(
            f"Qdrant Lock File Found: {lock_file}",
            "This causes 'PermissionError: [Errno 13]'. Kill any stale python.exe processes!"
        )
    else:
        print_success("No Qdrant locks detected.")

    # 🟢 STEP 3: Network Connectivity
    print_step("Checking Network Connectivity...")
    
    def check_host(host, port=443):
        try:
            socket.create_connection((host, port), timeout=3)
            return True
        except:
            return False

    # Check common endpoints
    hosts_to_check = {
        "HuggingFace (Models)": "huggingface.co",
        "Groq (LLM)": "api.groq.com",
        "OpenAI (Direct)": "api.openai.com"
    }
    
    for name, host in hosts_to_check.items():
        if check_host(host):
            print_success(f"Network: Reachable to {name} ({host})")
        else:
            print_warning(f"Network: {name} ({host}) is UNREACHABLE. This usually indicates VPN/Proxy issues.")

    # 🟢 STEP 4: Qdrant Connection
    print_step("Testing Vector Store (Qdrant)...")
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        print_success(f"Qdrant Connected. Collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print_error(f"Qdrant Connection Failed: {e}")

    # 🟢 STEP 5: Embedding Test (Local vs Cloud)
    print_step("Testing Embedding Generation...")
    try:
        start = time.time()
        # Test with a single string to see if it hangs
        vectors = get_corporate_embeddings(["Diagnostic test message"])
        print_success(f"Embedding generated (dim: {len(vectors[0])}). Time: {time.time()-start:.2f}s")
    except Exception as e:
        print_error(f"Embedding Failed: {e}", "In PwC, this usually means HuggingFace is blocked or requires SSL bypass.")

    # 🟢 STEP 6: LLM Generation Test
    print_step("Testing LLM generation (Official Client)...")
    try:
        start = time.time()
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": "Diagnostic: Say 'READY'"}],
            max_tokens=10
        )
        
        # LOGGING FOR DEEP DEBUGGING
        if not response.choices:
            print_error("LLM returned NO choices.", f"Full Response: {response}")
            return
            
        content = response.choices[0].message.content
        if content is None:
            print_warning("LLM returned 'None' content. Safety filter or safety settings might be too high.")
            print(f"  - Finish Reason: {response.choices[0].finish_reason}")
            print(f"  - Raw Message: {response.choices[0].message}")
        else:
            print_success(f"LLM Response: '{content.strip()}' (Time: {time.time()-start:.2f}s)")
            
    except Exception as e:
        print_error(f"LLM Connection Failed: {e}")
        # If possible, dump the error object attributes
        if hasattr(e, 'response'):
             print(f"  - Raw API Error Response: {e.response}")

    print("\n" + "="*60)
    print(f"{Colors.BOLD}DIAGNOSTICS COMPLETE.{Colors.END}")
    print("="*60)

if __name__ == "__main__":
    if platform.system() == 'Windows':
        # Fix for ProactorEventLoop in Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(run_diagnostics())
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nCritical failure: {e}")
