# PDF 文献命名规范与期刊缩写表

## 命名模板（用户确认的硬规则）

- 期刊论文：`{期刊缩写}-{年份}-{标题}.pdf`
- 补充材料：`SM-{期刊缩写}-{年份}-{标题}.pdf`
- 示例：`prl-2026-Dynamic Framework for Criticality-Enhanced Quantum Sensing.pdf` / `SM-prl-2026-Dynamic Framework for Criticality-Enhanced Quantum Sensing.pdf`

### 规则细节

| 项目 | 规则 |
|---|---|
| 年份 | 期刊取正式发表年（首页 `(2026)`）；arXiv 取提交年（`arXiv:2505.06155` → 2025） |
| 标题 | 真实标题，保留空格与大小写；首字母不大写化 |
| Windows 非法字符 | `\ / : * ? " < > \|` 全部替换为空格 |
| 空白 | 合并连续空白、去首尾空白 |
| 尾部标点 | 去掉尾部句点 |
| 长度 | 文件名（含扩展名）≤ 180 字符，超长截断 |
| 同目录冲突 | 目标名大小写不敏感重复时，追加 `-2`、`-3`… 后缀（多版本手稿会用到） |
| 已有新格式命名 | 大小写/缩写不规范的旧文件统一修正；完全正确的不动（标记"不变"） |

### 补充材料判定

- 文件名以 `SM`、`supp`、`supplementary`、`supporting`、`supplemental` 开头
- 或首页文本以 Supplemental/Supplementary/Supporting Information… 开头
- SM 标题去除前缀：`Supplementary Information for "XXX"` → `XXX`
- SM 若独立成文件，按标题继承主论文的期刊缩写 + 年份

## 期刊缩写表（用户已确认）

| 期刊 | 缩写 |
|---|---|
| Physical Review Letters | `prl` |
| Physical Review A | `pra` |
| Physical Review B | `prb` |
| Physical Review C | `prc` |
| Physical Review D | `prd` |
| Physical Review E | `pre` |
| Physical Review X | `prx` |
| Physical Review Research | `prr` |
| **Physical Review Applied** | **`prapplied`**（用户指定，非 prap） |
| Physical Review Materials | `prm` |
| **PRX Quantum** | **`prxquantum`**（用户指定，非 prxq） |
| Reviews of Modern Physics | `rmp` |
| Nature Physics | `np` |
| Nature Communications | `nc` |
| Nature Photonics | `nphotonics` |
| Nature | `nature` |
| Nature Nanotechnology | `nnano` |
| Nature Reviews Physics | `natrevphys` |
| npj Quantum Information | `npjqi` |
| Communications Physics | `commphys` |
| Science | `science` |
| Science Advances | `sciadv` |
| Scientific Reports | `scirep` |
| Applied Physics Letters | `apl` |
| Journal of Applied Physics | `jap` |
| Journal of Chemical Physics | `jcp` |
| Applied Physics Express | `apex` |
| AIP Advances | `aipadv` |
| AVS Quantum Science | `avsqs` |
| Optica | `optica` |
| Optics Express | `oe` |
| Optics Letters | `ol` |
| Photonics Research | `photonres` |
| JOSA B | `josab` |
| New Journal of Physics | `njp` |
| Journal of Physics A | `jpa` |
| Journal of Physics B | `jpb` |
| J. Phys.: Condensed Matter | `jpcm` |
| J. Phys.: Conf. Series | `jpconf` |
| Chinese Physics Letters | `cpl` |
| Chinese Physics B | `cpb` |
| Communications in Theoretical Physics | `ctp` |
| Quantum Science and Technology | `qst` |
| Quantum | `quantum` |
| Physica Scripta | `physscr` |
| EPL | `epl` |
| Annalen der Physik | `annphys` |
| Physics Reports | `physrep` |
| Comptes Rendus Physique | `crphys` |
| Advanced Science | `advs` |
| International Journal of Theoretical Physics | `ijtp` |
| Journal of Fluid Mechanics | `jfm` |
| Applied Magnetic Resonance | `amr` |
| Contemporary Physics | `contphys` |
| Laser & Photonics Reviews | `lpr` |
| Laser & Optoelectronics Progress | `lop` |
| J. Infrared Millim. Waves | `jirfmw` |
| IEEE | `ieee` |
| arXiv | `arxiv` |
| Chaos | `chaos` |
| National Science Review | `nsr` |

### 旧文件拼写错误 → 规范缩写（归一化映射）

