# 站点操作细节（ChatGPT / DeepSeek）

## 通用调用骨架（每个 computer_use_tool 调用）

```python
import seed_browser_use as bu
rec = {"id": "<tab-id>", "targetId": "<tab-id>", "url": "<站点url>"}
bu.switch_tab(rec)
bu.wait(2)
print(bu.page_info())   # 验证 url 正确再继续
snap = str(bu.snapshot())
# 提取输入框 ref → 动作 → 验证
```

## ChatGPT（https://chatgpt.com/）

- 输入框 ref：正则 `((?:d\d+):(?:e\d+)) textbox "与 ChatGPT 聊天"`（每次重新快照提取，scope 编号会变化）
- 提交：`bu.type(ref, text, submit=True)`；⚠️ 即使报 `ACTION FAILED ... did NOT land` 也不代表失败——ChatGPT 富文本编辑器读回校验会误报。用 `bu.get_page_text()` 检查任务文本是否进入对话，进入即成功，不要重发
- 等待生成：分段 `bu.wait(10~20)` + `bu.get_page_text()` 尾部检查；完成标志 = 出现完整 4 段输出且页面不再显示「正在思考」
- 思考中特征：页面文字含「正在思考」
- 会话 URL 形如 `https://chatgpt.com/c/<id>`，会话标题由页面自动生成

## DeepSeek（https://chat.deepseek.com/）

- 输入框 ref：正则 `((?:d\d+):(?:e\d+)) textarea "给 DeepSeek 发送消息"`
- 提交后同样用 `bu.get_page_text()` 验证（检查「辩论任务」等字样是否出现）
- 长回复提取：`bu.content_export(max_chars=12000)` 取 paragraphs——`get_page_text()` 的 DOM 顺序可能把历史消息排在回复之前，结构化提取更可靠
- 页面底部有「深度思考 / 智能搜索」按钮，保持默认不开启即可得到结构化辩论回复
- 会话 URL 形如 `https://chat.deepseek.com/a/chat/s/<id>`

## 标签 ID 获取

- `bu.list_tabs()` 可能只显示当前活动标签；要确认另一标签的 record，先 `bu.switch_tab(猜测record)` 或用 `bu.new_tab(url)` 新建（新建保留登录态），再 list 确认
- 标签关闭或浏览器重启后 record 失效，需重新获取

## 已知限制

- 只能操作内置浏览器（bu 挂载的会话），无法操作用户桌面上的独立浏览器窗口
- 每次 computer_use_tool 调用是独立进程，跨调用状态不持久——所有依赖先前状态的操作必须同调用内完成，或每调用开头重新 switch_tab + 验证
- 登录态由用户维护；如遇登录/验证码，调用 `interaction.request_action(type="browserControl")` 交还用户
