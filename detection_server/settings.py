import json
import os

# 공통 설정 파일 경로 (Dash가 저장한 config.json 위치)
CONFIG_PATH = os.path.join("shared", "config.json")

# 전역 설정값 저장소
settings = {}


def load_settings_once():
    global settings
    if settings:
        return settings  # 이미 로딩된 경우 그대로 사용

    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일이 존재하지 않습니다: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        settings = json.load(f)

    print(f"✅ 설정값 로드 완료: {settings}")
    return settings
