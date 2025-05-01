from ultralytics import YOLO
import cv2
import numpy as np
import os
from threading import Lock

# YOLO 모델 파일 경로 설정 (학습 완료된 best.pt 위치)
YOLO_MODEL_PATH = os.path.join("runs", "detect", "ocr_dash", "weights", "best.pt")


# 모델 로딩을 위한 싱글톤 클래스
class YOLOModelSingleton:
    _instance = None
    _lock = Lock()  # 멀티스레드 환경에서 안전하게 초기화하기 위한 락

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                print("🔄 YOLO 모델 로드 중...")
                cls._instance = super().__new__(cls)
                cls._instance.model = YOLO(YOLO_MODEL_PATH)
                print("✅ YOLO 모델 로드 완료")
        return cls._instance


# YOLO 모델 인스턴스 가져오기
def get_yolo_model():
    return YOLOModelSingleton().model


def detect_objects(frame, conf_thres=0.5):
    """
    YOLO 모델을 사용하여 객체를 감지하고 바운딩 박스를 반환합니다.

    :param frame: 입력 BGR 이미지 (numpy array)
    :param conf_thres: 신뢰도 임계값
    :return: 첫 번째 감지된 객체의 바운딩 박스 (x, y, w, h) 또는 None
    """
    model = get_yolo_model()  # 싱글톤 인스턴스에서 모델 가져오기
    print("✅ YOLO 모델 객체감지 시작 ")
    results = model.predict(source=frame, conf=conf_thres, verbose=False)

    detections = results[0].boxes.xyxy.cpu().numpy()  # (N, 4)
    scores = results[0].boxes.conf.cpu().numpy()
    print("✅ YOLO 모델 객체감지 진행함 ")
    if len(detections) == 0:
        return None

    # 신뢰도 높은 것부터 정렬
    idx = np.argmax(scores)
    x1, y1, x2, y2 = detections[idx]
    w = x2 - x1
    h = y2 - y1

    return (int(x1), int(y1), int(w), int(h))  # (x, y, w, h) 포맷
