from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import cv2, asyncio
import psutil  # 메모리 사용량 측정을 위한 라이브러리 추가

# === 앱 초기화 ===
templates = Jinja2Templates(directory="video_server/templates")
active_connections = set()
broadcast_task = None


# === WebSocket으로 프레임 송출 ===
async def video_broadcast():
    import time

    # 복구 관련 변수
    consecutive_failures = 0
    max_consecutive_failures = 5
    last_reconnect_time = time.time()
    reconnect_interval = 10  # 재연결 시도 간격(초)

    # 카메라 초기화 함수
    def init_camera():
        nonlocal cap
        if cap is not None:
            cap.release()  # 기존 카메라 리소스 해제

        cap = cv2.VideoCapture(0)
        # 카메라 속성 설정 (필요시)
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return cap.isOpened()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("🚨 카메라 열기 실패")
        return

    print("📷 카메라 송출 시작됨")
    process = psutil.Process()  # 현재 프로세스 객체 가져오기
    try:
        while True:
            # 클라이언트가 없으면 프레임 처리 생략
            if not active_connections:
                print("⏸️ 모든 클라이언트가 연결 해제됨. 대기 중...", flush=True)
                await asyncio.sleep(0.5)
                continue

            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                print(
                    f"⚠️ 프레임 읽기 실패 ({consecutive_failures}/{max_consecutive_failures})"
                )

                # 연속 실패 횟수가 임계값을 초과하면 카메라 재연결 시도
                if consecutive_failures >= max_consecutive_failures:
                    current_time = time.time()
                    if current_time - last_reconnect_time > reconnect_interval:
                        print("🔄 카메라 재연결 시도...")
                        if init_camera():
                            print("✅ 카메라 재연결 성공")
                            consecutive_failures = 0
                            last_reconnect_time = current_time
                        else:
                            print("❌ 카메라 재연결 실패")

                # 실패 후 대기 (연속 실패가 많을수록 대기 시간 증가)
                await asyncio.sleep(min(0.1 * consecutive_failures, 2.0))
                continue

            # 프레임 읽기 성공 시 연속 실패 카운터 초기화
            consecutive_failures = 0

            # 메모리 사용량 측정
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # MB 단위로 변환

            # 프레임 처리 및 전송
            cv2.putText(
                frame,
                f"Clients: {len(active_connections)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            # 메모리 사용량 표시 추가
            cv2.putText(
                frame,
                f"Memory: {memory_mb:.1f} MB",
                (10, 70),  # 위치를 아래로 조정
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            _, buffer = cv2.imencode(".jpg", frame)
            data = buffer.tobytes()

            # 참조 즉시 해제하여 메모리 회수 촉진
            del frame

            # 클라이언트별 송신 처리
            disconnected = set()
            for ws in list(active_connections):  # 복사본 사용
                try:
                    await ws.send_bytes(data)
                except WebSocketDisconnect:
                    print("🔴 WebSocket 연결 해제됨")
                    disconnected.add(ws)
                except Exception as e:
                    print(f"💥 송신 중 예외 발생: {e}")
                    disconnected.add(ws)

            # 연결 해제된 클라이언트 제거
            for ws in disconnected:
                active_connections.discard(ws)

            await asyncio.sleep(0.03)
    finally:
        cap.release()
        print("🛑 카메라 리소스 해제 완료")


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
    print("🟡 WebSocket 수락됨 (ping 대기 중...)")
    try:
        while True:
            await websocket.receive_text()  # ping 메시지 대기
            if websocket not in active_connections:  # 아직 추가되지 않았다면 추가
                active_connections.add(websocket)
                print(
                    f"🟢 WebSocket ping 수신 - 접속 등록됨 ({len(active_connections)}명)"
                )
    except WebSocketDisconnect:
        print("🔴 WebSocket 연결 해제됨")
    finally:
        active_connections.discard(websocket)
        print(f"🔵 WebSocket 연결 제거됨 (총 {len(active_connections)}명)")


# === HTTP 라우터 ===
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# @app.get("/favicon.ico")
# async def favicon():
#     return RedirectResponse(url="/static/favicon.ico")

# === 실행 ===
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
