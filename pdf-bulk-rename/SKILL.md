---
name: pdf-bulk-rename
description: 批量重命名 PDF 文献，按「期刊缩写-年份-标题」规范整理论文文件名。适用于用户要求把文件夹里的 PDF 文献统一命名、按期刊缩写+年份+标题改名、给补充材料加 SM 前缀、整理混乱的文献库文件名等场景。核心规则已与用户确认：期刊缩写对照表（Physical Review Applied→prapplied、PRX Quantum→prxquantum 等 60+ 项）、年份取正式发表年、同目录冲突加 -2/-3 后缀。使用前应先与用户确认缩写规则；用户确认后按"抽取→识别→补全→计划→执行→核验"流程操作。
---

# PDF 文献批量重命名

## 工作流总览

1. **确认缩写规则**：先向用户提交期刊缩写对照表（`references/naming-rules.md` 全表），用户确认（可能有定制，如 prapplied/prxquantum）后才开始。用户明确授权后跳过预览直接执行。
2. **抽取**：`python scripts/pdf_extract.py --root <文献目录> --meta1 <tmp>\pdf_meta.jsonl --meta2 <tmp>\pdf_meta2.jsonl`
3. **识别+计划**：`python scripts/pdf_rename.py --meta1 ... --meta2 ... --crossref <tmp>\pdf_crossref.jsonl --plan <目录>\_重命名记录_<日期>.csv --skiplist <目录>\_未处理清单_<日期>.csv`
4. **Crossref 补全（可选）**：对 SKIP 中疑似真实论文的文件，先跑 `python scripts/pdf_crossref.py --meta1 ... --meta2 ... --plan <计划csv> --out <tmp>\pdf_crossref.jsonl`，再重跑第 3 步（补全后计划会显著提升 RENAME 数量）
5. **确认**：向用户展示统计（RENAME/SKIP）与抽样新名，或按用户要求直接执行
6. **执行**：同第 3 步命令加 `--execute`
7. **核验**：全量核对 CSV 与磁盘（RENAME 行=旧名消失+新名存在；SKIP/不变行=旧名仍在），向用户交付两份 CSV 并说明 SKIP 分类

## 硬性规则（用户确认，不可更改）

- 命名模板：`{缩写}-{年份}-{标题}.pdf`；补充材料 `SM-{缩写}-{年份}-{标题}.pdf`
- 年份：期刊取正式发表年（首页 `(2026)`）；arXiv 取提交年（`arXiv:2505.06155` → 2025）
- 标题：真实标题保留空格大小写；Windows 非法字符 `\ / : * ? " < > |` → 空格；合并空白；去首尾点；≤180 字符
- 同目录目标名大小写不敏感冲突 → `-2`、`-3` 后缀（基于稳定 base 重算，绝不续接成 `-2-3-4`）
- 范围默认全含：论文+预印本+补充材料；图/PPT/作业/讲义等非论文文件不改名、列入未处理清单

## 脚本说明

- `scripts/pdf_extract.py`：递归扫描 root 下全部 PDF，抽取首页/次页文本（p1/p2）与元数据（title/author/cdate/npages），写两个 jsonl。读取失败记录 err 字段。
- `scripts/pdf_crossref.py`：对计划 CSV 中 SKIP 的文件按 DOI/标题查询 Crossref 补全（title/year/journal），增量写缓存 jsonl。仅查询真实论文候选（文件名/元数据/首页首行像标题者）。
- `scripts/pdf_rename.py`：主脚本。期刊检测（页眉+DOI+全文细分）→ 年份提取 → SM 判定 → 标题提取（元数据优先，文本启发式兜底）→ 旧文件名解析 → Crossref 兜底 → 冲突处理。`--execute` 才真改名，否则只出计划 CSV+统计+抽样。

## 执行纪律

- **先计划后执行**：不带 `--execute` 跑一遍，检查统计与抽样，质量满意后再执行
- **执行后必须核验**：全量比对 CSV 与磁盘；抽样验证新名存在、旧名消失
- **不跳步、不降级**：抽取失败的加密/损坏 PDF 明确列入未处理清单并说明原因；文件被占用（WinError 32）标记后提示用户关闭阅读器再补改
- **跨轮对账**：若中途重跑计划且磁盘已有新名，加环境变量 `NO_DISK_CHECK=1` 恢复纯净映射，避免凭空 -2 后缀
- **交付**：重命名记录 CSV（旧路径,旧名,新名,状态,备注）+ 未处理清单 CSV（路径,原因,文件名），用 present_files 交付

## 环境注意（Windows）

- PowerShell 不支持 `&&` 与 heredoc；含 `<` `>` `&` `|` 的 Python 代码必须写成 .py 文件再运行
- **禁止用 `| Select-Object -First 1` 截断运行中的脚本**（会立即杀进程、丢输出）
- pypdf 需要 `warnings.filterwarnings('ignore')` 抑制字体警告刷屏
- 读 jsonl 用 Python 而非 PowerShell `Get-Content`（避免编码乱码）

## 参考

- 完整期刊缩写表、SM 判定、兜底逻辑、踩坑清单：见 `references/naming-rules.md`
