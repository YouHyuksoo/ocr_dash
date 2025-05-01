import asyncio
import websockets


async def test_ws():
    try:
        print("🔌 연결 시도 중...")
        async with websockets.connect(
            "ws://127.0.0.1:8000/ws/video", open_timeout=3
        ) as ws:
            print("✅ 연결 성공")
    except Exception as e:
        print("❌ 연결 실패:", e)


asyncio.run(test_ws())
