// WebSocket 관련 변수
let feedWs = null;
let feedPingInterval = null;
let canvasInterval = null;

// DOM 요소 참조
let canvas = null;
let ctx = null;
let img = new Image();
let statusIndicator = null;
let statusText = null;

// 주기적으로 DOM 요소 검색 시도
function initializeElements() {
  canvas = document.getElementById("live-feed-canvas");

  if (canvas) {
    console.log("Canvas 요소를 찾았습니다!");
    clearInterval(canvasInterval);

    // 캔버스 컨텍스트 초기화
    ctx = canvas.getContext("2d");

    // 이미지 로드 이벤트
    img.onload = function () {
      console.log("이미지 로드됨");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };

    // 상태 표시 요소
    statusIndicator = document.getElementById("feed-status");
    statusText = document.getElementById("feed-status-text");

    if (!statusIndicator || !statusText) {
      console.warn("상태 표시 요소를 찾을 수 없습니다!");
    }
  } else {
    console.log("Canvas 요소를 아직 찾지 못했습니다. 다시 시도합니다...");
  }
}

// 페이지 로드 시 실행 - 자동 연결 로직 추가
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM 로드 완료, 웹소켓 초기화 준비");

  // 100ms마다 DOM 요소 검색 시도 (Dash가 컴포넌트를 렌더링할 때까지)
  canvasInterval = setInterval(function () {
    initializeElements();

    // Canvas 요소를 찾았으면 연결 시도
    if (canvas) {
      // 요소를 찾았고 아직 연결되지 않았으면 연결 시도
      if (!feedWs) {
        console.log("Canvas 요소 감지됨 - 자동 연결 시도...");
        // 약간의 지연을 두어 다른 초기화가 완료되도록 함
        setTimeout(function () {
          window.connectFeed();
        }, 500);
      }
    }
  }, 100);
});

// WebSocket 연결 함수
window.connectFeed = function () {
  console.log("WebSocket 연결 시도 중...");

  // 캔버스 요소가 없으면 연결하지 않음
  if (!canvas) {
    console.error("Canvas 요소가 없어 WebSocket 연결을 시도할 수 없습니다!");
    return;
  }

  try {
    // 이미 연결되어 있는 경우 연결 해제
    if (feedWs) {
      console.log("이미 연결된 WebSocket이 있습니다. 연결을 해제합니다.");
      feedWs.close();
    }

    // WebSocket 서버 URL
    const wsUrl = "ws://127.0.0.1:8010/ws/annotated";
    console.log("연결 시도 URL:", wsUrl);

    feedWs = new WebSocket(wsUrl);
    feedWs.binaryType = "arraybuffer";

    // 연결 성공 시 버튼 상태 설정
    feedWs.onopen = function () {
      console.log("WebSocket 연결 성공!");
      if (statusIndicator) statusIndicator.style.background = "#4caf50";
      if (statusText) statusText.textContent = "연결됨";

      // 버튼 상태 명시적 설정
      const connectBtn = document.getElementById("btn-connect-feed");
      const disconnectBtn = document.getElementById("btn-disconnect-feed");

      if (connectBtn) connectBtn.disabled = true;
      if (disconnectBtn) disconnectBtn.disabled = false;

      // 핑 메시지 전송 (연결 유지)
      feedPingInterval = setInterval(function () {
        if (feedWs && feedWs.readyState === WebSocket.OPEN) {
          feedWs.send("ping");
        }
      }, 5000);
    };

    // 연결 종료 시
    feedWs.onclose = function () {
      console.log("WebSocket 연결 종료됨");
      if (statusIndicator) statusIndicator.style.background = "#f44336";
      if (statusText) statusText.textContent = "연결 끊김";
      clearInterval(feedPingInterval);
      feedWs = null;

      // 버튼 상태 업데이트
      const connectBtn = document.getElementById("btn-connect-feed");
      const disconnectBtn = document.getElementById("btn-disconnect-feed");

      if (connectBtn) connectBtn.disabled = false;
      if (disconnectBtn) disconnectBtn.disabled = true;
    };

    // 에러 발생 시
    feedWs.onerror = function (error) {
      console.error("WebSocket 오류:", error);
      if (statusIndicator) statusIndicator.style.background = "#ff9800";
      if (statusText) statusText.textContent = "연결 오류";
    };

    // 메시지 수신 시
    feedWs.onmessage = function (event) {
      console.log("WebSocket 메시지 수신됨");
      const blob = new Blob([event.data], { type: "image/jpeg" });
      img.src = URL.createObjectURL(blob);
    };
  } catch (e) {
    console.error("WebSocket 연결 오류:", e);
    if (statusIndicator) statusIndicator.style.background = "#f44336";
    if (statusText) statusText.textContent = "연결 실패";
  }
};

// WebSocket 연결 해제 함수 - 버튼 상태 관리 추가
window.disconnectFeed = function () {
  if (feedWs) {
    console.log("연결 해제 요청됨");
    feedWs.close();

    // 연결 버튼과 연결 해제 버튼 상태 직접 업데이트
    const connectBtn = document.getElementById("btn-connect-feed");
    const disconnectBtn = document.getElementById("btn-disconnect-feed");

    if (connectBtn) {
      console.log("연결 버튼 활성화");
      connectBtn.disabled = false;
    }

    if (disconnectBtn) {
      console.log("연결 해제 버튼 비활성화");
      disconnectBtn.disabled = true;
    }
  }
};
