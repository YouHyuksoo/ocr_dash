import sys
import os
import cv2
import asyncio
import time
import numpy as np
import websockets
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import load_settings_once
from state import state
from detector import detect_objects
from tracker import create_tracker, init_tracker, update_tracker
from motion_detector import detect_motion
from roi_checker import is_inside_roi, draw_roi, load_roi_settings
from ocr import run_ocr_on_bbox
from failure_manager import has_roi_timeout, exceeded_ocr_retries, reset_system

# === 전역 설정 ===
VIDEO_WS_URL = "ws://127.0.0.1:8000/ws/video"
ROI_BOX = load_roi_settings()
frame_queue = asyncio.Queue(maxsize=1)
templates = Jinja2Templates(directory="detection_server/templates")


# === WebSocket 프레임 수신 ===
async def receive_frames_from_ws():
    while True:
        try:
            async with websockets.connect(VIDEO_WS_URL, max_size=None) as ws:
                print("✅ WebSocket 영상 수신 연결됨")
                while True:
                    data = await ws.recv()
                    if isinstance(data, bytes):
                        frame = cv2.imdecode(
                            np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR
                        )
                        if frame is not None:
                            if frame_queue.full():
                                try:
                                    frame_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    pass
                            await frame_queue.put(frame)
                    await asyncio.sleep(0.001)
        except Exception as e:
            print(f"💥 WebSocket 연결 오류: {e}")
            await asyncio.sleep(1)


# === lifespan ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(receive_frames_from_ws())
    yield
    task.cancel()
    print("🛑 WebSocket 수신 종료")


# === FastAPI 앱 ===
app = FastAPI(lifespan=lifespan)


@app.get("/annotated_feed")
async def stream_video():
    async def frame_generator():
        while True:
            try:
                frame = await frame_queue.get()
                frame = draw_roi(frame)

                # === 감지 및 추적 ===
                # (이전 주석 처리된 감지/추적/ocr 블럭 그대로 복구 가능)

                _, buffer = cv2.imencode(".jpg", frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                await asyncio.sleep(0.03)
            except Exception as e:
                print(f"💥 프레임 처리 중 예외 발생: {e}")
                await asyncio.sleep(0.5)

    return StreamingResponse(
        frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010)
