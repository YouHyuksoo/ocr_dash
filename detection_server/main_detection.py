# import sys
# import os
# import cv2
# import asyncio
# import time
# import numpy as np
# import websockets
# from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
# from fastapi.templating import Jinja2Templates
# from contextlib import asynccontextmanager

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from settings import load_settings_once
# from state import state
# from detector import detect_objects
# from tracker import create_tracker, init_tracker, update_tracker
# from motion_detector import detect_motion
# from roi_checker import is_inside_roi, draw_roi, load_roi_settings
# from ocr import run_ocr_on_bbox
# from failure_manager import has_roi_timeout, exceeded_ocr_retries, reset_system

# # === 전역 설정 ===
# VIDEO_WS_URL = "ws://127.0.0.1:8000/ws/video"
# ROI_BOX = load_roi_settings()
# templates = Jinja2Templates(directory="detection_server/templates")
# frame_queue = asyncio.Queue(maxsize=1)
# active_ws = set()
# active_pass_ws = set()


# # === WebSocket 프레임 수신 ===
# async def receive_frames_from_ws():
#     while True:
#         try:
#             print("🔌 WebSocket 연결 시도 중...")
#             async with websockets.connect(VIDEO_WS_URL, max_size=None) as ws:
#                 print("✅ WebSocket 연결 성공 → ping 전송")
#                 await ws.send("ping")
#                 while True:
#                     data = await ws.recv()
#                     if isinstance(data, bytes):
#                         frame = cv2.imdecode(
#                             np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR
#                         )
#                         if frame is not None:
#                             if frame_queue.full():
#                                 try:
#                                     frame_queue.get_nowait()
#                                 except asyncio.QueueEmpty:
#                                     pass
#                             await frame_queue.put(frame)
#                     await asyncio.sleep(0.001)
#         except Exception as e:
#             print(f"💥 WebSocket 연결 오류: {e}")
#             await asyncio.sleep(1)


# # === 통합된 프레임 처리 및 브로드캐스트 함수 ===
# async def process_and_broadcast_frames():
#     while True:
#         try:
#             # 큐에서 프레임 가져오기
#             frame = await frame_queue.get()

#             # 큐에 더 많은 프레임이 있으면 최신 것만 사용
#             while not frame_queue.empty():
#                 try:
#                     frame = frame_queue.get_nowait()
#                 except asyncio.QueueEmpty:
#                     break

#             # 분석용 프레임 처리 (원본 프레임은 보존)
#             annotated_frame = frame.copy()
#             annotated_frame = draw_roi(annotated_frame)

#             # 상태에 따른 처리
#             if state["mode"] == "idle":
#                 if detect_motion(annotated_frame):
#                     cv2.putText(
#                         annotated_frame,
#                         "Motion On",
#                         (10, 120),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 255, 0),
#                         2,
#                     )
#                     bbox = detect_objects(annotated_frame)
#                     if bbox:
#                         tracker = create_tracker()
#                         if init_tracker(tracker, annotated_frame, bbox):
#                             state.update(
#                                 {
#                                     "mode": "tracking",
#                                     "tracker": tracker,
#                                     "bbox": bbox,
#                                     "start_time": time.time(),
#                                     "roi_enter_time": None,
#                                     "ocr_attempts": 0,
#                                     "ocr_done": False,
#                                     "ocr_result": None,
#                                     "failure_message": None,
#                                 }
#                             )
#                     else:
#                         print("❌ 객체 감지 실패")
#                         state["failure_message"] = "객체 감지 실패"
#                         reset_system()
#                 else:
#                     cv2.putText(
#                         annotated_frame,
#                         "Motion Off",
#                         (10, 120),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 0, 255),
#                         2,
#                     )