`nphoton→nphotonics`、`prappliad/prapliad/prap→prapplied`、`prxq→prxquantum`、
`arxivl/arxivp→arxiv`、`sciencereports→scirep`、`physrevlett→prl`、`physrevapplied→prapplied`、
`naturecomms/natcomms→nc`、`naturephys→np`、`naturephot→nphotonics`、`opticsexpress→oe`、
`optlett/opticsletters→ol`、`applphyslett→apl`、`japplphys→jap`、`revmodphys→rmp`

## 关键兜底逻辑

- **知名论文兜底**（标题匹配）：`quantum limits on noise in linear amplifiers`→prd-1982；
  `on the measurement of a weak classical force...`→rmp-1980；`four golden lessons`→nature-2003
- **旧文件名解析**：已按 `{缩写}-{年份}-{标题}` 命名但大小写/缩写不对的文件，直接解析旧名归一化；
  两位年份 `92` → 1992（≥80 归 19xx，否则 20xx）
- **DOI 识别**：文件名即 DOI（`PhysRevA.106.053714.pdf`、`s41534-019-0195-2.pdf`）或首页 DOI → 期刊
- **Crossref 补全**：DOI 优先查 `api.crossref.org/works/<doi>`；无 DOI 按标题 `query.bibliographic`
  模糊查询，取 title_key 匹配分最高者（完全一致=3 / 包含=2 / 前缀=1）
- **Crossref 标题覆盖**：仅当 crossref 标题 key 包含在提取标题 key 内（提取标题被作者行/摘要污染时），
  或用提取标题为空/过短时，才用 crossref 干净标题替换

## 踩过的坑（必须遵守）

1. **PowerShell 限制**：`&&` 与 heredoc 不可用；内联 `python -c` 里含 `<` `>` `&` `|` 会被解析夹死 → 一律写 .py 文件再跑；`| Select-Object -First 1` 会立即杀掉 python 进程（首行输出后 SIGPIPE），**不要用管道截断正在写 CSV 的脚本**
2. **pypdf 字体警告刷屏** → 必须 `warnings.filterwarnings('ignore')` + pypdf logger 设 CRITICAL
3. **Unicode 代理对** `\ud800-\udfff` 写 JSON 必崩 → 清洗；PUA 区 `\ue000-\uf8ff`、零宽字符也需剥离
4. **元数据 creation_date 是 datetime 对象**，`re.sub` 报 "expected string" → clean() 先 `str(s)`
5. **加密 PDF**（AES）报 `cryptography>=3.1 is required`，缺依赖无法读取 → 进未处理清单，不装依赖不重试（需先向用户说明）
6. **文件被占用**（WinError 32，用户在阅读器打开）→ 标记"文件被其他程序占用"，用户关闭后重跑 `--execute` 补改
7. **同标题多副本**（手稿多个草稿）→ 冲突后缀必须基于稳定 base 重算（`base-2`、`base-3`…），
   不能在新名上反复续接（否则出现 `-2-3-4-5`）
8. **页眉年份误判**：`PhysRev Lett 75, 4587 (1995)` 是参考文献引文不是页眉 → 页眉年份只匹配
   Abstract/Received 之前文本块，且排除 `Phys. Rev.` 开头
9. **`optics|optica` 无词边界**会误杀 "Optical isolator..." 标题 → 必须加 `\b`
10. **期刊检测排除机构行**：`Center for Quantum Science and Technology` 等以 AFFIL 正则过滤，
    避免误判期刊
11. **两词大写姓名行**（`Markus Aspelmeyer *`）+ 下一行是机构 → 判为作者行，防止混入标题
12. **标题尾部作者后缀**：`First Last et al`、`Author, Author, Author et al` → AUTH_SUFFIX 剥离
13. **Nature 引用行污染**：`Giazotto, F. et al. Coherent ... Nat Commun (2026).` → 剥前缀作者、
    尾部期刊(年份)、URL/DOI 残留
14. **AIP 首页垃圾行**：`View Online` / `Export Citation` / `RESEARCH ARTICLE` / 分号作者名单 → 过滤
15. **Crossref 查询条目是作品本体**（无 `message` 包裹，按标题查时）→ `m = it.get('message') or it`
16. **DOI 文件名尾缀**：`PhysRevA.91.033818-accepted.pdf` → 先剥 `-accepted|final|published|submitted|v\d+` 再查
17. **跨轮对账**：执行改名后 CSV 必须与实际磁盘核对（旧名消失+新名存在=成功）；
    重新生成计划时若磁盘已有新名，会凭空多出 `-2` 后缀 → 用 `NO_DISK_CHECK=1` 恢复纯净映射
