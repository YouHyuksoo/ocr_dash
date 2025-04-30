import sys
import os
import cv2
import asyncio
import time
import uvicorn

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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
VIDEO_URL = "http://127.0.0.1:8000/video_feed"
cap = None
ROI_BOX = load_roi_settings()


# === 앱 수명 주기: 최초 영상 연결 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cap
    for _ in range(30):  # 최대 3초간 재시도
        cap = cv2.VideoCapture(VIDEO_URL)
        if cap.isOpened():
            print("✅ 최초 영상 수신 연결 성공")
            break
        print("❌ 영상 연결 실패... 재시도 중")
        await asyncio.sleep(0.1)
    else:
        print("🚨 최초 영상 연결 실패")

    yield
    if cap:
        cap.release()
        print("📷 Video feed 종료")


# === FastAPI 앱 ===
app = FastAPI(lifespan=lifespan)


@app.get("/annotated_feed")
async def stream_video():
    async def frame_generator():
        global cap
        fail_count = 0
        MAX_FAIL_COUNT = 30  # 30 프레임 이상 실패 시 재연결 시도

        while True:
            try:
                success, frame = cap.read()
                if not success:
                    fail_count += 1
                    print(f"⚠️ 프레임 수신 실패 ({fail_count})")
                    await asyncio.sleep(0.1)

                    if fail_count >= MAX_FAIL_COUNT:
                        print("🔄 영상 재연결 시도...")
                        cap.release()
                        for _ in range(10):
                            cap = cv2.VideoCapture(VIDEO_URL)
                            if cap.isOpened():
                                print("✅ 영상 재연결 성공")
                                fail_count = 0
                                break
                            print("⏳ 재연결 대기 중...")
                            await asyncio.sleep(0.2)
                    continue

                fail_count = 0  # 정상 수신 시 실패 카운트 초기화
                frame = draw_roi(frame)

                # # === 감지 및 추적 ===
                # if state["mode"] == "idle":
                #     if detect_motion(frame):
                #         bbox = detect_objects(frame)
                #         if bbox:
                #             tracker = create_tracker()
                #             if init_tracker(tracker, frame, bbox):
                #                 state.update(
                #                     {
                #                         "mode": "tracking",
                #                         "tracker": tracker,
                #                         "bbox": bbox,
                #                         "start_time": time.time(),
                #                         "roi_enter_time": None,
                #                         "ocr_attempts": 0,
                #                         "ocr_done": False,
                #                         "ocr_result": None,
                #                         "failure_message": None,
                #                     }
                #                 )
                #         else:
                #             print("❌ 객체 감지 실패")
                #             state["failure_message"] = "객체 감지 실패"
                #             reset_system()

                # elif state["mode"] == "tracking":
                #     tracker = state["tracker"]
                #     success, bbox = update_tracker(tracker, frame)
                #     if success:
                #         state["bbox"] = bbox
                #         x, y, w, h = [int(v) for v in bbox]
                #         cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

                #         if is_inside_roi(bbox):
                #             if not state["ocr_done"]:
                #                 state["roi_enter_time"] = (
                #                     state["roi_enter_time"] or time.time()
                #                 )
                #                 ocr_result = run_ocr_on_bbox(frame, bbox)
                #                 state["ocr_attempts"] += 1
                #                 if ocr_result:
                #                     state["ocr_result"] = ocr_result
                #                     state["ocr_done"] = True
                #                     print(f"✅ OCR 성공: {ocr_result}")
                #                 elif exceeded_ocr_retries():
                #                     print("❌ OCR 최대 시도 실패")
                #                     state["failure_message"] = "OCR 실패"
                #                     reset_system()
                #         else:
                #             if has_roi_timeout():
                #                 print("⌛ ROI 진입 실패")
                #                 state["failure_message"] = "ROI 진입 실패"
                #                 reset_system()
                #     else:
                #         print("❌ 추적 실패")
                #         state["failure_message"] = "추적 실패"
                #         reset_system()

                # # === 프레임에 상태 표시 ===
                # if state["ocr_result"]:
                #     cv2.putText(
                #         frame,
                #         f"OCR: {state['ocr_result']}",
                #         (10, 40),
                #         cv2.FONT_HERSHEY_SIMPLEX,
                #         1.2,
                #         (0, 255, 0),
                #         2,
                #     )
                # elif state["failure_message"]:
                #     cv2.putText(
                #         frame,
                #         state["failure_message"],
                #         (10, 40),
                #         cv2.FONT_HERSHEY_SIMPLEX,
                #         1.2,
                #         (0, 0, 255),
                #         2,
                #     )

                _, buffer = cv2.imencode(".jpg", frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                await asyncio.sleep(0.03)

            except Exception as e:
                print(f"💥 프레임 처리 중 예외 발생: {e}")
                await asyncio.sleep(0.5)

    return StreamingResponse(
        frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ... 기존 FastAPI 라우팅 및 app 정의 코드가 여기까지 구성되어 있어야 함 ...
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010)
