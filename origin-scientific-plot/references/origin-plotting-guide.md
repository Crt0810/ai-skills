# ORIGIN_PLOTTING_GUIDE.md

# Origin Scientific Plotting Workflow Guide

## 1. Purpose

This workspace automates scientific plotting using:

- MATLAB for numerical calculation and raw data generation;
- Codex for understanding natural-language plotting instructions;
- Python for data preparation and Origin automation;
- Origin / OriginPro for final scientific figures.

The intended workflow is:

```text
MATLAB
   ↓
raw numerical data
   ↓
Codex interprets the user's request
   ↓
plot specification JSON
   ↓
prepare_origin_data.py
   ↓
standardized Origin Excel workbook
   ↓
plot_origin*.py
   ↓
Origin
   ↓
editable OPJU (PDF only when requested)
```

The main design principle is:

> Scientific data, plotting style, and figure layout must remain separate.

New figures should normally require new data/specifications, not new plotting scripts.

---

# 2. Expected workspace structure

```text
origin\
│
├── AGENTS.md
├── ORIGIN_PLOTTING_GUIDE.md
│
├── data\
│   ├── Fig1_raw.xlsx
│   ├── Fig2_raw.xlsx
│   └── ...
│
├── generated\
│   ├── Fig1_origin.xlsx
│   ├── Fig2_origin.xlsx
│   └── ...
│
├── plot_specs\
│   ├── Fig1.json
│   ├── Fig2.json
│   └── ...
│
├── figures\
│   ├── Fig1\
│   ├── Fig2\
│   └── ...
│
└── origin-scientific-plot\
    │
    ├── SKILL.md
    │
    ├── config\
    │   └── style.yaml
    │
    └── scripts\
        ├── prepare_origin_data.py
        ├── plot_origin.py
        ├── plot_origin_two_panel.py
        └── plot_origin_three_panel.py
```

---

# 3. Stable plotting backends

There are currently three supported layouts.

## 3.1 Single panel

Use:

```text
plot_origin.py
```

Typical use:

```text
one scientific panel
```

---

## 3.2 Two panels

Use:

```text
plot_origin_two_panel.py
```

Layout:

```text
(a)        (b)
```

Do not implement a two-panel figure by modifying `plot_origin.py`.

---

## 3.3 Three panels

Use:

```text
plot_origin_three_panel.py
```

Layout:

```text
(a)        (b)

      (c)
```

Panel (c) is a long lower panel.

The current accepted three-panel implementation uses an Origin Layout Page.

Do not revert to the older method that placed three raw layers directly on one graph page unless explicitly requested.

---

# 4. Shared plotting style

All three plotting backends use:

```text
origin-scientific-plot/config/style.yaml
```

This file controls the global plotting style.

Do not create layout-specific or figure-specific YAML files by default.

---

# 5. Current plotting conventions

## Page

Default physical Origin graph page:

```text
245 mm × 250 mm
```

## Axes

Use a four-sided frame.

Show:
- bottom axis;
- top axis;
- left axis;
- right axis.

Show major ticks on all four sides.

Show numerical tick labels only on:
- bottom;
- left.

Hide duplicate numerical labels on:
- top;
- right.

Major ticks point inward.

Minor ticks are normally disabled.

## Axis line and tick width

Default:

```text
axis/frame line width = 1.5 pt
major tick width      = 1.5 pt
major tick length     = 8 pt
```

## Tick labels

Tick-label numbers remain native Origin tick labels.

Default:

```text
Times New Roman
26 pt
non-bold
horizontal
```

Do not replace numerical tick labels with LaTeX text objects.

## Curves

Default:

```text
line width = 2 pt
```

Default color order:

```text
red
blue
green
```

Symbols are disabled unless explicitly requested.

## Axis titles

Axis titles may use Origin LaTeX-style text objects.

Examples:

```text
delta → \delta
GdB   → G_{\rm{dB}}
```

Do not confuse axis-title LaTeX objects with numerical tick labels.