#             elif state["mode"] == "tracking":
#                 tracker = state["tracker"]
#                 success, bbox = update_tracker(tracker, annotated_frame)
#                 if success:
#                     state["bbox"] = bbox
#                     x, y, w, h = [int(v) for v in bbox]
#                     cv2.rectangle(
#                         annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 2
#                     )
#                     if is_inside_roi(bbox):
#                         if not state["ocr_done"]:
#                             state["roi_enter_time"] = (
#                                 state["roi_enter_time"] or time.time()
#                             )
#                             ocr_result = run_ocr_on_bbox(annotated_frame, bbox)
#                             state["ocr_attempts"] += 1
#                             if ocr_result:
#                                 state["ocr_result"] = ocr_result
#                                 state["ocr_done"] = True
#                                 print(f"✅ OCR 성공: {ocr_result}")
#                             elif exceeded_ocr_retries():
#                                 print("❌ OCR 최대 시도 실패")
#                                 state["failure_message"] = "OCR 실패"
#                                 reset_system()
#                     else:
#                         if has_roi_timeout():
#                             print("⌛ ROI 진입 실패")
#                             state["failure_message"] = "ROI 진입 실패"
#                             reset_system()
#                 else:
#                     print("❌ 추적 실패")
#                     state["failure_message"] = "추적 실패"
#                     reset_system()

#                 if state["ocr_result"]:
#                     cv2.putText(
#                         annotated_frame,
#                         f"OCR: {state['ocr_result']}",
#                         (10, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 255, 0),
#                         2,
#                     )
#                 elif state["failure_message"]:
#                     cv2.putText(
#                         annotated_frame,
#                         state["failure_message"],
#                         (10, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 0, 255),
#                         2,
#                     )

#             # 분석 프레임 인코딩 및 전송
#             if active_ws:
#                 success, buffer = cv2.imencode(".jpg", annotated_frame)
#                 if success:
#                     data = buffer.tobytes()
#                     for ws in list(active_ws):
#                         try:
#                             await ws.send_bytes(data)
#                         except:
#                             active_ws.discard(ws)

#             # 원본 프레임 인코딩 및 전송
#             if active_pass_ws:
#                 success, buffer = cv2.imencode(".jpg", frame)
#                 if success:
#                     data = buffer.tobytes()
#                     for ws in list(active_pass_ws):
#                         try:
#                             await ws.send_bytes(data)
#                         except:
#                             active_pass_ws.discard(ws)

#             await asyncio.sleep(0.03)
#         except Exception as e:
#             print(f"💥 프레임 처리 예외: {e}")
#             await asyncio.sleep(0.5)


# # === FastAPI lifespan ===
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # 프레임 수신 태스크
#     t1 = asyncio.create_task(receive_frames_from_ws())
#     # 통합된 프레임 처리 및 송출 태스크
#     t2 = asyncio.create_task(process_and_broadcast_frames())

#     yield

#     # 태스크 정리
#     t1.cancel()
#     t2.cancel()

#     try:
#         await t1
#     except asyncio.CancelledError:
#         pass

#     try:
#         await t2
#     except asyncio.CancelledError:
#         pass

#     print("🛑 수신/송출 태스크 종료")


# # === FastAPI 앱 정의
# app = FastAPI(lifespan=lifespan)


# # === WebSocket 라우트
# @app.websocket("/ws/annotated")
# async def ws_annotated(websocket: WebSocket):
#     await websocket.accept()
#     active_ws.add(websocket)
#     print(f"🧠 분석 WebSocket 연결됨 ({len(active_ws)}명)")
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     finally:
#         active_ws.discard(websocket)
#         print(f"🔴 분석 WebSocket 해제됨 ({len(active_ws)}명)")


# @app.websocket("/ws/pass_through")
# async def ws_pass_through(websocket: WebSocket):
#     await websocket.accept()
#     active_pass_ws.add(websocket)
#     print(f"🧪 pass_through WebSocket 연결됨 ({len(active_pass_ws)}명)")
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     finally:
#         active_pass_ws.discard(websocket)
#         print(f"🔴 pass_through WebSocket 해제됨 ({len(active_pass_ws)}명)")


# # === 템플릿 렌더링
# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


# # === 실행 구문
# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="127.0.0.1", port=8010)
# import sys
# import os
# import cv2
# import asyncio
# import time
# import numpy as np
# import websockets
# import gc  # [🔧 추가] 명시적인 메모리 수거

