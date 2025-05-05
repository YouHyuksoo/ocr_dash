import json
import os

# 공통 설정 파일 경로
CONFIG_PATH = os.path.join("shared", "config.json")

# 전역 설정값 저장소
_settings = {}


def load_settings_once():
    """설정 파일을 한 번만 로드하는 함수"""
    global _settings
    if _settings:
        return _settings  # 이미 로딩된 경우 그대로 사용

    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일이 존재하지 않습니다: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _settings = json.load(f)

    print(f"✅ 설정값 로드 완료: {_settings}")
    return _settings


def get_setting(key, default=None):
    """특정 설정값을 가져오는 함수"""
    if not _settings:
        load_settings_once()
    return _settings.get(key, default)


# 모델 경로를 가져오는 함수
def get_model_path():
    """YOLO 모델 경로를 설정 또는 기본값에서 가져옴"""
    default_path = os.path.join("runs", "detect", "ocr_dash", "weights", "best.pt")
    return get_setting("yolo_model_path", default_path)