---

# 6. Raw MATLAB data

MATLAB should preferably export numerical data, not only `.fig` files.

Recommended formats:

```text
.xlsx
.csv
.mat
```

For instructions such as:

> use row 1 as x, rows 2/4/6 as y curves

`.xlsx` is usually the easiest format.

Example row-oriented raw data:

```text
Row 1  → x
Row 2  → curve 1
Row 3  → curve 2
Row 4  → curve 3
...
```

Raw MATLAB output is not assumed to already follow the Origin standardized format.

---

# 7. Standardized Origin Excel format

Each curve must be an independent XY pair.

Example with three curves:

```text
Row 1:
x_1    y_1    x_2    y_2    x_3    y_3

Row 2:
X      Y      X      Y      X      Y

Row 3:
1      1      2      2      3      3

Row 4:
0.5    0.5    0.7    0.7    1      1

Row 5:
delta  GdB    delta  GdB    delta  GdB

Row 6:
condition / comment

Row 7:
blank

Row 8+:
numerical data
```

Important:

```text
x_1 / y_1 → curve 1
x_2 / y_2 → curve 2
x_3 / y_3 → curve 3
```

Different curves may have different numbers of valid data points.

Optional row 7 may contain the curve-parameter name used for legends:

```text
Row 7:
parameter_name=A
```

When omitted, the default is `N_in`. Numerical data still starts at row 8.

---

# 8. Data preparation

Use:

```text
prepare_origin_data.py
```

Typical command:

```powershell
python "E:\Agent\科研绘图\origin\origin-scientific-plot\scripts\prepare_origin_data.py" --spec "E:\Agent\科研绘图\origin\plot_specs\Fig2.json"
```

This script converts raw MATLAB-style Excel data into the standardized workbook required by the Origin plotting backends.

---

# 9. Plot specification JSON

Codex should translate the user's natural-language request into a structured plot specification.

Example:

```json
{
  "layout": "three_panel",
  "figure_name": "Fig2",
  "source": "../data/Fig2_raw.xlsx",
  "sheet": "Data",
  "output_excel": "../generated/Fig2_origin.xlsx",
  "condition": "generated by MATLAB",
  "parameter_name": "A",

  "panels": {
    "a": {
      "x_row": 1,
      "y_rows": [2, 4, 6],
      "N_in": [0.5, 0.7, 1.0],
      "x_variable": "delta",
      "y_variable": "GdB"
    },

    "b": {
      "x_row": 1,
      "y_rows": [8, 10, 12],
      "N_in": [0.5, 0.7, 1.0],
      "x_variable": "delta",
      "y_variable": "GdB"
    },

    "c": {
      "x_row": 1,
      "y_rows": [14, 16, 18],
      "N_in": [0.5, 0.7, 1.0],
      "x_variable": "delta",
      "y_variable": "GdB"
    }
  }
}
```

---

# 10. Interpreting user instructions

Example user request:

> Use row 1 as x.
> Use rows 2, 4, and 6 for panel (a).
> Use rows 8, 10, and 12 for panel (b).
> Use rows 14, 16, and 18 for panel (c).
> N_in is 0.5, 0.7, and 1.
> Use the three-panel layout.

Interpret as:

```text
layout = three_panel

Panel A:
x_row = 1
y_rows = [2, 4, 6]

Panel B:
x_row = 1
y_rows = [8, 10, 12]

Panel C:
x_row = 1
y_rows = [14, 16, 18]

N_in = [0.5, 0.7, 1.0]
```

Codex should then generate/update the JSON specification.

---

# 11. Backend routing

Route strictly by layout.

## Single panel

```text
layout = single
→ plot_origin.py
```

## Two panels

```text
layout = two_panel
→ plot_origin_two_panel.py
```

## Three panels

```text
layout = three_panel
→ plot_origin_three_panel.py
```

Do not create a new plotting backend when an existing supported layout is sufficient.

---