# from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
# from fastapi.templating import Jinja2Templates
# from contextlib import asynccontextmanager

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from settings import load_settings_once
# from state import state
# from detector import detect_objects
# from tracker import create_tracker, init_tracker, update_tracker
# from motion_detector import detect_motion
# from roi_checker import is_inside_roi, draw_roi, load_roi_settings
# from ocr import run_ocr_on_bbox
# from failure_manager import has_roi_timeout, exceeded_ocr_retries, reset_system

# # === 전역 설정 ===
# VIDEO_WS_URL = "ws://127.0.0.1:8000/ws/video"
# ROI_BOX = load_roi_settings()
# templates = Jinja2Templates(directory="detection_server/templates")
# frame_queue = asyncio.Queue(maxsize=1)
# active_ws = set()
# active_pass_ws = set()


# # === WebSocket 프레임 수신 ===
# async def receive_frames_from_ws():
#     while True:
#         try:
#             print("🔌 WebSocket 연결 시도 중...")
#             async with websockets.connect(VIDEO_WS_URL, max_size=None) as ws:
#                 print("✅ WebSocket 연결 성공 → ping 전송")
#                 await ws.send("ping")
#                 while True:
#                     data = await ws.recv()
#                     if isinstance(data, bytes):
#                         frame = cv2.imdecode(
#                             np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR
#                         )
#                         if frame is not None:
#                             # [🔧 변경] 큐에 남은 오래된 프레임은 버림 (최신 프레임만 유지)
#                             while not frame_queue.empty():
#                                 try:
#                                     frame_queue.get_nowait()
#                                 except asyncio.QueueEmpty:
#                                     break
#                             await frame_queue.put(frame)
#                     await asyncio.sleep(0.001)  # [안정성] 이벤트 루프 잠시 양보
#         except Exception as e:
#             print(f"💥 WebSocket 연결 오류: {e}")
#             await asyncio.sleep(1)


# # === 프레임 처리 및 송출 통합 ===
# async def process_and_broadcast_frames():
#     frame_counter = 0  # [🔧 추가] gc 주기 조절을 위한 카운터

#     while True:
#         try:
#             frame = await frame_queue.get()

#             # [🔧 변경] 큐 내 최신 프레임으로 갱신
#             while not frame_queue.empty():
#                 try:
#                     frame = frame_queue.get_nowait()
#                 except asyncio.QueueEmpty:
#                     break

#             annotated_frame = frame.copy()
#             annotated_frame = draw_roi(annotated_frame)

#             # === 상태 기반 처리 ===
#             if state["mode"] == "idle":
#                 if detect_motion(annotated_frame):
#                     cv2.putText(
#                         annotated_frame,
#                         "Motion On",
#                         (10, 120),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 255, 0),
#                         2,
#                     )
#                     bbox = detect_objects(annotated_frame)
#                     if bbox:
#                         tracker = create_tracker()
#                         if init_tracker(tracker, annotated_frame, bbox):
#                             state.update(
#                                 {
#                                     "mode": "tracking",
#                                     "tracker": tracker,
#                                     "bbox": bbox,
#                                     "start_time": time.time(),
#                                     "roi_enter_time": None,
#                                     "ocr_attempts": 0,
#                                     "ocr_done": False,
#                                     "ocr_result": None,
#                                     "failure_message": None,
#                                 }
#                             )
#                     else:
#                         print("❌ 객체 감지 실패")
#                         state["failure_message"] = "객체 감지 실패"
#                         reset_system()
#                 else:
#                     cv2.putText(
#                         annotated_frame,
#                         "Motion Off",
#                         (10, 120),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 0, 255),
#                         2,
#                     )

#             elif state["mode"] == "tracking":
#                 tracker = state["tracker"]
#                 success, bbox = update_tracker(tracker, annotated_frame)
#                 if success:
#                     state["bbox"] = bbox
#                     x, y, w, h = [int(v) for v in bbox]
#                     cv2.rectangle(
#                         annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 2
#                     )

