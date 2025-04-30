import cv2

# 이전 프레임 저장용 (초기에는 None)
prev_frame = None


def detect_motion(frame, threshold=25, area_threshold=5000):
    """
    현재 프레임과 이전 프레임을 비교하여 움직임을 감지합니다.

    :param frame: 현재 프레임 (BGR 이미지)
    :param threshold: 픽셀 차이 임계값
    :param area_threshold: 움직임으로 판단할 최소 영역 크기
    :return: 움직임 감지 여부 (True/False)
    """
    global prev_frame

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    if prev_frame is None:
        prev_frame = gray
        return False

    diff = cv2.absdiff(prev_frame, gray)
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    motion_area = cv2.countNonZero(thresh)

    prev_frame = gray  # 이전 프레임 갱신

    return motion_area > area_threshold
