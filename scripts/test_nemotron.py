import asyncio
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.llm_client import NemotronClient
from app.config import settings


async def main():
    print("=" * 60)
    print("🧪 Testing NVIDIA Nemotron 3.5 Lightning NIM Integration")
    print(f"• Endpoint: {settings.nemotron_url}")
    print(f"• Model: {settings.nemotron_model}")
    print("=" * 60)

    client = NemotronClient(
        base_url=settings.nemotron_url,
        model=settings.nemotron_model,
        api_key=settings.nemotron_api_key
    )

    is_healthy = await client.check_health()
    print(f"Health Check: {'✅ ONLINE' if is_healthy else '⚠️ OFFLINE (Mock Fallback Active)'}")

    system_prompt = "You are an AI Sports Producer. Return JSON with a soccer highlight prediction."
    user_prompt = "Match: Barcelona 6-1 PSG. Event: Neymar free-kick at 88 minutes."

    print("\nSending structured JSON reasoning query...")
    result = await client.chat_json(
        system_prompt=system_prompt,
        user_message=user_prompt,
        fallback_handler=lambda msg: {"status": "fallback_success", "player": "Neymar", "minute": 88}
    )

    print("Response received:")
    print(result)
    print("\n✅ Nemotron Client test concluded successfully.")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