#                     if is_inside_roi(bbox) and not state["ocr_done"]:
#                         state["roi_enter_time"] = state["roi_enter_time"] or time.time()
#                         ocr_result = run_ocr_on_bbox(annotated_frame, bbox)
#                         state["ocr_attempts"] += 1
#                         if ocr_result:
#                             state["ocr_result"] = ocr_result
#                             state["ocr_done"] = True
#                             print(f"✅ OCR 성공: {ocr_result}")
#                         elif exceeded_ocr_retries():
#                             print("❌ OCR 최대 시도 실패")
#                             state["failure_message"] = "OCR 실패"
#                             reset_system()
#                     elif has_roi_timeout():
#                         print("⌛ ROI 진입 실패")
#                         state["failure_message"] = "ROI 진입 실패"
#                         reset_system()
#                 else:
#                     print("❌ 추적 실패")
#                     state["failure_message"] = "추적 실패"
#                     reset_system()

#                 if state["ocr_result"]:
#                     cv2.putText(
#                         annotated_frame,
#                         f"OCR: {state['ocr_result']}",
#                         (10, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 255, 0),
#                         2,
#                     )
#                 elif state["failure_message"]:
#                     cv2.putText(
#                         annotated_frame,
#                         state["failure_message"],
#                         (10, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 0, 255),
#                         2,
#                     )

#             # === 분석 프레임 전송
#             if active_ws:
#                 success, buffer = cv2.imencode(".jpg", annotated_frame)
#                 if success:
#                     data = buffer.tobytes()
#                     for ws in list(active_ws):
#                         try:
#                             await ws.send_bytes(data)
#                         except:
#                             await ws.close()  # [🔧 변경] 안전하게 종료
#                             active_ws.discard(ws)

#             # === 원본 프레임 전송
#             if active_pass_ws:
#                 success, buffer = cv2.imencode(".jpg", frame)
#                 if success:
#                     data = buffer.tobytes()
#                     for ws in list(active_pass_ws):
#                         try:
#                             await ws.send_bytes(data)
#                         except:
#                             await ws.close()  # [🔧 변경] 안전하게 종료
#                             active_pass_ws.discard(ws)

#             # === 메모리 정리: 일정 주기마다 강제 GC 실행
#             frame_counter += 1
#             if frame_counter % 100 == 0:
#                 del annotated_frame, buffer, frame, data
#                 gc.collect()

#             await asyncio.sleep(0.03)

#         except Exception as e:
#             print(f"💥 프레임 처리 예외: {e}")
#             await asyncio.sleep(0.5)


# # === FastAPI lifespan ===
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     t1 = asyncio.create_task(receive_frames_from_ws())
#     t2 = asyncio.create_task(process_and_broadcast_frames())

#     yield

#     t1.cancel()
#     t2.cancel()

#     try:
#         await t1
#     except asyncio.CancelledError:
#         pass

#     try:
#         await t2
#     except asyncio.CancelledError:
#         pass

#     print("🛑 수신/송출 태스크 종료")


# # === FastAPI 앱 정의
# app = FastAPI(lifespan=lifespan)


# # === WebSocket 라우트
# @app.websocket("/ws/annotated")
# async def ws_annotated(websocket: WebSocket):
#     await websocket.accept()
#     active_ws.add(websocket)
#     print(f"🧠 분석 WebSocket 연결됨 ({len(active_ws)}명)")
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     finally:
#         active_ws.discard(websocket)
#         print(f"🔴 분석 WebSocket 해제됨 ({len(active_ws)}명)")


# @app.websocket("/ws/pass_through")
# async def ws_pass_through(websocket: WebSocket):
#     await websocket.accept()
#     active_pass_ws.add(websocket)
#     print(f"🧪 pass_through WebSocket 연결됨 ({len(active_pass_ws)}명)")
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     finally:
#         active_pass_ws.discard(websocket)
#         print(f"🔴 pass_through WebSocket 해제됨 ({len(active_pass_ws)}명)")


# # === 템플릿 렌더링
# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


# # === 실행 구문
# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="127.0.0.1", port=8010)
# import sys
# import os
# import cv2
# import asyncio
# import time
# import numpy as np
# import websockets
# import gc

