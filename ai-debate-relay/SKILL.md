---
name: ai-debate-relay
description: 用浏览器自动化（computer_use_tool plane="bu" + seed_browser_use）在两个已登录的 AI 网页聊天（默认 ChatGPT + DeepSeek）之间执行多轮"互读-互批-修订"辩论接力，最终得到双方都满意的收敛答案。当用户要求"让两个AI互相辩论/互相批判/互相审阅"、"ChatGPT和DeepSeek打辩论/互相检查"、"双模型交叉验证公式推导、物理图像或结论"、"接力搬运两个AI的回答"等场景时使用。
---

# AI 辩论接力（双模型互批收敛）

## 概述

在两个已登录的 AI 网页聊天标签页之间接力搬运消息，执行「开局 → 互批 → 修订 → 表态」协议，直到双方连续【满意】或达到轮数上限，输出收敛答案。默认组合 ChatGPT + DeepSeek，可替换为任意两个已登录的聊天网页。运行通道：

```python
computer_use_tool(plane="bu", code="import seed_browser_use as bu ...")
```

## 前置检查（每个 computer_use_tool 调用开头都要做）

1. `bu.list_tabs()` 拿到两个标签的完整 record（含 id / targetId / url），确认 URL：ChatGPT=`https://chatgpt.com/`、DeepSeek=`https://chat.deepseek.com/`
2. `bu.switch_tab(record)` → `bu.wait(2)` → 用 `bu.page_info()` 验证当前 URL 符合预期，再做动作
3. 跨调用不持久：每次新调用都必须重新 switch_tab 并验证；中途不要调用 `bu.resync()`（会把挂载拽回前台标签，可能造成快照错乱）
4. 两个标签需已登录（登录态由用户保持；若遇 `blocked=auth`，用 `interaction.request_action` 交还用户登录）

## 辩论协议（开局时随任务一起发给第一位 AI）

任务模板、协议全文与话术见 `references/relay-templates.md`。核心约束：

- 每轮输出 4 段：① 对对方答案的批判（事实错误/逻辑漏洞/遗漏角度）② 坚持或让步的说明 ③ 修订后的完整答案 ④ 满意度表态：【满意】/【不满意】
- 规则：不做无意义让步；除非对方证据充分否则坚持观点；可引用权威依据
- 轮数上限默认 3 轮；双方连续【满意】即终止

## 接力流程

- R0 开局：向 AI-A 发送「任务 + 协议 + 请给出初始答案」
- R1 读 A 完整回复 → 转给 AI-B：「对手的初始回答 + 请按协议批判并给出修订版」
- R2 读 B 完整回复 → 转给 AI-A：「对手的批判 + 请逐条回应并重写答案」
- R3 读 A 完整回复 → 转给 AI-B：「对手的回应 + 请给出最终回应与最终修订版」（收尾轮）

每轮要点：

1. 读完回复后提取完整文本（`bu.get_page_text()`；DOM 顺序错乱时用 `bu.content_export()`）
2. 转达消息必须包含对方回复的完整实质内容（立场、各条批判/反驳、对比表、排序），不能只转结论
3. 终止判断：读回的表态连续为【满意】或达到轮数上限，即停止
4. 交付：向用户输出各轮交锋要点 + 最终收敛答案 + 分歧遗留点（如有）

## 站点操作要点（详细见 references/site-specs.md）

- ChatGPT：输入框 ref 用正则 `((?:d\d+):(?:e\d+)) textbox "与 ChatGPT 聊天"` 匹配；富文本编辑器下 `bu.type` 可能报 ⚠️ ACTION FAILED——以 `bu.get_page_text()` 确认文本进入对话为准，不要因报错重发（会重复）
- DeepSeek：输入框 ref 用正则 `((?:d\d+):(?:e\d+)) textarea "给 DeepSeek 发送消息"` 匹配
- 等待生成：禁止 `bu.js` 长轮询（会超时卡死调用）；用分段 `bu.wait(6~20)` + `bu.get_page_text()` 看尾部是否出现完整 4 段输出
- 长回复提取：优先 `bu.content_export(max_chars=12000)` 的 paragraphs

## 常见坑

| 症状 | 对策 |
|---|---|
| switch_tab 后快照是旧标签 | 每调用开头重切 + 验证 page_info URL |
| type 报 ACTION FAILED | 用 get_page_text 验证；已进对话则视为成功 |
| 等生成卡死/超时 | 分段 wait + 短查尾部，禁长轮询 |
| get_page_text 顺序乱 | 用 content_export 提取 |
| 长消息 typing 慢/中断 | 保持单条消息发送，等待后验证 |

## 结果交付要求

- 用表格/可视化呈现「初始立场 → 交锋点 → 收敛结论」（可结合 doubao-visualization）
- 注明：双方引用的外部依据（如 WHO、文献）未经独立核验，重要决策前需人工确认
