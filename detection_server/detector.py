from ultralytics import YOLO
import cv2
import numpy as np
import os

# YOLO 모델 파일 경로 설정 (학습 완료된 best.pt 위치)
YOLO_MODEL_PATH = os.path.join("runs", "detect", "ocr_dash", "weights", "best.pt")

# YOLO 모델 로드 (최초 1회)
model = YOLO(YOLO_MODEL_PATH)


def detect_objects(frame, conf_thres=0.5):
    """
    YOLO 모델을 사용하여 객체를 감지하고 바운딩 박스를 반환합니다.

    :param frame: 입력 BGR 이미지 (numpy array)
    :param conf_thres: 신뢰도 임계값
    :return: 첫 번째 감지된 객체의 바운딩 박스 (x, y, w, h) 또는 None
    """
    results = model.predict(source=frame, conf=conf_thres, verbose=False)
    detections = results[0].boxes.xyxy.cpu().numpy()  # (N, 4)
    scores = results[0].boxes.conf.cpu().numpy()

    if len(detections) == 0:
        return None

    # 신뢰도 높은 것부터 정렬
    idx = np.argmax(scores)
    x1, y1, x2, y2 = detections[idx]
    w = x2 - x1
    h = y2 - y1

    return (int(x1), int(y1), int(w), int(h))  # (x, y, w, h) 포맷
