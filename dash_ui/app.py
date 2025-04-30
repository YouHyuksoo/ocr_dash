import dash
from dash import html, dcc, Input, Output, State
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
                                    ]
                                ),
                            ]
                        )
                    ],
                    width=3,
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
                                html.Img(
                                    id="live-feed",
                                    src="http://127.0.0.1:8010/annotated_feed",
                                    style={"width": "100%", "border": "1px solid #444"},
                                    alt="📷 영상 수신 실패 - 서버 확인 필요 http://127.0.0.1:8010/annotated_feed",
                                ),
                            ]
                        )
                    ],
                    width=6,
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
                            ]
                        )
                    ],
                    width=3,
                ),
            ]
        ),
        dcc.Interval(id="status-interval", interval=2000, n_intervals=0),
        dcc.Store(id="sidebar-toggle", data=True),
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


if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
