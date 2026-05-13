# EchoMem UI (Streamlit Skeleton)

最小可运行的可视化骨架，包含 4 个区域：

- Chat
- Profile
- Memory Timeline
- Retrieval Dashboard

默认尝试读取：

- `profile/profile.db`
- `memory.db`

如果数据库或表读取失败，页面会优雅降级为提示信息和示例数据，不会崩溃。

用户选择行为：

- 侧边栏提供显式 `User ID` 选择器，写入 `st.session_state.selected_user_id`。
- Chat 与 Dashboard 共用同一个 `selected_user_id`，会话请求始终使用该值。
- 仅当 `profile/profile.db` 读取失败时，才降级到 `demo_user` 并显示提示。

## Run

在仓库根目录执行：

```bash
streamlit run ui/app.py
```
