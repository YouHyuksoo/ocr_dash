import sys
import os
import cv2
import asyncio
import time
import numpy as np
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
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
templates = Jinja2Templates(directory="detection_server/templates")
active_ws = set()
frame_queue = asyncio.Queue(maxsize=1)


# === WebSocket 프레임 수신 ===
async def receive_frames_from_ws():
    global frame_queue
    while True:
        try:
            print("🔌 WebSocket 연결 시도 중...")
            async with websockets.connect(VIDEO_WS_URL, max_size=None) as ws:
                print("✅ WebSocket 연결 성공 → ping 전송")
                await ws.send("ping")
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


# === 분석 프레임 송출 ===
async def broadcast_annotated_frames():
    while True:
        try:
            frame = await frame_queue.get()
            frame = draw_roi(frame)

            if state["mode"] == "idle":
                if detect_motion(frame):
                    cv2.putText(
                        frame,
                        "Motion On",
                        (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 255, 0),
                        2,
                    )
                    bbox = detect_objects(frame)
                    if bbox:
                        tracker = create_tracker()
                        if init_tracker(tracker, frame, bbox):
                            state.update(
                                {
                                    "mode": "tracking",
                                    "tracker": tracker,
                                    "bbox": bbox,
                                    "start_time": time.time(),
                                    "roi_enter_time": None,
                                    "ocr_attempts": 0,
                                    "ocr_done": False,
                                    "ocr_result": None,
                                    "failure_message": None,
                                }
                            )
                    else:
                        print("❌ 객체 감지 실패")
                        state["failure_message"] = "객체 감지 실패"
                        reset_system()
                else:
                    cv2.putText(
                        frame,
                        "Motion Off",
                        (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 0, 255),
                        2,
                    )

            elif state["mode"] == "tracking":
                tracker = state["tracker"]
                success, bbox = update_tracker(tracker, frame)
                if success:
                    state["bbox"] = bbox
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    if is_inside_roi(bbox):
                        if not state["ocr_done"]:
                            state["roi_enter_time"] = (
                                state["roi_enter_time"] or time.time()
                            )
                            ocr_result = run_ocr_on_bbox(frame, bbox)
                            state["ocr_attempts"] += 1
                            if ocr_result:
                                state["ocr_result"] = ocr_result
                                state["ocr_done"] = True
                                print(f"✅ OCR 성공: {ocr_result}")
                            elif exceeded_ocr_retries():
                                print("❌ OCR 최대 시도 실패")
                                state["failure_message"] = "OCR 실패"
                                reset_system()
                    else:
                        if has_roi_timeout():
                            print("⌛ ROI 진입 실패")
                            state["failure_message"] = "ROI 진입 실패"
                            reset_system()
                else:
                    print("❌ 추적 실패")
                    state["failure_message"] = "추적 실패"
                    reset_system()

                if state["ocr_result"]:
                    cv2.putText(
                        frame,
                        f"OCR: {state['ocr_result']}",
                        (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 255, 0),
                        2,
                    )
                elif state["failure_message"]:
                    cv2.putText(
                        frame,
                        state["failure_message"],
                        (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 0, 255),
                        2,
                    )

            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                print("⚠️ 분석 프레임 인코딩 실패")
                continue
            data = buffer.tobytes()

            for ws in list(active_ws):
                try:
                    await ws.send_bytes(data)
                    # print(f"📤 분석 프레임 송출 ({len(data)} bytes)")
                except:
                    active_ws.discard(ws)

            await asyncio.sleep(0.03)
        except Exception as e:
            print(f"💥 분석 프레임 처리 중 예외: {e}")
            await asyncio.sleep(0.5)


# === lifespan ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    t1 = asyncio.create_task(receive_frames_from_ws())
    t2 = asyncio.create_task(broadcast_annotated_frames())
    yield
    t1.cancel()
    t2.cancel()
    print("🛑 수신/송출 태스크 종료")


# === FastAPI 앱 정의 ===
app = FastAPI(lifespan=lifespan)


# === WebSocket 라우트 ===
@app.websocket("/ws/annotated")
async def ws_annotated(websocket: WebSocket):
    await websocket.accept()
    active_ws.add(websocket)
    print(f"🧠 분석 WebSocket 연결됨 ({len(active_ws)}명)")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        active_ws.discard(websocket)
        print(f"🔴 분석 WebSocket 해제됨 ({len(active_ws)}명)")


@app.websocket("/ws/pass_through")
async def ws_pass_through(websocket: WebSocket):
    await websocket.accept()
    print("🧪 pass_through WebSocket 연결됨")
    try:
        while True:
            frame = await frame_queue.get()
            if frame is None:
                continue
            success, buffer = cv2.imencode(".jpg", frame)
            if success:
                await websocket.send_bytes(buffer.tobytes())
                # print(f"📤 pass_through 송출 ({len(buffer.tobytes())} bytes)")
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        print("🔴 pass_through WebSocket 연결 해제됨")


# === 템플릿 UI 라우트 ===
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# === 독립 실행 구문 ===
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010)
