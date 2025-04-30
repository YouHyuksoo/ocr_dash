import cv2

# 영상 수신 설정
VIDEO_URL = "http://127.0.0.1:8000/video_feed"

def test_video_stream():
    print("📷 테스트: 영상 수신 시작")
    test_cap = cv2.VideoCapture(VIDEO_URL)

    if not test_cap.isOpened():
        print("❌ 영상 스트림을 열 수 없습니다. URL을 확인하세요.")
        return

    print("✅ 영상 스트림 연결 성공")
    while True:
        ret, frame = test_cap.read()
        if not ret:
            print("⚠️ 프레임을 읽을 수 없습니다. 재시도 중...")
            break

        cv2.imshow("Test Video Feed", frame)

        # 'q' 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    test_cap.release()
    cv2.destroyAllWindows()
    print("📷 테스트: 영상 수신 종료")

if __name__ == "__main__":
    test_video_stream()