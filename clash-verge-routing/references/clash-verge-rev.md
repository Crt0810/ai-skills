# Clash Verge Rev 分流配置机制参考

面向 Windows 本地环境的 Clash Verge / Clash Verge Rev。用于执行"按域名直连/走代理"分流任务时查阅。

## 1. 核心概念

- **分流是每连接级的**：Clash 按"规则(rules)"从上到下匹配每个网络连接的目标域名/IP，命中即采用该规则指定的策略（直连 DIRECT / 走代理 / 拒绝）。所以同时开两个网页，一个直连一个走代理，天然互不干扰，无需浏览器级开关。
- **模式**：`mode: rule`（规则模式）才做分流；`global` 全走代理；`direct` 全直连。分流任务要求 rule 模式。
- **规则优先级**：自上而下，先命中先生效。因此"直连某域名"的规则必须放在代理规则（尤其 MATCH 兜底）之前。

## 2. 配置目录与文件

配置根目录（Windows）：

```
%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\
├── profiles\                # 订阅与扩展配置文件
│   ├── <uid>.yaml           # 远程订阅快照(更新时被覆盖, 不要直接改)
│   ├── <uid>.yaml           # 扩展文件: rules / merge / proxies / groups 类型
│   └── Merge.yaml / Script.js
├── profiles.yaml            # 订阅管理: current + items(uid/type/option)
├── config.yaml              # Verge 生成的最终生效配置(含合并后的 rules)
└── verge.yaml               # Verge 界面设置(系统代理开关/TUN等)
```

旧版 Clash Verge 的目录为 `%APPDATA%\clash-verge\`，机制相同。

## 3. 扩展文件机制（给订阅加规则的正道）

- **不要直接改订阅快照**（更新订阅会被覆盖）。正确做法是给订阅挂**扩展文件**，订阅更新后扩展规则仍在。
- Clash Verge Rev 支持四种扩展类型：**rules / merge / proxies / groups**，另有 script。
- **rules 扩展文件**语法（推荐用于分流规则）：

```yaml
prepend:
  - 'DOMAIN-SUFFIX,aps.org,DIRECT'
append: []
delete: []
```

`prepend` 插入到订阅规则**最前面**（最高优先）；`append` 插到末尾（MATCH 之后，意义有限）；`delete` 删除订阅中的规则。
- 在界面中给订阅挂扩展：订阅页 → 当前订阅 → 编辑 → 添加"规则扩展"；或在订阅的"扩展配置"里选择。也可以直接写 `profiles.yaml` 中该订阅 item 的 `option.rules: <uid>` 指向一个 type=rules 的扩展。
- merge 扩展同样可加规则，用 `prepend-rules:` / `append-rules:` 键（旧版写法），作用域可设为全局（Merge.yaml）或订阅专属。

## 4. 关键坑：修改后必须"重新激活/重启内核"

外部直接编辑 profiles 下的扩展文件后，**Verge 不会自动重新生成配置**。必须：

- 订阅页 → 当前订阅 → **重新激活**（最可靠，会重新生成最终配置并合并扩展）；或
- 主界面右下角 → **重启内核**。

重启内核的替代：停掉 `clash-verge.exe` 与 `verge-mihomo.exe` 后重新启动 `clash-verge.exe`。注意 `clash-verge-service`（Windows 服务）不要停。

## 5. 本地 API 验证（mihomo 内核）

- 端点与密钥在最终配置 `config.yaml` 中：`external-controller: 127.0.0.1:9097`、`secret: <密钥>`。
- 常用请求（PowerShell）：

```powershell
# 版本
Invoke-RestMethod -Uri "http://127.0.0.1:9097/version" -Headers @{Authorization="Bearer <密钥>"}
# 全部生效规则
Invoke-RestMethod -Uri "http://127.0.0.1:9097/rules" -Headers @{Authorization="Bearer <密钥>"}
```

- `/rules` 返回数组，每项含 `type / payload / proxy`；检查目标域名规则的 `proxy` 是否为 DIRECT。
- 注意：API 的 `PUT /configs?force=true` 只重载已生成的 config.yaml，**不会**重新合并扩展文件；验证前必须先重新激活/重启内核。

## 6. 规则语法速查

| 规则类型 | 示例 | 说明 |
|---|---|---|
| DOMAIN | `DOMAIN,example.com,DIRECT` | 精确域名（含子域） |
| DOMAIN-SUFFIX | `DOMAIN-SUFFIX,aps.org,DIRECT` | 域名及所有子域（最常用） |
| DOMAIN-KEYWORD | `DOMAIN-KEYWORD,mojie,DIRECT` | 域名含关键词 |
| GEOIP | `GEOIP,CN,DIRECT` | 按 IP 归属（国内直连常见） |
| MATCH | `MATCH,节点选择` | 兜底，放最后 |
| PROCESS-NAME | `PROCESS-NAME,chrome.exe,DIRECT` | 按进程（可选） |

策略字段：`DIRECT`（直连）、`REJECT`（拒绝）、`PROXY`（默认代理）、或具体策略组名（如"节点选择"/"自动选择"，名称为中文时按订阅实际组名）。

## 7. 常见故障排查

| 现象 | 原因/处理 |
|---|---|
| 加了规则不生效 | 未重新激活/重启内核；旧内核进程占端口 → 重新激活即可 |
| 订阅更新后规则丢失 | 改的是订阅快照而非扩展文件；应走 rules 扩展 |
| 重启内核后配置回到旧状态 | 确认扩展文件确实被当前订阅 option 引用 |
| 直连网站打不开 | 该站直连可能被墙/不稳定；删除该条规则或改为走代理 |
| 想撤销 | 恢复 `.bak` 备份，或从 prepend 中删除该行后重新激活 |

## 8. 多订阅场景

- 扩展文件按订阅绑定（`option.rules`），只影响对应订阅；切换订阅后规则集随订阅切换。
- 需要所有订阅都生效 → 用全局 Merge.yaml 的 `prepend-rules`。
