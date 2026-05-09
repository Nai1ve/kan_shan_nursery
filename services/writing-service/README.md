# writing-service

写作苗圃服务。

职责：

- 8 步写作流程。
- 根据种子方向注入兴趣分类 Memory。
- 核心观点确认。
- 论证蓝图。
- 初稿生成。
- 圆桌审稿。
- 定稿草案。

P0 接口：

- `GET /health`
- `POST /writing/sessions`
- `GET /writing/sessions/{session_id}`
- `POST /writing/sessions/{session_id}/confirm-claim`
- `POST /writing/sessions/{session_id}/blueprint`
- `POST /writing/sessions/{session_id}/draft`
- `POST /writing/sessions/{session_id}/roundtable`
- `POST /writing/sessions/{session_id}/finalize`
