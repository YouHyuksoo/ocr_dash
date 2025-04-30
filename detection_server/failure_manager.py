import time
from state import state
from settings import load_settings_once

config = load_settings_once()

# 설정값
OCR_RETRY_LIMIT = config.get("ocr_retry_limit", 3)
ROI_ENTRY_TIMEOUT = config.get("roi_entry_timeout", 5.0)
DETECTION_GRACE_PERIOD = config.get("detection_grace_period", 2.0)


def has_roi_timeout():
    """
    ROI 진입까지 허용된 시간 초과 여부 확인
    :return: True / False
    """
    if state["roi_enter_time"] is None:
        return False

    elapsed = time.time() - state["roi_enter_time"]
    return elapsed > ROI_ENTRY_TIMEOUT


def has_tracking_timeout():
    """
    YOLO 감지 이후 객체 추적 중일 때 일정 시간 이상 경과하면 실패로 판단
    :return: True / False
    """
    if state["start_time"] is None:
        return False

    elapsed = time.time() - state["start_time"]
    return elapsed > DETECTION_GRACE_PERIOD


def exceeded_ocr_retries():
    """
    OCR 실패 재시도 횟수 초과 여부
    :return: True / False
    """
    return state["ocr_attempts"] >= OCR_RETRY_LIMIT


def reset_system():
    """
    시스템을 초기 상태로 리셋
    """
    print("🔄 시스템 상태 초기화 (감지 실패 또는 완료)")
    state.update(
        {
            "mode": "idle",
            "tracker": None,
            "bbox": None,
            "last_seen": None,
            "ocr_attempts": 0,
            "ocr_done": False,
            "start_time": None,
            "roi_enter_time": None,
            "ocr_result": None,
        }
    )
