---
name: origin-scientific-plot
description: 用 Origin 从 Excel 数据生成科研论文图，输出可编辑 .opju + PDF。当用户要求用 Origin 绘图/出图、科学绘图、论文插图、单面板/双面板/三面板多曲线图，或给出数据文件要求"按既有样式自动绘图"时使用。固定绝对 mm 几何、Times New Roman、LaTeX 轴标题；输入为原始列式 Excel + plot spec，输出经稳定后端完成，支持 dry-run 校验。
---

# Origin Scientific Plot

在 Origin 中按固定科研样式绘制单/双/三面板多曲线图，交付可编辑 `.opju`（主产物）与 PDF（默认伴随）。

## 硬规则

- **稳定优先**：所有变动只发生在数据文件与 plot spec，**永不修改** `scripts/plot_origin*.py` 与 `config/style.yaml`。
- **真相源**：数值样式以 `config/style.yaml` 为准；几何、流程、协议、错误恢复以 `references/baseline.md` 为准。
- **三面板必须用单 Graph 页 3 图层架构**：显式 mm 几何（页 245×250、组宽 190 高 134、左缘 27.5mm、组垂直居中），三面板右边缘按构造必然对齐；禁止 g2layout/Layout Page/pfit2l。布局由 `--arrangement` 选择：`ab-top`（默认，A/B 上排各 85×73、C 整宽 190×55 下排）或 `a-top`（A 整宽 190×55 上排、B/C 各 85×73 下排，几何见 baseline §13a）。
- 轴标题用 LaTeX 文本对象（20pt），刻度标签保持 Origin 原生（Times New Roman 26pt）；不要双重转义反斜杠。

## 运行环境（本机已核验）

```text
Origin:   Origin 2024 (C:\Program Files\OriginLab\Origin2024)
Python:   D:\python\python.exe (3.13.7)，originpro 1.1.15
注意:    origin\.venv 是空壳，不要用；正式运行前先 --dry-run
```

## 标准流程

1. 解析用户请求 → 写 `plot_specs/<figure>.json`（模板见 `assets/plot_spec_template.json`）。
2. 原始 Excel → `scripts/prepare_origin_data.py` 生成标准化 workbook（8 行元数据头 + 数值区）。
3. 按校验清单检查（见下）。
4. 选对应后端真实运行（先 `--dry-run`）。
5. 按 manifest + 产物清单验收（见下）。

## 输入协议

plot spec 字段（`layout` 必为 single/two/three；`panels.a/b/c` 每面板给 `x_column`、`y_columns`、`N_in`、`x_variable`、`y_variable`）。`N_in` 生成图例标签 `N_{in} = <value>`。

源头数据排版（AI 友好，画图前先按此检查/指导数据文件，完整模板见 `references/baseline.md` §27a）：

```text
优先：源头（MATLAB/仿真程序）直接输出标准格式 = 下方 8 行元数据头 + 数值区，
      后端可直接消费、无需转换；N_in 与变量名随文件携带，AI 零猜测。
兜底：源头输出普通宽表（首列 X、后续每列一个 Y；表头有意义不重复；数据区连续
      纯数值、无空行/合并单元格/公式；一面板一表；科学计数法可用但勿与文本混排），
      再由 scripts\prepare_origin_data.py 显式参数转换。
命名：Fig1a_raw.xlsx（原始）→ Fig1a_origin.xlsx（标准）；一面板一文件。
```

标准化 Excel 结构（每曲线一对 XY 列）：

```text
Row 1: short names      x_1 y_1 x_2 y_2 ...
Row 2: designations     X   Y   X   Y   ...
Row 3: curve ids        1   1   2   2   ...
Row 4: N_in values      0.5 0.5 0.7 0.7 ...
Row 5: variable names   delta GdB delta GdB ...
Row 6: condition
Row 7: blank
Row 8+: numerical data
```

准备命令示例：

```text
python scripts\prepare_origin_data.py --input raw\data.xlsx --sheet Data ^
  --x-column 1 --y-columns 2,3,4 --n-in 0.5,0.7,1 ^
  --variable x,GdB --condition "dj=1e-4" --output generated\Fig1_origin.xlsx
```

## 后端 CLI

```text
单面板:   scripts\plot_origin.py            --excel <std.xlsx> --sheet Standard ...
双面板:   scripts\plot_origin_two_panel.py  --excel-a <a.xlsx> --sheet-a Standard --excel-b <b.xlsx> --sheet-b Standard ...
三面板:   scripts\plot_origin_three_panel.py --excel-a --sheet-a [--excel-b --sheet-b --excel-c --sheet-c] [--arrangement ab-top|a-top] ...

公共参数: --config config\style.yaml  --output-dir <out>  --figure-name <Name>
          --hide-origin  隐藏 Origin 窗口
          --dry-run      不启动 Origin，只校验解析与几何（正式运行前必跑）
```

## 校验清单（后端调用前）

```text
1 源文件存在；2 sheet 存在；3 行列存在；4 X/Y 数据数值化；
5 每面板至少 1 条有效曲线；6 Row1 短名非空；7 designation 为 X,Y,X,Y...；
8 spec.layout 与后端匹配；9 --dry-run 通过
```

## 输出与验收

每次运行产出 `<name>.opju`、`<name>.pdf`、`<name>_manifest.json`（记录每条曲线的图例标签、点数、数据范围）。

```text
1 .opju 存在且非空；2 PDF 存在（style.yaml 默认开启）；3 manifest 存在；
4 manifest.series_count == spec y_columns 数；5 图例标签与预期一致；6 页面尺寸匹配
```

## 已知限制

```text
- 曲线样式：固定 6 色 × 6 线型序列（红#FB6F6F / 蓝#5E72FF / 绿#00BB0C / 紫#9D3CFF / 橙#FF8C00 / 黑#000000 × 实线 / 短点线 / 短点划线 / 划线 / 双点划线 / 短划线）；>6 条时按取模循环复用第 1 条样式
- 线型经 plot.set_cmd("-d <index>") 写入；索引按 Origin LabTalk 枚举 0=solid 1=dash 2=dot 3=dash-dot 4=dash-dot-dot 5=short dash 6=short dot 7=short dash-dot
- 显式坐标范围/刻度步长/刻度数字格式：后端未支持，保持 auto rescale + Origin 原生格式（增强项）
- 面板标签：三面板固定加 (a)(b)(c)、双面板默认加 (a)(b)、单面板默认不加；style.yaml figure_labels 为保留配置（后端暂未读取）
```

## 错误恢复速查

```text
- originpro import 失败 → 确认 Origin 2024 安装 + D:\python 可 import originpro
- .opju 被 Origin GUI 占用 → 关闭工程后重跑
- Origin 首启弹窗 → 第一次人工确认，之后 --hide-origin 正常
- 解析失败 → 报错含具体 sheet/行，修正标准化 Excel，先 --dry-run 再跑
- 三面板疑似不对齐 → 先回读三层 mm 几何（section 11/13），不要 ad hoc 改 margin
```

## 深度参考

`references/baseline.md` 是完整规范，仅在需要细节时读取，按需 grep：

```text
grep "24. Runtime\|25. Script CLI\|26. Plot Specification\|27. Data Preparation\|31. Output Verification\|32. Known Failures" references\baseline.md
```
