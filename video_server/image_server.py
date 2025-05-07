from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
import cv2
import asyncio

# === 초기 설정 ===
templates = Jinja2Templates(directory="video_server/templates")
UPLOAD_DIR = Path("video_server/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
uploaded_images = []  # 업로드된 이미지 경로 저장
active_connections = set()
broadcast_task = None


# === 업로드된 이미지 순차 송출 ===
async def video_broadcast():
    import time
    from datetime import datetime

    print("🖼️ 업로드 이미지 영상처럼 송출 시작")
    index = 0

    try:
        while True:
            if not uploaded_images:
                print("⏸️ 업로드 이미지 없음. 대기 중...")
                await asyncio.sleep(1.0)
                continue

            if not active_connections:
                await asyncio.sleep(0.5)
                continue

            image_path = uploaded_images[index % len(uploaded_images)]
            if not image_path.exists():
                print(f"❌ 존재하지 않는 이미지: {image_path}")
                await asyncio.sleep(0.5)
                continue

            frame = cv2.imread(str(image_path))
            if frame is None:
                print(f"❌ 이미지 읽기 실패: {image_path}")
                await asyncio.sleep(0.5)
                continue

            # 현재 시간 추가
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(
                frame,
                current_time,
                (10, 50),  # 텍스트 위치
                cv2.FONT_HERSHEY_SIMPLEX,
                1,  # 글자 크기
                (0, 255, 0),  # 글자 색상 (녹색)
                2,  # 글자 두께
                cv2.LINE_AA,
            )
            print("⏸️ 업로드 이미지 송출 중...")
            _, buffer = cv2.imencode(".jpg", frame)
            data = buffer.tobytes()
            del frame

            disconnected = set()
            for ws in list(active_connections):
                try:
                    await ws.send_bytes(data)
                except WebSocketDisconnect:
                    disconnected.add(ws)
                except Exception as e:
                    print(f"💥 송출 오류: {e}")
                    disconnected.add(ws)

            for ws in disconnected:
                active_connections.discard(ws)

            index += 1
            await asyncio.sleep(1.0)  # 1초 간격
    finally:
        print("🛑 이미지 송출 종료")


# === lifespan 관리 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global broadcast_task
    broadcast_task = asyncio.create_task(video_broadcast())
    yield
    broadcast_task.cancel()
    print("🛑 송출 태스크 종료")


# === FastAPI 앱 생성 ===
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="video_server/static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# === 이미지 업로드 처리 ===
@app.get("/upload")
async def upload_form(request: Request):
    return templates.TemplateResponse(
        "upload.html", {"request": request, "filename": None}
    )


@app.post("/upload")
async def upload_image(request: Request, file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    uploaded_images.append(file_path)
    print(f"✅ 이미지 업로드 완료: {file_path}")
    return templates.TemplateResponse(
        "upload.html", {"request": request, "filename": file.filename}
    )


# === WebSocket 엔드포인트 ===
@app.websocket("/ws/video")
async def video_feed_ws(websocket: WebSocket):
    await websocket.accept()
    print("🟡 WebSocket 수락됨 (이미지 송출)")
    try:
        while True:
            await websocket.receive_text()
            if websocket not in active_connections:
                active_connections.add(websocket)
                print(f"🟢 WebSocket 등록 ({len(active_connections)}명)")
    except WebSocketDisconnect:
        print("🔴 WebSocket 해제")
    finally:
        active_connections.discard(websocket)
        print(f"🔵 제거됨 ({len(active_connections)}명)")


# === 메인 페이지 ===
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# === 실행 ===
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
