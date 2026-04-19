import httpx
import asyncio
from app.core.config import settings

async def pull_model(model_name: str):
    """Checks if a model exists in Ollama and pulls it if not."""
    print(f"🚀 Checking model: {model_name}...")
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            # Check if model exists
            tags_response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if tags_response.status_code == 200:
                models = tags_response.json().get("models", [])
                if any(m.get("name").startswith(model_name) for m in models):
                    print(f"✅ {model_name} is already available.")
                    return

            # Pull model
            print(f"📥 {model_name} not found. Starting download (this may take a few minutes)...")
            async with client.stream("POST", f"{settings.OLLAMA_BASE_URL}/api/pull", json={"name": model_name}) as response:
                async for line in response.aiter_lines():
                    # We don't need to print every progress update, just the completion
                    pass
            print(f"✅ Successfully pulled {model_name}")
    except Exception as e:
        print(f"⚠️ Could not pull model {model_name}: {e}")
        print("Continuing anyway, assuming model might be handled externally.")

async def run_bootstrap():
    """Initializes all necessary models."""
    print("\n--- Project Initialization ---")
    await pull_model(settings.LLM_MODEL)
    await pull_model(settings.EMBEDDING_MODEL)
    print("--- Initialization Complete ---\n")

if __name__ == "__main__":
    asyncio.run(run_bootstrap())