# 12. Example three-panel execution

Assume:

```text
generated/Fig2_origin.xlsx
```

contains:

```text
FigA
FigB
FigC
```

Then run:

```powershell
python "E:\Agent\科研绘图\origin\origin-scientific-plot\scripts\plot_origin_three_panel.py" --excel-a "E:\Agent\科研绘图\origin\generated\Fig2_origin.xlsx" --sheet-a "FigA" --excel-b "E:\Agent\科研绘图\origin\generated\Fig2_origin.xlsx" --sheet-b "FigB" --excel-c "E:\Agent\科研绘图\origin\generated\Fig2_origin.xlsx" --sheet-c "FigC" --config "E:\Agent\科研绘图\origin\origin-scientific-plot\config\style.yaml" --output-dir "E:\Agent\科研绘图\origin\figures\Fig2" --figure-name "Fig2"
```

---

# 13. Validation before plotting

Before calling Origin, verify:

1. source file exists;
2. requested sheet exists;
3. requested rows/columns exist;
4. X data are numerical;
5. Y data are numerical;
6. each panel has at least one curve;
7. parameter arrays such as `N_in` match the number of curves;
8. standardized workbook was generated successfully.

If requested data are missing, do not silently replace them.

Report the issue.

---

# 14. Validation after plotting

A successful Python exit code is not enough.

Verify as much as possible:

- expected Origin worksheets were created;
- expected number of curves were plotted;
- no plots disappeared;
- the requested layout backend was used;
- `.opju` exists;
- `.pdf` exists only when PDF export was explicitly requested.

Report exact output paths.

---

# 15. Stability rule

Treat these files as stable backends:

```text
plot_origin.py
plot_origin_two_panel.py
plot_origin_three_panel.py
style.yaml
```

Do not modify them just because a new figure changes:

- selected rows;
- curve count;
- parameter values;
- filenames;
- MATLAB conditions.

Those belong in:
- the raw data;
- the plot specification;
- the standardized generated workbook.

Only change the stable backend when the user explicitly requests a change in the plotting standard.

---

# 16. Avoid configuration proliferation

Do not automatically create:

```text
single_panel.yaml
two_panel.yaml
three_panel.yaml
Fig1_style.yaml
Fig2_style.yaml
```

Use the shared:

```text
style.yaml
```

unless the user explicitly requests independent styles.

---

# 17. Preferred Codex workflow

For a new plotting request:

```text
1. Read AGENTS.md.
2. Read ORIGIN_PLOTTING_GUIDE.md.
3. Read origin-scientific-plot/SKILL.md.
4. Inspect the raw numerical data.
5. Parse the user's row/column instructions.
6. Generate/update plot_specs/<figure>.json.
7. Run prepare_origin_data.py.
8. Verify the generated standardized workbook.
9. Select the correct plotting backend.
10. Run Origin.
11. Verify OPJU (and PDF only when requested).
12. Report the result.
```

---

# 18. Example user request

Example:

> MATLAB generated `data/Fig4_raw.xlsx`.
> In the Data sheet, row 1 is delta.
> Rows 2, 3, and 4 are panel (a).
> Rows 6, 7, and 8 are panel (b).
> Rows 10, 11, and 12 are panel (c).
> N_in values are 0.5, 0.7, and 1.
> Use the three-panel layout.
> Call the final figure Fig4.

Expected workflow:

```text
data/Fig4_raw.xlsx
        ↓
plot_specs/Fig4.json
        ↓
prepare_origin_data.py
        ↓
generated/Fig4_origin.xlsx
        ↓
plot_origin_three_panel.py
        ↓
figures/Fig4/Fig4.opju
```

PDF is exported only when the user explicitly requests it.

---

# 19. Core philosophy

The workflow should remain:

```text
natural-language request
        ↓
structured plot specification
        ↓
standardized numerical data
        ↓
stable Origin backend
        ↓
publication figure
```

This separation is the central design rule of the workspace.