# from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
# from fastapi.templating import Jinja2Templates
# from contextlib import asynccontextmanager

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from settings import load_settings_once
# from state import state
# from detector import detect_objects
# from tracker import create_tracker, init_tracker, update_tracker
# from motion_detector import detect_motion
# from roi_checker import is_inside_roi, draw_roi, load_roi_settings
# from ocr import run_ocr_on_bbox
# from failure_manager import has_roi_timeout, exceeded_ocr_retries, reset_system

# # === 전역 설정 ===
# VIDEO_WS_URL = "ws://127.0.0.1:8000/ws/video"
# ROI_BOX = load_roi_settings()
# templates = Jinja2Templates(directory="detection_server/templates")
# frame_queue = asyncio.Queue(maxsize=1)
# active_ws = set()
# active_pass_ws = set()


# # === WebSocket 프레임 수신 ===
# async def receive_frames_from_ws():
#     while True:
#         try:
#             print("🔌 WebSocket 연결 시도 중...")
#             async with websockets.connect(VIDEO_WS_URL, max_size=None) as ws:
#                 print("✅ WebSocket 연결 성공 → ping 전송")
#                 await ws.send("ping")
#                 while True:
#                     data = await ws.recv()
#                     if isinstance(data, bytes):
#                         frame = cv2.imdecode(
#                             np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR
#                         )
#                         if frame is not None:
#                             while not frame_queue.empty():
#                                 try:
#                                     frame_queue.get_nowait()
#                                 except asyncio.QueueEmpty:
#                                     break
#                             await frame_queue.put(frame)
#                     await asyncio.sleep(0.001)
#         except Exception as e:
#             print(f"💥 WebSocket 연결 오류: {e}")
#             await asyncio.sleep(1)


# # === 프레임 처리 및 송출 ===
# async def process_and_broadcast_frames():
#     frame_counter = 0

#     while True:
#         buffer_annotated = None
#         buffer_original = None
#         data_annotated = None
#         data_original = None

#         try:
#             frame = await frame_queue.get()
#             while not frame_queue.empty():
#                 try:
#                     frame = frame_queue.get_nowait()
#                 except asyncio.QueueEmpty:
#                     break

#             annotated_frame = frame.copy()
#             annotated_frame = draw_roi(annotated_frame)

#             if state["mode"] == "idle":
#                 if detect_motion(annotated_frame):
#                     cv2.putText(
#                         annotated_frame,
#                         "Motion On",
#                         (10, 120),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 255, 0),
#                         2,
#                     )
#                     bbox = detect_objects(annotated_frame)
#                     if bbox:
#                         tracker = create_tracker()
#                         if init_tracker(tracker, annotated_frame, bbox):
#                             state.update(
#                                 {
#                                     "mode": "tracking",
#                                     "tracker": tracker,
#                                     "bbox": bbox,
#                                     "start_time": time.time(),
#                                     "roi_enter_time": None,
#                                     "ocr_attempts": 0,
#                                     "ocr_done": False,
#                                     "ocr_result": None,
#                                     "failure_message": None,
#                                 }
#                             )
#                     else:
#                         print("❌ 객체 감지 실패")
#                         state["failure_message"] = "객체 감지 실패"
#                         reset_system()
#                 else:
#                     cv2.putText(
#                         annotated_frame,
#                         "Motion Off",
#                         (10, 120),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 0, 255),
#                         2,
#                     )

#             elif state["mode"] == "tracking":
#                 tracker = state["tracker"]
#                 success, bbox = update_tracker(tracker, annotated_frame)
#                 if success:
#                     state["bbox"] = bbox
#                     x, y, w, h = [int(v) for v in bbox]
#                     cv2.rectangle(
#                         annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 2
#                     )

#                     if is_inside_roi(bbox) and not state["ocr_done"]:
#                         state["roi_enter_time"] = state["roi_enter_time"] or time.time()
#                         ocr_result = run_ocr_on_bbox(annotated_frame, bbox)
#                         state["ocr_attempts"] += 1
#                         if ocr_result:
#                             state["ocr_result"] = ocr_result
#                             state["ocr_done"] = True
#                             print(f"✅ OCR 성공: {ocr_result}")
#                         elif exceeded_ocr_retries():
#                             print("❌ OCR 최대 시도 실패")
#                             state["failure_message"] = "OCR 실패"
#                             reset_system()
#                     elif has_roi_timeout():
#                         print("⌛ ROI 진입 실패")
#                         state["failure_message"] = "ROI 진입 실패"
#                         reset_system()
#                 else:
#                     print("❌ 추적 실패")
#                     state["failure_message"] = "추적 실패"
#                     reset_system()

