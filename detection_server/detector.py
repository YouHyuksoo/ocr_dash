from ultralytics import YOLO
import cv2
import numpy as np
import os

# 전역 모델 변수
yolo_model = None


def set_model(model):
    """외부에서 모델을 주입할 수 있는 함수"""
    global yolo_model
    yolo_model = model
    print("✅ YOLO 모델 설정 완료", flush=True)


def detect_objects(frame, conf_thres=0.5):
    """
    YOLO 모델을 사용하여 객체를 감지하고 바운딩 박스를 반환합니다.

    :param frame: 입력 BGR 이미지 (numpy array)
    :param conf_thres: 신뢰도 임계값
    :return: 첫 번째 감지된 객체의 바운딩 박스 (x, y, w, h) 또는 None
    """
    if yolo_model is None:
        print("⚠️ YOLO 모델이 초기화되지 않았습니다", flush=True)
        return None

    results = yolo_model.predict(source=frame, conf=conf_thres, verbose=False)

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
