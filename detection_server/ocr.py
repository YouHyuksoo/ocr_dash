import easyocr
import re
import cv2

# EasyOCR Reader 초기화 (한 번만)
reader = easyocr.Reader(["en"], gpu=False)  # GPU 사용 시 gpu=True


def extract_numbers_from_text(text):
    """
    문자열에서 3~4자리 숫자만 추출
    :param text: OCR로 읽은 전체 문자열
    :return: 숫자 문자열 또는 None
    """
    matches = re.findall(r"\b\d{3,4}\b", text)
    return matches[0] if matches else None


def run_ocr_on_bbox(frame, bbox):
    """
    객체 바운딩 박스 내부에서 OCR 수행
    :param frame: 전체 BGR 이미지
    :param bbox: (x, y, w, h) 바운딩 박스
    :return: 숫자 결과 문자열 또는 None
    """
    x, y, w, h = bbox
    roi = frame[y : y + h, x : x + w]  # 객체 박스 부분만 잘라냄

    # OCR 실행
    result = reader.readtext(roi)

    if not result:
        return None

    for _, text, _ in result:
        cleaned = extract_numbers_from_text(text)
        if cleaned:
            return cleaned

    return None
