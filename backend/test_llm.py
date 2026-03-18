import os
import sys

# Ensure backend/ directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import config
from app.engine.agents.llm_client import get_llm
from langchain_core.messages import HumanMessage

def test_generation():
    print(f"--- LLM Generation Test ---")
    print(f"Model: {config.llm_model}")
    print(f"Base URL: {config.llm_base_url or 'Default'}")
    
    try:
        # Initialize the LLM client
        llm = get_llm()
        
        print("\nSending test prompt: 'Hello, what is 2+2?'")
        messages = [HumanMessage(content="Hello, what is 2+2?")]
        
        # Test basic invocation
        print("Waiting for response...")
        response = llm.invoke(messages)
        
        print("\n--- RESPONSE RECEIVED ---")
        print(response.content)
        print("--------------------------")
        print("\n✅ LLM Generation Service is WORKING correctly.")

    except Exception as e:
        print("\n❌ LLM Generation Service FAILED.")
        print(f"Error detail: {e}")
        print("\nPossible fixes:")
        print("1. Check if IMMERSIVE_RAG_LLM_API_KEY is correct in your .env file.")
        print("2. Verify if you have internet access (or VPN OFF if using Groq).")
        print("3. Check if IMMERSIVE_RAG_LLM_BASE_URL matches your provider's OpenAI-compatible endpoint.")

if __name__ == "__main__":
    test_generation()
