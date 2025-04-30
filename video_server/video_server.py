from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import cv2, asyncio

# === 앱 초기화 ===
templates = Jinja2Templates(directory="video_server/templates")
active_connections = set()
broadcast_task = None


# === WebSocket으로 프레임 송출 ===
async def video_broadcast():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("🚨 카메라 열기 실패")
        return

    print("📷 카메라 송출 시작됨")
    while True:
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.05)
            continue

        # ✅ 접속자 수 표시
        cv2.putText(
            frame,
            f"Clients: {len(active_connections)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        _, buffer = cv2.imencode(".jpg", frame)
        data = buffer.tobytes()

        disconnected = set()
        for ws in active_connections:
            try:
                await ws.send_bytes(data)
            except WebSocketDisconnect:
                disconnected.add(ws)
            except Exception as e:
                print(f"💥 송신 중 예외 발생: {e}")
                disconnected.add(ws)

        active_connections.difference_update(disconnected)
        await asyncio.sleep(0.03)


# === lifespan 기반 프레임 수신 태스크 관리 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global broadcast_task
    broadcast_task = asyncio.create_task(video_broadcast())
    yield
    broadcast_task.cancel()
    print("🛑 영상 송출 태스크 종료")


# === FastAPI 앱 ===
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="video_server/static"), name="static")


# === WebSocket 엔드포인트 ===
@app.websocket("/ws/video")
async def video_feed_ws(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    print(f"🟢 WebSocket 연결됨 (총 {len(active_connections)}명)")
    try:
        while True:
            await websocket.receive_text()  # ping 유지용
    except WebSocketDisconnect:
        print("🔴 WebSocket 연결 해제됨")
    finally:
        active_connections.discard(websocket)


# === HTTP 라우터 ===
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")


# === 실행 ===
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
