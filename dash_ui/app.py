import dash
from dash import html, dcc, Input, Output, State, ClientsideFunction
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MORPH])

app.layout = dbc.Container(
    [
        # 상태 저장
        dbc.Row(
            [
                # 좌측 슬라이드 패널
                dbc.Col(
                    id="sidebar-col",
                    children=[
                        dbc.Card(
                            [
                                dbc.CardHeader("제어 패널"),
                                dbc.CardBody(
                                    [
                                        dbc.Button(
                                            "▶ 감지 시작",
                                            id="btn-start",
                                            color="success",
                                            outline=True,
                                            className="mb-3 d-block w-100",
                                        ),
                                        dbc.Button(
                                            "⏹ 감지 중지",
                                            id="btn-stop",
                                            color="danger",
                                            outline=True,
                                            className="mb-3 d-block w-100",
                                        ),
                                        dbc.Checklist(
                                            options=[{"label": "OCR 사용", "value": 1}],
                                            value=[],
                                            id="toggle-ocr",
                                            switch=True,
                                            className="mb-3",
                                        ),
                                        dbc.Input(
                                            id="roi-input",
                                            placeholder="ROI 입력 (x,y,w,h)",
                                            type="text",
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "🖍 ROI 설정",
                                            id="btn-roi",
                                            color="primary",
                                            outline=True,
                                            className="d-block w-100",
                                        ),
                                        html.Hr(className="my-3"),  # 구분선 추가
                                        html.H6(
                                            "모델 테스트", className="mb-2"
                                        ),  # 섹션 제목
                                        dbc.Select(
                                            id="model-select",
                                            options=[
                                                {
                                                    "label": "YOLOv8n",
                                                    "value": "yolov8n",
                                                },
                                                {
                                                    "label": "YOLOv8s",
                                                    "value": "yolov8s",
                                                },
                                                {
                                                    "label": "YOLOv8m",
                                                    "value": "yolov8m",
                                                },
                                            ],
                                            value="yolov8n",
                                            className="mb-2",
                                        ),
                                        dbc.Button(
                                            "🧪 모델 테스트 실행",
                                            id="btn-test-model",
                                            color="info",
                                            outline=True,
                                            className="d-block w-100 mb-2",
                                        ),
                                        dbc.Button(
                                            "📊 결과 비교",
                                            id="btn-compare-results",
                                            color="secondary",
                                            outline=True,
                                            className="d-block w-100",
                                        ),
                                    ],
                                    className="p-2",  # 내부 패딩 축소
                                ),
                            ],
                            className="border-0",
                        )
                    ],
                    width=2,  # 3에서 2로 변경 (25% -> 약 16.7%)
                    style={
                        "transition": "all 0.5s ease",
                        "transform": "translateX(0%)",
                        "position": "relative",
                        "zIndex": "1000",
                    },
                ),
                # 중앙 영상
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        dbc.Button(
                                            DashIconify(icon="mdi:menu", width=24),
                                            id="btn-toggle-sidebar",
                                            color="secondary",
                                            outline=True,
                                            className="mb-3",
                                        )
                                    ]
                                ),
                                html.H5(
                                    "실시간 감지 영상", className="text-center mb-3"
                                ),
                                # html.Img를 html.Canvas로 변경
                                html.Div(
                                    [
                                        html.Canvas(
                                            id="live-feed-canvas",
                                            width=640,
                                            height=480,
                                            style={
                                                "width": "100%",
                                                "border": "1px solid #444",
                                                "background": "#000",
                                            },
                                        ),
                                        html.Div(
                                            [
                                                html.Span(
                                                    id="feed-status",
                                                    className="status",
                                                    style={
                                                        "display": "inline-block",
                                                        "width": "10px",
                                                        "height": "10px",
                                                        "borderRadius": "50%",
                                                        "background": "#666",
                                                        "marginRight": "5px",
                                                    },
                                                ),
                                                html.Span(
                                                    "연결 대기 중...",
                                                    id="feed-status-text",
                                                ),
                                                html.Button(
                                                    "연결",
                                                    id="btn-connect-feed",
                                                    className="ms-2",
                                                ),
                                                html.Button(
                                                    "연결 해제",
                                                    id="btn-disconnect-feed",
                                                    className="ms-2",
                                                    disabled=True,
                                                ),
                                            ],
                                            className="d-flex align-items-center justify-content-center mt-2",
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                    width=8,  # 7에서 8로 변경하여 중앙 영역 확대
                ),
                # 우측 상태 정보
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("상태 정보"),
                                dbc.CardBody(
                                    [
                                        html.Span(
                                            "🟢 시스템 정상 작동 중", id="status-msg"
                                        ),
                                        html.Hr(),
                                        html.P("객체 수:", className="mb-1"),
                                        html.Div(
                                            id="object-count",
                                            className="h3 text-info mb-3",
                                        ),
                                        html.P("OCR 결과:", className="mb-1"),
                                        html.Pre(
                                            id="ocr-output",
                                            className="bg-dark text-success p-2",
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-3",
                        ),
                        # 환경설정 카드 추가
                        dbc.Card(
                            [
                                dbc.CardHeader("환경설정"),
                                dbc.CardBody(
                                    [
                                        html.P("로그 레벨:", className="mb-1"),
                                        dbc.Select(
                                            id="log-level",
                                            options=[
                                                {"label": "DEBUG", "value": "debug"},
                                                {"label": "INFO", "value": "info"},
                                                {
                                                    "label": "WARNING",
                                                    "value": "warning",
                                                },
                                                {"label": "ERROR", "value": "error"},
                                            ],
                                            value="info",
                                            className="mb-3",
                                        ),
                                        html.P("알림 설정:", className="mb-1"),
                                        dbc.Checklist(
                                            options=[
                                                {
                                                    "label": "오류 알림",
                                                    "value": "error_alert",
                                                },
                                                {
                                                    "label": "OCR 완료 알림",
                                                    "value": "ocr_alert",
                                                },
                                            ],
                                            value=["error_alert"],
                                            id="notification-settings",
                                            switch=True,
                                            className="mb-3",
                                        ),
                                        html.P("모니터링 간격:", className="mb-1"),
                                        dbc.Input(
                                            id="monitoring-interval",
                                            type="number",
                                            min=500,
                                            max=10000,
                                            step=500,
                                            value=2000,
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "💾 설정 저장",
                                            id="btn-save-settings",
                                            color="primary",
                                            className="mt-2 w-100",
                                        ),
                                    ]
                                ),
                            ]
                        ),
                    ],
                    width=2,  # 3에서 2로 변경하여 폭 축소
                ),
            ]
        ),
        dcc.Interval(id="status-interval", interval=2000, n_intervals=0),
        dcc.Store(id="sidebar-toggle", data=True),
        dcc.Store(id="feed-connection-status", data=False),
    ],
    fluid=True,
    className="py-4",
)


