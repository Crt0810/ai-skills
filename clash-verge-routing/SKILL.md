---
name: clash-verge-routing
description: "配置 Clash Verge / Clash Verge Rev 的按域名分流规则：让指定网站直连(DIRECT)、走代理(PROXY)或自定义策略。当用户要求「某某网站直连/不走代理」「给这些网站配置代理」「某些网站走代理某些直连」「Clash 分流规则」时使用。自动定位订阅的 rules 扩展文件、幂等添加规则、自动备份，并指导重新加载与验证。"
---

# Clash Verge Routing

## Overview

为 Clash Verge / Clash Verge Rev（mihomo 内核，Windows）添加"域名 → 直连/代理"分流规则。分流按连接自动判断，多个网页同时打开时直连与代理互不干扰。核心做法是修改**订阅绑定的 rules 扩展文件**的 `prepend` 列表（优先级最高），而不是改订阅快照。

## 工作流

1. **明确需求**：用户给出的网站/域名清单 + 每类策略（直连 DIRECT / 走代理 PROXY / 自定义组名）。域名可从 `references/domain-groups.md` 的常用分组挑选。
2. **运行脚本添加规则**：

```bash
python <skill>/scripts/add_rules.py --direct aps.org nature.com --proxy youtube.com
```

   - 脚本自动定位 Clash Verge 配置目录与当前订阅的 rules 扩展文件；
   - 幂等去重、自动备份（`.bak-时间戳`）；
   - 先 `--dry-run` 预览，确认无误再去掉该参数执行；
   - `--list` 可查看当前规则；`--proxy-policy <组名>` 可指定非默认策略。
   - 脚本依赖 PyYAML：`python -m pip install pyyaml`。
3. **触发重新加载（必做，否则不生效）**：Verge 不会自动合并外部修改。让用户在界面操作，或代为重启：
   - 订阅页 → 当前订阅 → **重新激活**；或主界面 → **重启内核**。
   - 若代重启：停掉 `clash-verge.exe` 与 `verge-mihomo.exe` 进程后重新启动 `clash-verge.exe`（勿停 `clash-verge-service` 服务）；提前告知用户会闪断几秒并征得同意。
4. **验证生效**：从最终配置 `config.yaml` 读取 `external-controller` 与 `secret`，调用 `GET /rules` 检查目标域名的 `proxy` 字段是否为 DIRECT/PROXY：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:9097/rules" -Headers @{Authorization="Bearer <secret>"}
```

   - 也可让用户实测：访问目标站点 + 一个代理站点，观察 Clash 连接列表分别走直连/节点。
5. **交付说明**：告知用户改动了哪个文件、备份位置、如何撤销（恢复备份或删行后重新激活）。

## 规则语法速查

- `DOMAIN-SUFFIX,aps.org,DIRECT` —— 域名及所有子域，最常用
- `DOMAIN,example.com,DIRECT` —— 精确域名
- 策略字段：`DIRECT` / `PROXY` / `REJECT` / 具体策略组名（中文组名需与订阅实际一致）
- 规则自上而下匹配，直连规则须置于 MATCH 之前（prepend 自动满足）

## 参考文件

- `references/clash-verge-rev.md` —— 配置目录结构、扩展文件机制、API 验证、常见故障（规则不生效时先读）
- `references/domain-groups.md` —— 学术文献/AI/社交/工具等常用域名分组清单
- `scripts/add_rules.py` —— 幂等添加规则脚本（参数：`--direct/--proxy/--proxy-policy/--rules-file/--dry-run/--list`）

## 安全与纪律

- 修改前必须备份（脚本已自动备份）；不直接改订阅快照文件。
- 用户明确拒绝的操作不得换法重试；删除/覆盖类操作按确认模式处理。
- 直连不可用属正常情况：删除该条规则或改走代理，不强行"修复"。
- 涉及重启用户代理进程时先说明影响（短暂断网）并征得同意。
