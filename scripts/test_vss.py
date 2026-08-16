import asyncio
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.vss.client import VSSClient
from app.vss.mock_client import MockVSSClient
from app.config import settings


async def main():
    print("=" * 60)
    print("🧪 Testing NVIDIA VSS (Video Search and Summarization) Skills")
    print(f"• Endpoint: {settings.vss_url}")
    print(f"• VSS Enabled in Config: {settings.vss_enabled}")
    print("=" * 60)

    client = VSSClient(settings.vss_url) if settings.vss_enabled else MockVSSClient()

    is_healthy = await client.check_health()
    print(f"VSS Health Check: {'✅ ONLINE' if is_healthy else '⚠️ OFFLINE (Mocking Active)'}")

    print("\n1. Testing VIOS Video Ingestion...")
    ingest_res = await client.ingest_video("sample_match.mp4", "test_stream_01")
    print("Ingest Result:", ingest_res)

    print("\n2. Testing Dense Captioning skill...")
    captions = await client.get_dense_captions("test_stream_01", 0, 300000)
    print(f"Captions retrieved: {len(captions)}")
    if captions:
        print("Sample Caption:", captions[0])

    print("\n3. Testing vss-ask-video VLM Q&A...")
    answer = await client.ask_video("test_stream_01", 195000, "What is Neymar doing in this frame?")
    print("VLM Answer:", answer)

    print("\n✅ VSS skills test concluded successfully.")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
