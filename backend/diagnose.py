import os
import sys
import logging
import time

# Ensure backend/ directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Silence all but errors initially
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnostic")

from app.core.config import config
from app.storage.vector_db import get_qdrant_client
from app.engine.ingestion.embedder import get_corporate_embeddings
from app.engine.agents.llm_client import get_llm
from langchain_core.messages import HumanMessage

def run_diagnostics():
    print("\n" + "="*50)
    print("      🔍 IMMERSIVERAG VPN DIAGNOSTICS      ")
    print("="*50)
    print(f"Bypass SSL: {config.bypass_ssl_verify}")
    print(f"LLM Provider: {config.llm_base_url or 'Default'}")
    print(f"Embedding Mode: {config.embedding_provider}")
    print("-" * 50)

    # 🟢 TEST 1: Qdrant Connection (Local)
    print("\n[TEST 1] Connecting to local Qdrant...")
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        print(f"✅ Qdrant OK. Found collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print(f"❌ Qdrant FAILED: {e}")

    # 🟢 TEST 2: Embedding Generation (VPN/Local)
    print("\n[TEST 2] Generating test embedding (384-dim if local, 1536 if API)...")
    try:
        start = time.time()
        # Test with a single string
        vectors = get_corporate_embeddings(["Test query for connectivity"])
        print(f"✅ Embedding OK. Vector dim: {len(vectors[0])} (Took {time.time()-start:.2f}s)")
    except Exception as e:
        print(f"❌ Embedding FAILED: {e}")
        print("Tip: If this hangs, your VPN is blocking the local 'FastEmbed' model download from HuggingFace.")

    # 🟢 TEST 3: LLM Connectivity (VPN/Proxy)
    print("\n[TEST 3] Connecting to LLM Service (Groq/OpenAI)...")
    try:
        start = time.time()
        llm = get_llm()
        print("Sending 'ping'...")
        response = llm.invoke([HumanMessage(content="Say 'pong'")])
        print(f"✅ LLM OK. Response: '{response.content.strip()}' (Took {time.time()-start:.2f}s)")
    except Exception as e:
        print(f"❌ LLM FAILED: {e}")
        print("Tip: If this fails with SSL error, verify bypass_ssl_verify=True in .env")

    print("\n" + "="*50)
    print("DIAGNOSTICS COMPLETE")
    print("="*50)

if __name__ == "__main__":
    run_diagnostics()
