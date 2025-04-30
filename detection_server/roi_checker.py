import cv2
from settings import load_settings_once

def load_roi_settings():
    """
    ROI 설정값을 로드합니다.

    :return: ROI_BOX 값
    """
    config = load_settings_once()
    return config.get("roi", [100, 100, 200, 200])  # 기본값


# ROI 사각형 좌표 읽어오기
ROI_BOX = load_roi_settings()


def is_inside_roi(bbox):
    """
    객체의 중심점이 ROI 안에 들어있는지 판단합니다.

    :param bbox: (x, y, w, h) 포맷의 바운딩 박스
    :return: True(안에 있음) / False(밖에 있음)
    """
    x, y, w, h = bbox
    obj_center_x = x + w // 2
    obj_center_y = y + h // 2

    roi_x, roi_y, roi_w, roi_h = ROI_BOX

    if (roi_x <= obj_center_x <= roi_x + roi_w) and (
        roi_y <= obj_center_y <= roi_y + roi_h
    ):
        return True
    return False


def draw_roi(frame):
    """
    프레임에 ROI 사각형을 항상 그립니다.

    :param frame: BGR 이미지
    :return: 그려진 프레임
    """
    roi_x, roi_y, roi_w, roi_h = ROI_BOX
    cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 255, 0), 2)
    return frame
