from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cv2, threading, time, asyncio

# === 앱 생성 ===
app = FastAPI()
templates = Jinja2Templates(directory="video_server/templates")
app.mount("/static", StaticFiles(directory="video_server/static"), name="static")

# === 전역 변수 ===
camera = cv2.VideoCapture(0)
latest_frame = None
frame_lock = threading.Lock()
client_count = 0
client_count_lock = threading.Lock()


# === 프레임 수신 스레드 시작 ===
def update_frames():
    global latest_frame
    while True:
        if not camera.isOpened():
            print("⚠️ 카메라 연결 해제됨. 재시도 중...")
            time.sleep(1)
            camera.open(0)
            continue

        success, frame = camera.read()
        if success:
            with frame_lock:
                latest_frame = frame
        else:
            print("⚠️ 프레임 읽기 실패")
        time.sleep(0.03)


threading.Thread(target=update_frames, daemon=True).start()


# === MJPEG 스트림 ===
async def generate_mjpeg():
    global client_count
    with client_count_lock:
        client_count += 1
    print(f"🟢 클라이언트 접속됨: {client_count}")

    try:
        while True:
            with frame_lock:
                frame = latest_frame.copy() if latest_frame is not None else None

            if frame is not None:
                cv2.putText(
                    frame,
                    f"Clients: {client_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )
                _, buffer = cv2.imencode(".jpg", frame)
                try:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                except Exception as e:
                    print(f"⚠️ yield 중 오류 발생: {e}")
                    break
            await asyncio.sleep(0.03)
    except asyncio.CancelledError:
        print("🔻 클라이언트 연결 종료 감지됨")
        raise
    finally:
        with client_count_lock:
            client_count -= 1
        print(f"🔴 클라이언트 연결 해제됨: {client_count}")


# === 라우터 ===
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Connection": "close"},
    )


@app.get("/camera_info")
async def camera_info():
    w = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    return {"index": 0, "resolution": f"{int(w)}x{int(h)}"}


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")


# ... 기존 FastAPI 라우팅 및 app 정의 코드가 여기까지 구성되어 있어야 함 ...
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