# 슬라이드 토글 콜백 (transform 방식)
@app.callback(
    Output("sidebar-col", "style"),
    Output("sidebar-toggle", "data"),
    Input("btn-toggle-sidebar", "n_clicks"),
    State("sidebar-toggle", "data"),
    prevent_initial_call=True,
)
def toggle_sidebar(n, is_open):
    new_open = not is_open
    style = {
        "transition": "all 0.5s ease",
        "position": "relative",
        "zIndex": "1000",
        "transform": "translateX(0%)" if new_open else "translateX(-120%)",
    }
    return style, new_open


# 상태 업데이트 콜백
@app.callback(
    Output("object-count", "children"),
    Output("ocr-output", "children"),
    Input("status-interval", "n_intervals"),
)
def update_status(n):
    return "3", "ABC-1234"


# 간소화된 WebSocket 연결 상태 관리를 위한 콜백
app.clientside_callback(
    """
    function(n_connect, n_disconnect, current_status) {
        // 초기 로드 시에는 아무 것도 하지 않음
        if (!n_connect && !n_disconnect) {
            console.log("초기 로드 - 상태 유지:", current_status);
            return [current_status, current_status, !current_status];
        }
        
        // 어떤 버튼이 눌렸는지 확인 (가장 최근에 변경된 prop_id)
        var ctx = window.dash_clientside.callback_context;
        if (!ctx || !ctx.triggered) {
            console.log("콜백 컨텍스트 없음 - 상태 유지:", current_status);
            return [current_status, current_status, !current_status];
        }
        
        var triggered_id = ctx.triggered[0].prop_id.split('.')[0];
        console.log("트리거된 ID:", triggered_id);
        
        if (triggered_id === 'btn-connect-feed') {
            console.log("연결 버튼 클릭됨");
            if (typeof window.connectFeed === 'function') {
                window.connectFeed();
                return [true, true, false];
            } else {
                console.error("connectFeed 함수를 찾을 수 없습니다!");
                return [current_status, current_status, !current_status];
            }
        } else if (triggered_id === 'btn-disconnect-feed') {
            console.log("연결 해제 버튼 클릭됨");
            if (typeof window.disconnectFeed === 'function') {
                window.disconnectFeed();
                return [false, false, true];
            } else {
                console.error("disconnectFeed 함수를 찾을 수 없습니다!");
                return [current_status, current_status, !current_status];
            }
        }
        
        return [current_status, current_status, !current_status];
    }
    """,
    Output("feed-connection-status", "data"),
    Output("btn-disconnect-feed", "disabled"),
    Output("btn-connect-feed", "disabled"),
    Input("btn-connect-feed", "n_clicks"),
    Input("btn-disconnect-feed", "n_clicks"),
    State("feed-connection-status", "data"),
)


if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