#                 if state["ocr_result"]:
#                     cv2.putText(
#                         annotated_frame,
#                         f"OCR: {state['ocr_result']}",
#                         (10, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 255, 0),
#                         2,
#                     )
#                 elif state["failure_message"]:
#                     cv2.putText(
#                         annotated_frame,
#                         state["failure_message"],
#                         (10, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2,
#                         (0, 0, 255),
#                         2,
#                     )

#             # 분석 프레임 인코딩 및 전송
#             if active_ws:
#                 success, buffer_annotated = cv2.imencode(".jpg", annotated_frame)
#                 if success:
#                     data_annotated = buffer_annotated.tobytes()
#                     for ws in list(active_ws):
#                         try:
#                             await ws.send_bytes(data_annotated)
#                         except:
#                             await ws.close()
#                             active_ws.discard(ws)

#             # 원본 프레임 인코딩 및 전송
#             if active_pass_ws:
#                 success, buffer_original = cv2.imencode(".jpg", frame)
#                 if success:
#                     data_original = buffer_original.tobytes()
#                     for ws in list(active_pass_ws):
#                         try:
#                             await ws.send_bytes(data_original)
#                         except:
#                             await ws.close()
#                             active_pass_ws.discard(ws)

#             # 메모리 정리
#             frame_counter += 1
#             if frame_counter % 100 == 0:
#                 for var in [
#                     buffer_annotated,
#                     buffer_original,
#                     data_annotated,
#                     data_original,
#                     annotated_frame,
#                     frame,
#                 ]:
#                     if var is not None:
#                         del var
#                 gc.collect()

#             await asyncio.sleep(0.03)

#         except Exception as e:
#             print(f"💥 프레임 처리 예외: {e}")
#             await asyncio.sleep(0.5)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     t1 = asyncio.create_task(receive_frames_from_ws())
#     t2 = asyncio.create_task(process_and_broadcast_frames())
#     yield
#     t1.cancel()
#     t2.cancel()
#     try:
#         await t1
#     except asyncio.CancelledError:
#         pass
#     try:
#         await t2
#     except asyncio.CancelledError:
#         pass
#     print("🛑 수신/송출 태스크 종료")


# app = FastAPI(lifespan=lifespan)


# @app.websocket("/ws/annotated")
# async def ws_annotated(websocket: WebSocket):
#     await websocket.accept()
#     active_ws.add(websocket)
#     print(f"🧠 분석 WebSocket 연결됨 ({len(active_ws)}명)")
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     finally:
#         active_ws.discard(websocket)
#         print(f"🔴 분석 WebSocket 해제됨 ({len(active_ws)}명)")


# @app.websocket("/ws/pass_through")
# async def ws_pass_through(websocket: WebSocket):
#     await websocket.accept()
#     active_pass_ws.add(websocket)
#     print(f"🧪 pass_through WebSocket 연결됨 ({len(active_pass_ws)}명)")
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     finally:
#         active_pass_ws.discard(websocket)
#         print(f"🔴 pass_through WebSocket 해제됨 ({len(active_pass_ws)}명)")


# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="127.0.0.1", port=8010)
import sys
import os
import cv2
import asyncio
import time
import numpy as np
import websockets
import gc

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
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
frame_queue = asyncio.Queue(maxsize=1)
active_ws = set()
active_pass_ws = set()


# === WebSocket 프레임 수신 ===
async def receive_frames_from_ws():
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
                            while not frame_queue.empty():
                                try:
                                    frame_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    break
                            await frame_queue.put(frame)
                    await asyncio.sleep(0.001)
        except Exception as e:
            print(f"💥 WebSocket 연결 오류: {e}")
            await asyncio.sleep(1)


