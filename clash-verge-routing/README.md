# clash-verge-routing

Clash Verge / Clash Verge Rev 按域名分流配置技能：让指定网站**直连（DIRECT）**或**走代理（PROXY）**，支持自定义策略。

## 它能做什么

- 自动定位当前订阅绑定的 **rules 扩展文件**（`%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles\`）
- 幂等添加 `DOMAIN-SUFFIX,xxx,DIRECT` 规则（已存在自动跳过）
- 修改前**自动备份**（`.bak-时间戳`），可随时回滚
- 分流按连接自动判断：**同时打开两个网页，一个直连一个走代理，互不干扰**
- 与订阅更新兼容：规则写在扩展文件里，订阅刷新后不会丢失

## 安装

将本技能目录放入技能根目录（如 `workspace/.user_skills/`），确保 `scripts/add_rules.py` 有 Python 3 + PyYAML 环境：

```bash
python -m pip install pyyaml
```

## 使用

### 直接让 AI 助手操作

对话中说「帮我把 xxx 网站配成直连 / 走代理」即可，助手会自动调用本技能完成配置、提示重新激活并验证。

### 命令行手动使用

```bash
# 让 aps.org、nature.com 直连
python scripts/add_rules.py --direct aps.org nature.com

# 让 youtube.com 走代理
python scripts/add_rules.py --proxy youtube.com

# 混合 + 指定策略组
python scripts/add_rules.py --direct arxiv.org --proxy openai.com --proxy-policy PROXY

# 只预览不写入
python scripts/add_rules.py --dry-run --direct example.com

# 查看当前规则
python scripts/add_rules.py --list
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `--direct` | 直连域名列表（规则 `DIRECT`） |
| `--proxy` | 走代理域名列表（默认策略 `PROXY`） |
| `--proxy-policy` | 自定义代理策略名（如订阅里的组名） |
| `--rules-file` | 指定 rules 扩展文件（跳过自动定位） |
| `--dry-run` | 仅预览，不写入 |
| `--list` | 列出当前规则 |

### 生效步骤

修改规则后 Clash Verge **不会自动重新加载**，需二选一：

1. Clash Verge 订阅页 → 当前订阅 → **重新激活**；或
2. 主界面 → **重启内核**。

## 目录结构

```
clash-verge-routing/
├── SKILL.md                  # 技能说明与工作流
├── scripts/
│   └── add_rules.py          # 幂等添加直连/代理规则脚本
└── references/
    ├── clash-verge-rev.md    # Clash Verge Rev 机制详解与故障排查
    └── domain-groups.md      # 常用网站域名分组（学术/AI/社交/工具）
```

## 常用域名速查

学术文献类（建议直连）：`aps.org` `nature.com` `science.org` `iop.org` `arxiv.org` `doi.org` `sciencedirect.com` `springer.com` 等，完整清单见 `references/domain-groups.md`。

## 说明

- 仅支持 Clash Verge / Clash Verge Rev（mihomo 内核，Windows）；
- 修改前自动备份，恢复方法：用 `.bak-*` 备份覆盖原文件后重新激活订阅。
