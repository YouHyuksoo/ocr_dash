import gc  # [🔧 추가]
import time
from state import state
from settings import load_settings_once

config = load_settings_once()

# 설정값
OCR_RETRY_LIMIT = config.get("ocr_retry_limit", 3)
ROI_ENTRY_TIMEOUT = config.get("roi_entry_timeout", 5.0)
DETECTION_GRACE_PERIOD = config.get("detection_grace_period", 2.0)


def has_roi_timeout():
    if state["roi_enter_time"] is None:
        return False
    elapsed = time.time() - state["roi_enter_time"]
    return elapsed > ROI_ENTRY_TIMEOUT


def has_tracking_timeout():
    if state["start_time"] is None:
        return False
    elapsed = time.time() - state["start_time"]
    return elapsed > DETECTION_GRACE_PERIOD


def exceeded_ocr_retries():
    return state["ocr_attempts"] >= OCR_RETRY_LIMIT


def reset_system():
    """
    시스템을 초기 상태로 리셋하고 메모리 수거까지 수행
    """
    print("🔄 시스템 상태 초기화 (감지 실패 또는 완료)", flush=True)

    # [🔧 명시적 참조 해제]
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

    # [🔧 명시적 메모리 수거]
    gc.collect()
