import os
import sys
import asyncio

# Ensure backend/ directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import config
from app.engine.agents.llm_client import get_llm_client

async def test_generation():
    print(f"--- LLM Generation Test (Official OpenAI Client) ---")
    print(f"Model: {config.llm_model}")
    print(f"Base URL: {config.llm_base_url or 'Default'}")
    print(f"Bypass SSL: {config.bypass_ssl_verify}")
    
    try:
        # Initialize the official AsyncOpenAI client
        client = get_llm_client()
        
        print("\nSending test prompt: 'Hello, what is 2+2?'")
        messages = [
            {"role": "user", "content": "Hello, what is 2+2?"}
        ]
        
        # Test basic chat completion
        print("Waiting for response...")
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            max_tokens=50
        )
        
        print("\n--- RESPONSE RECEIVED ---")
        print(response.choices[0].message.content.strip())
        print("--------------------------")
        print("\n✅ Official OpenAI Client is WORKING correctly.")

    except Exception as e:
        print("\n❌ LLM Connection FAILED.")
        print(f"Error detail: {e}")

if __name__ == "__main__":
    asyncio.run(test_generation())