# === 프레임 처리 및 송출 ===
async def process_and_broadcast_frames():
    frame_counter = 0

    while True:
        buffer_annotated = None
        buffer_original = None
        data_annotated = None
        data_original = None

        try:
            frame = await frame_queue.get()
            while not frame_queue.empty():
                try:
                    frame = frame_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            annotated_frame = frame.copy()
            annotated_frame = draw_roi(annotated_frame)

            if state["mode"] == "idle":
                if detect_motion(annotated_frame):
                    cv2.putText(
                        annotated_frame,
                        "Motion On",
                        (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 255, 0),
                        2,
                    )
                    bbox = detect_objects(annotated_frame)
                    if bbox:
                        tracker = create_tracker()
                        if init_tracker(tracker, annotated_frame, bbox):
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
                        annotated_frame,
                        "Motion Off",
                        (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 0, 255),
                        2,
                    )

            elif state["mode"] == "tracking":
                tracker = state["tracker"]
                success, bbox = update_tracker(tracker, annotated_frame)
                if success:
                    state["bbox"] = bbox
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(
                        annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 2
                    )

                    if is_inside_roi(bbox) and not state["ocr_done"]:
                        state["roi_enter_time"] = state["roi_enter_time"] or time.time()
                        ocr_result = run_ocr_on_bbox(annotated_frame, bbox)
                        state["ocr_attempts"] += 1
                        if ocr_result:
                            state["ocr_result"] = ocr_result
                            state["ocr_done"] = True
                            print(f"✅ OCR 성공: {ocr_result}")
                        elif exceeded_ocr_retries():
                            print("❌ OCR 최대 시도 실패")
                            state["failure_message"] = "OCR 실패"
                            reset_system()
                    elif has_roi_timeout():
                        print("⌛ ROI 진입 실패")
                        state["failure_message"] = "ROI 진입 실패"
                        reset_system()
                else:
                    print("❌ 추적 실패")
                    state["failure_message"] = "추적 실패"
                    reset_system()

                if state["ocr_result"]:
                    cv2.putText(
                        annotated_frame,
                        f"OCR: {state['ocr_result']}",
                        (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 255, 0),
                        2,
                    )
                elif state["failure_message"]:
                    cv2.putText(
                        annotated_frame,
                        state["failure_message"],
                        (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 0, 255),
                        2,
                    )

            # 분석 프레임 인코딩 및 전송
            if active_ws:
                success, buffer_annotated = cv2.imencode(".jpg", annotated_frame)
                if success:
                    data_annotated = buffer_annotated.tobytes()
                else:
                    buffer_annotated = None

                if data_annotated:
                    for ws in list(active_ws):
                        try:
                            await ws.send_bytes(data_annotated)
                        except:
                            await ws.close()
                            active_ws.discard(ws)

            # 원본 프레임 인코딩 및 전송
            if active_pass_ws:
                success, buffer_original = cv2.imencode(".jpg", frame)
                if success:
                    data_original = buffer_original.tobytes()
                else:
                    buffer_original = None

                if data_original:
                    for ws in list(active_pass_ws):
                        try:
                            await ws.send_bytes(data_original)
                        except:
                            await ws.close()
                            active_pass_ws.discard(ws)

            # 메모리 정리
            frame_counter += 1
            if frame_counter % 100 == 0:
                del buffer_annotated, buffer_original
                del data_annotated, data_original
                del annotated_frame, frame
                gc.collect()

            await asyncio.sleep(0.03)

        except Exception as e:
            print(f"💥 프레임 처리 예외: {e}")
            await asyncio.sleep(0.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    t1 = asyncio.create_task(receive_frames_from_ws())
    t2 = asyncio.create_task(process_and_broadcast_frames())
    yield
    t1.cancel()
    t2.cancel()
    try:
        await t1
    except asyncio.CancelledError:
        pass
    try:
        await t2
    except asyncio.CancelledError:
        pass
    print("🛑 수신/송출 태스크 종료")


app = FastAPI(lifespan=lifespan)


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
    active_pass_ws.add(websocket)
    print(f"🧪 pass_through WebSocket 연결됨 ({len(active_pass_ws)}명)")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        active_pass_ws.discard(websocket)
        print(f"🔴 pass_through WebSocket 해제됨 ({len(active_pass_ws)}명)")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010)
