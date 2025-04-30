import cv2


def create_tracker():
    """
    OpenCV Tracker 객체를 생성합니다. (CSRT 사용)

    :return: tracker 객체
    """
    return cv2.TrackerCSRT_create()


def init_tracker(tracker, frame, bbox):
    """
    Tracker를 초기화합니다.

    :param tracker: Tracker 객체
    :param frame: 현재 프레임
    :param bbox: (x, y, w, h) 형식의 초기 바운딩 박스
    :return: 초기화 성공 여부 (bool)
    """
    return tracker.init(frame, bbox)


def update_tracker(tracker, frame):
    """
    Tracker를 업데이트하여 새로운 바운딩 박스를 얻습니다.

    :param tracker: Tracker 객체
    :param frame: 현재 프레임
    :return: (업데이트 성공 여부, bbox)
    """
    return tracker.update(frame)
