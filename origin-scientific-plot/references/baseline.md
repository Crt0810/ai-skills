# ORIGIN_STABLE_BASELINE.md

# Origin Scientific Plotting — Stable Baseline

Version: v2.2 (2026-09-09)
Status: current accepted baseline for all Origin plotting work.

> Revision log
>
> - v2.2 (2026-09-09): added §27a source-layout specification (AI-friendly Excel
>   output and minimum layout requirements); corrected the §27 stale note —
>   scripts\prepare_origin_data.py exists, is shipped in the Skill and is frozen;
>   marked §34 checklist item 2 as done; synced the engineering-dir SKILL.md to the
>   shipped Skill version (it was still the obsolete V1/V5 draft).
> - v2.1 (2026-09-08): recorded the six-color × six-line-style sequence (§29) and the
>   single-Graph-page three-layer architecture for three-panel figures (§§11–15),
>   replacing the deprecated g2layout/Layout-Page approach.
> - v2.0 (2026-09-08): reconciled three document conflicts (page width 245 vs 250 mm,
>   axis-title size 20 vs 26 pt, PDF default on/off); recorded the real script CLI,
>   runtime environment, plot-spec JSON protocol, manifest verification loop, error
>   recovery, and a future Skill-mapping section. All newly added facts were verified
>   against the actual scripts and local environment.
> - v1.x (earlier): original stable baseline as accepted.

This document records the stable, accepted baseline for the Origin scientific plotting workflow.

Use this file as the default reference for future Origin plotting work.

Do not redesign the workflow from scratch unless explicitly requested.

---

## 1. Current Working Philosophy

The preferred workflow is now:

```text
User provides:
- data file
- sheet name
- row/column selections
- single / two / three-panel layout
- axis titles
- legend information
- output name

Assistant prepares:
- the required Python plotting script
- any small data-preparation helper if necessary

User then:
- runs the Python script locally
- checks the Origin result
- reports any error or visual issue
```

The user no longer intends to rely on Codex to autonomously reason through the whole plotting workflow.

Priority is:

```text
stability > automation
```

[v2.0 note] The practical input protocol is now a plot-spec JSON plus a standardized
Excel workbook (see sections 26 and 27). The assistant edits the spec and the data,
never the stable backends.

---

# 2. Stable Origin Plotting Backends

There are currently three stable plotting entry points:

```text
scripts\
├── plot_origin.py
├── plot_origin_two_panel.py
└── plot_origin_three_panel.py
```

Their roles are:

```text
plot_origin.py
→ single-panel figure

plot_origin_two_panel.py
→ two-panel figure

plot_origin_three_panel.py
→ three-panel figure
```

These are considered stable backends.

Do not casually rewrite them when only the data changes.

[v2.0 note] All three backends are command-line tools with a documented interface
(section 25). Differences between figures belong in the plot spec and the data
preparation step, not in the backends.

---

# 3. Shared Configuration

All layouts use the same global configuration:

```text
config\
└── style.yaml
```

Do not create separate style files such as:

```text
single_panel.yaml
two_panel.yaml
three_panel.yaml
Fig1_style.yaml
Fig2_style.yaml
```

unless explicitly requested.

The design intentionally keeps one shared plotting style.

[v2.0 note] style.yaml is the single source of truth for all numeric style values.
It is versioned (currently `version: 5`). Do not edit it for a single figure
exception; per-figure overrides belong in the plot spec (section 26).

---

# 4. Single-Panel Stable Baseline

The accepted single-panel configuration is:

```text
Graph page:
245 mm × 250 mm

Layer:
110 mm × 85 mm

Centered position:
left = 67.5 mm
top  = 82.5 mm
```

[v2.0 fix] Page width is **245 mm** (matches `style.yaml canvas.width_mm` and the
backend defaults). The value "250 mm" that appears in `README.md` and the old
`SKILL.md` is outdated (single-panel `left` would then be 70 mm); ignore it.
See section 33 for the document-conflict rule.

Origin layer position uses millimeters.

The stable implementation uses:

```text
layer.unit = 4
```

for mm.

The physical graph page size is controlled using the Origin page resolution:

```text
page.width  = page.resx * width_in
page.height = page.resy * height_in
```

Fixed factor behavior uses:

```text
page -afu1;
```

with fallback behavior when needed.

---

# 5. Axis Style

Use a four-sided axis frame.

Show:

- bottom axis
- top axis
- left axis
- right axis

Show major ticks on all four sides.

Numerical tick labels:

```text
bottom → shown
left   → shown
top    → hidden
right  → hidden
```

Default axis/tick styling:

```text
axis/frame line width = 1.5 pt
major tick width      = 1.5 pt
major tick length     = 8 pt
major ticks           = inward
minor ticks           = off
```

Default scale is linear unless explicitly changed.

---

# 6. Numerical Tick Labels

Numerical tick labels must remain native Origin tick labels.

Do not convert numerical tick values into LaTeX text objects.

Default:

```text
font       = Times New Roman
size       = 26 pt
bold       = no
rotation   = 0°
```

Typical Origin settings:

```text
layer.x.label.font = font(Times New Roman);
layer.y.label.font = font(Times New Roman);

layer.x.label.pt = 26;
layer.y.label.pt = 26;

layer.x.label.rotate = 0;
layer.y.label.rotate = 0;

layer.x.label.bold = 0;
layer.y.label.bold = 0;
```

[v2.0 note] The numeric format (decimals / scientific notation / `10^n` display) is
currently not pinned; Origin's native auto-format is used together with auto rescale.
If a fixed format is needed, see section 28 (currently an enhancement item).

---

# 7. Curves

Default curve style:

```text
plot type   = line
line width  = 2 pt
symbols     = off
grid        = off
```

Default color / line-style order (six curves, fixed sequence):

```text
#  color      hex        line style        LabTalk index
1  red        #FB6F6F    solid             0
2  blue       #5E72FF    short dot         6
3  green      #00BB0C    short dash-dot    7
4  purple     #9D3CFF    dash              1
5  orange     #FF8C00    dash-dot-dot      4
6  black      #000000    short dash        5
```

[v2.1] The backends apply colors by modulo (`color_seq[i % len(color_seq)]`) and
line styles by modulo (`style_seq[i % len(style_seq)]`): curves 1–6 get six
distinct color+style pairs, curve 7+ repeats curve 1's pair. Line styles are
written with `plot.set_cmd(f"-d {index}")`; the index follows the Origin LabTalk
enumeration `set name -d #`: 0=solid 1=dash 2=dot 3=dash-dot 4=dash-dot-dot
5=short dash 6=short dot 7=short dash-dot. All values live in `style.yaml`
(section 29). Orange (#FF8C00) is a default pick; change it in style.yaml if a
different orange is preferred.

---

# 8. Axis Titles

Built-in Origin axis titles are cleared.

Axis titles are added as separate LaTeX-style text objects.

Typical formulas:

```text
x title:
\delta

y title:
G_{\rm{dB}}
```

Recommended default title sizes:

```text
x axis title = 20 pt
y axis title = 20 pt
```

Y-axis title is rotated +90° counterclockwise.

[v2.0 note] Two font-size values exist in style.yaml; they are not in conflict:

```text
text.axis_title.size_pt      = 26   → built-in axis titles (cleared, never visible)
latex.axis_titles.font_size_pt = 20 → LaTeX text objects (the ones that are actually shown)
```

The **effective** axis-title size is 20 pt (the LaTeX text objects). The 26 pt
built-in value is dead configuration. Do not change either value without reviewing
both entries.

Important:

Origin must receive single-backslash LaTeX formulas.

Correct:

```text
\q(\delta)
\q(G_{\rm{dB}})
```

Do not double the LaTeX backslashes unnecessarily.

---

# 9. Legend

The built-in Origin legend may be preserved.

Typical legend behavior:

```text
font   ≈ 26 pt
frame  = none
```

Additional standalone LaTeX labels may also be used, for example:

```text
N_{\rm{in}} = 0.5
N_{\rm{in}} = 0.7
N_{\rm{in}} = 1
```

These extra labels can be manually repositioned later in Origin.

Legend positioning is not considered permanently fixed and may be adjusted case by case.

[v2.0 note] The extra-legend placement defaults live in style.yaml:

```text
latex.extra_legend:
  enabled: true
  font_size_pt: 20.0
  start_pos_percent: { x: 73, y: 24 }   # page-percent anchor for the first label
  dy_percent: 5                          # vertical step between consecutive labels
  position: blank_area
```

These are the accepted defaults; override per figure only in the plot spec or a
per-figure YAML, never by editing the global YAML.

---

# 10. Two-Panel Layout

Stable script:

```text
plot_origin_two_panel.py
```

Accepted panel geometry:

```text
Fig(a):
85 mm × 73 mm

Fig(b):
85 mm × 73 mm

horizontal gap:
20 mm

page:
245 mm × 250 mm
```

The two panels are arranged horizontally:

```text
(a)        (b)
```

[v2.0 add] The backends place the two panels as one centered group (not each panel
centered independently):

```text
group width  = 2 × 85 + 20      = 190 mm
group height = 73 mm

group_left   = (245 - 190) / 2  = 27.5 mm
group_top    = (250 - 73) / 2   = 88.5 mm

Fig(a) left  = 27.5 mm
Fig(b) left  = 27.5 + 85 + 20   = 132.5 mm
Fig(a/b) top = 88.5 mm  (shared → the two panels are vertically centered, top-aligned)
```

The stable two-panel backend should be reused rather than reconstructing the layout for each dataset.

---

# 11. Three-Panel Layout — Important

Stable script:

```text
plot_origin_three_panel.py
```

The three-panel figure is built as ONE graph page with THREE layers.
No Layout Page, no g2layout, no pfit2l. Deterministic mm geometry guarantees
that the bottom panel's left/right edges align exactly with the A+B group
above by construction.

The accepted layout is conceptually:

```text
(a)        (b)

      (c)
```

where panel (c) is a long lower panel.

This architecture was verified end to end: after building Test3, reading the
layer geometry back from the saved .opju gives

```text
Layer A: left=27.517  top=57.997  width=85.005  height=72.983  right=112.522
Layer B: left=132.500 top=57.997  width=85.005  height=72.983  right=217.505
Layer C: left=27.517  top=136.990 width=189.990 height=54.991  right=217.507
page   : 244.983 x 249.978 mm
```

B right == C right within 0.002 mm: the bottom panel is aligned with the
A+B group.

---

# 12. Three-Panel Successful Architecture

The successful three-panel implementation is a single graph page with three
layers, exactly like the two-panel backend but with a third (bottom) layer:

```text
Layer A: (left_a, top_a, 85, 73)
Layer B: (left_b, top_a, 85, 73)
Layer C: (left_a, top_c, 190, 55)
```

The A+B group and C share the same left edge (left_a) and the same right edge
(left_a + 190), so all three panels align without any post-scaling.

Workflow:

```text
worksheet A + worksheet B + worksheet C
      ↓
one Graph page, 3 layers (gp.add_layer)
      ↓
per layer: curves → layer geometry (mm) → axis style → LaTeX axis titles
           → extra legend → panel label
      ↓
final Graph page (the page itself is the deliverable)
```

Do not use g2layout / Layout Page for three-panel figures: g2layout scales each
source graph independently and cannot guarantee edge alignment (that was the
cause of the "bottom panel right edge missing / not aligned" bug the user
reported).

---

# 13. Three-Panel Layout Geometry

Accepted defaults:

```text
final graph page:
245 mm × 250 mm

Fig(a):
85 mm × 73 mm

Fig(b):
85 mm × 73 mm

horizontal gap:
20 mm

vertical gap:
6 mm

Fig(c):
190 mm × 55 mm
```

Group width  = 85 + 20 + 85 = 190 mm
Group height = 73 + 6 + 55  = 134 mm

Centered on the 245×250 page:

```text
left_a = (245 - 190) / 2  = 27.5 mm
top_a  = (250 - 134) / 2  = 58.0 mm
left_b = 27.5 + 85 + 20   = 132.5 mm
top_c  = 58.0 + 73 + 6    = 137.0 mm
```

Therefore:

```text
Fig(a) right = 27.5 + 85  = 112.5 mm
Fig(b) right = 132.5 + 85 = 217.5 mm
Fig(c) right = 27.5 + 190 = 217.5 mm
```

Fig(b) right == Fig(c) right → the A+B group and C share the same right edge.

---

# 14. Three-Panel Page Sizing

The page size is set directly (no pfit2l):

```text
page.kar  = 0;                      // disable Keep Aspect Ratio
page.width  = page.resx * W / 25.4;
page.height = page.resy * H / 25.4;
```

`page.kar` MUST be disabled first: with kar=1 (the default), setting
page.height silently rescales page.width proportionally (e.g. 222x100 becomes
290x100). That lock was the root cause of the original misalignment: the two
source pages could never be given identical physical sizes.

`label -p x y` positions text relative to the ACTIVE LAYER, so every layer
gets its own panel label and legend in the same relative spot; there is no
need to compute page-level coordinates.

---

# 15. Three-Panel Final Layout

The final page IS the graph page itself (no separate Layout window). `expGraph`
exports the active graph page directly to PDF.

Panels are placed with exact mm coordinates (layer.unit=4). Page size and
geometry are deterministic; nothing depends on Origin's auto-scaling.

No g2layout, no Layout window, no pfit2l, no pfit2l-style page fitting.

---

# 16. Failed Three-Panel Approaches — Do Not Reuse

Do not reuse the earlier g2layout / Layout Page approach:

- `g2layout` with `aspectratio:=1` scales each source graph independently by
  its own aspect ratio; the TopAB and BottomC source pages always end up with
  different scaled widths, so the bottom panel's right edge does not align
  with the A+B group (reported by the user as "bottom panel right side
  missing / not aligned").
- Forcing layer geometry on a Layout page does not work: on Layout pages
  `page.active` does not switch layers — all layer reads return the same
  placeholder values.
- Unifying the two source pages to identical physical sizes does not fix it
  either: g2layout scales by layer/content, not by page size.

The accepted replacement is the single-graph-page three-layer geometry
described above.

---

---

# 17. Standardized Excel Format

The Origin plotting backends use a standardized worksheet structure.

For three curves:

```text
Row 1:
x_1    y_1    x_2    y_2    x_3    y_3

Row 2:
X      Y      X      Y      X      Y

Row 3:
1      1      2      2      3      3

Row 4:
parameter / legend values
for example:
0.5    0.5    0.7    0.7    1      1

Row 5:
variable names
for example:
delta  GdB    delta  GdB    delta  GdB

Row 6:
condition / comment

Row 7:
blank

Row 8+:
numerical data
```

Each curve is an independent XY pair.

[v2.0 note] The row roles are also recorded in `style.yaml data_defaults.metadata_rows`
with these labels: short_name(1) / designation(2) / curve_id(3) / N_in(4) /
variable(5) / condition(6) / separator(7) / data_start(8). The backends parse exactly
these rows; the short names in Row 1 are used as Origin worksheet column names.

[v2.0 add] Parser rule (as implemented): columns are scanned pairwise; a pair is
treated as one independent curve when the designation row reads "X" followed by "Y".
Non-numeric cells in the data region are coerced to NaN. Each curve must contribute
at least one valid (x, y) point, otherwise the backend fails with a useful message.

---

# 18. Raw MATLAB Data

MATLAB should preferably save numerical data in a simple file format.

Recommended:

```text
.xlsx
```

For simple column-oriented output:

```text
Column 1 → x
Column 2 → y for A=1
Column 3 → y for A=2
Column 4 → y for A=3
```

This is acceptable.

If raw data does not match the standardized Origin workbook format, transform the data before calling the stable plotting backend.

[v2.0 note] The transformation step is owned by the assistant and produces (a) a
standardized Excel workbook (section 17) and (b) a plot-spec JSON (section 26).
See section 27 for the validation checklist applied before calling a backend.

---

# 19. Example Test Dataset

A simple test case is:

```text
y = A sin(x)
```

with:

```text
A = 1, 2, 3
x ∈ [0, 2π]
number of points = 100
```

Excel layout:

```text
Column 1 → x
Column 2 → A=1
Column 3 → A=2
Column 4 → A=3
```

---

# 20. Output Preference

The primary output is the editable Origin project:

```text
.opju
```

This is preferred because further manual adjustment may be performed in Origin.

[v2.0 fix] PDF export is **enabled by default** in the actual configuration
(`style.yaml export.pdf.enabled: true`; backends export PDF through the documented
`expGraph` path + filename syntax). The accepted interpretation is:

```text
.opju → primary deliverable, always required
.pdf  → companion deliverable, exported by default
```

A PDF is not an acceptance gate in itself: if a task only needs the editable project,
the PDF may be ignored (or PDF export may be switched off in style.yaml). Do not
assume PDF is required beyond what the config and the user's request imply.

---

# 21. Future Collaboration Default

For future plotting tasks, the preferred workflow is:

```text
User describes data and layout
→ assistant writes/updates Python
→ user runs locally
→ user checks Origin
→ assistant fixes specific issues if needed
```

[v2.0 note] In practice the assistant now writes/updates a **plot-spec JSON**
(section 26) and a **standardized Excel workbook** (section 27) instead of touching
the stable backends. The "assistant fixes specific issues" loop stays as-is.

Typical request format:

```text
Data:
E:\...\data.xlsx

Sheet:
Data

Layout:
single / two-panel / three-panel

Fig(a):
x = column/row ...
y = columns/rows ...
legend = ...

Fig(b):
...

Axis titles:
x = ...
y = ...

Output:
FigureName.opju
```

[v2.0 add] Optional fields the user may add to the request (mapped into the plot spec):

```text
curve colors / line styles (override)
axis ranges / tick step (reserved, see section 28)
tick label number format (reserved, see section 28)
panel labels (a)/(b)/(c) on/off (see section 30)
export PDF yes/no (default: follow style.yaml)
```

---

# 22. Stability Principle

Once a version has been explicitly confirmed as working, freeze it as the baseline.

When a new issue appears:

```text
1. identify the specific failing component;
2. modify only the necessary part;
3. preserve stable behavior elsewhere;
4. test incrementally.
```

Preferred principle:

```text
minimal changes
+
stable baselines
+
manual verification in Origin
```

---

# 23. Short Reference

Current stable files:

```text
plot_origin.py
plot_origin_two_panel.py
plot_origin_three_panel.py
style.yaml
```

Three-panel rule:

```text
must use the accepted single-graph-page three-layer implementation
```

Default output:

```text
editable .opju (+ companion PDF by default)
```

Default working style:

```text
assistant writes/updates Python
→ user runs locally
→ user checks Origin
→ assistant fixes specific issues if needed
```

This document should be treated as the stable baseline unless explicitly updated.

---

# 24. Runtime Environment (verified 2026-09-08)

The backends run on this machine with:

```text
Origin:     Origin 2024 (C:\Program Files\OriginLab\Origin2024)
Python:     D:\python\python.exe  (Python 3.13.7)
originpro:  1.1.15  (importable from the system Python)
OriginExt:  1.2.5
Deps:       numpy 2.3.2, pandas 3.0.5, openpyxl 3.1.5, PyYAML 6.0.3
```

Usage rules:

1. Run with the **system Python** `D:\python\python.exe`, not with `origin\.venv`.
   The `.venv` in `origin\.venv` is an empty shell (only pip installed) and is not
   part of the runtime.
2. `originpro` requires a licensed, installed Origin on the same machine; it attaches
   to or launches Origin automatically.
3. Before any real run, always execute the backend with `--dry-run` to validate data
   parsing and geometry **without** starting Origin.
4. On first run of a session, Origin may take a while to start or may show dialogs;
   use `--hide-origin` to keep the Origin window hidden.

---

# 25. Script CLI (verified 2026-09-08)

All backends share the same argument style. Examples:

Single panel:

```text
D:\python\python.exe scripts\plot_origin.py ^
  --excel "E:\...\Fig1_standardized.xlsx" ^
  --sheet "Fig1_Standard" ^
  --config "E:\...\origin-scientific-plot\config\style.yaml" ^
  --output-dir "E:\...\figures\Fig1" ^
  --figure-name "Fig1a" ^
  --dry-run
```

Common arguments:

```text
--config        required  path to config\style.yaml
--output-dir    required  where .opju / .pdf / _manifest.json are written
--figure-name   optional  base name of outputs (defaults: Fig1a / Fig1ab / Fig1abc)
--hide-origin   optional  do not show the Origin window
--dry-run       optional  validate parsing and geometry without starting Origin
```

Panel arguments:

```text
plot_origin.py (single):
  --excel (required)   --sheet (required)

plot_origin_two_panel.py (two):
  --excel-a --sheet-a (required)
  --excel-b --sheet-b (required)

plot_origin_three_panel.py (three):
  --excel-a --sheet-a (required)
  --excel-b --sheet-b (optional, default None)
  --excel-c --sheet-c (optional, default None)
```

Per-panel outputs (two/three panels) are combined into one final figure by the backend.

Successful runs produce:

```text
<figure-name>.opju
<figure-name>.pdf            (when PDF export is enabled)
<figure-name>_manifest.json
```

---

# 26. Plot Specification JSON Protocol

Each plotting task is driven by one plot-spec JSON placed in `plot_specs\<figure>.json`.
This file is the **only thing the assistant creates or edits per figure** — never the
backends, never the global style.

Current accepted schema (extend only with backward-compatible fields):

```json
{
  "layout": "single | two | three",
  "figure_name": "Fig1",
  "source": "path to raw or standardized Excel",
  "sheet": "sheet name to read",
  "output_excel": "path to the standardized workbook produced for the backends",
  "condition": "free-text condition, e.g. A = 1,2,3",
  "panels": {
    "a": {
      "x_column": 1,
      "y_columns": [2, 3, 4],
      "N_in": [1, 2, 3],
      "x_variable": "x",
      "y_variable": "y"
    },
    "b": { "...": "..." },
    "c": { "...": "..." }
  }
}
```

Rules:

1. One spec per figure. Do not reuse a spec across figures with different data.
2. `layout` must match exactly one of the three backends.
3. For two/three-panel layouts, provide one panel entry per figure panel.
4. `N_in` drives the legend labels `N_{\rm{in}} = <value>` (see the manifest output,
   section 31).
5. Optional fields (reserved, backward-compatible): axis ranges, tick format,
   color overrides, panel-label on/off — see sections 28–30. Fields not yet supported
   by the backends must not be silently dropped; record them as pending.
6. The spec lives at `E:\Agent\科研绘图\参考\测试文件\plot_specs\` in the reference
   workspace (examples: Fig1.json, Fig2.json).

---

# 27. Data Preparation and Validation

Raw MATLAB output is converted into the standardized workbook (section 17) before a
backend is called.

[v2.2 note] `scripts/prepare_origin_data.py` now exists (shipped inside the Skill)
and is the frozen conversion helper: raw column-oriented Excel → standardized
workbook (section 17). The assistant reads the raw file first, confirms column
roles, then runs it with explicit `--x-column / --y-columns / --n-in /
--variable / --condition`, then validates with the checklist below. Treat this
helper like a backend: never modify it without a full regression.

Validation checklist before calling any backend:

```text
1. source file exists
2. requested sheet exists
3. requested rows/columns exist
4. selected X/Y data are numerical (or coercible)
5. each requested panel has at least one valid curve
6. Row 1 short names are non-empty for every used column
7. designation row reads X,Y,X,Y,... for the used columns
8. spec.layout matches the chosen backend
9. --dry-run passes without Origin
```

---

# 27a. Source Layout Specification (AI-friendly Excel output)

To make AI plotting require zero guessing, prefer the data source (MATLAB /
simulation program) to output Excel directly in the standardized layout of
section 17. A workbook that IS the standardized format is consumed by the
backends with no conversion.

## Recommended: source outputs the standardized layout directly

```text
Row 1: short names      x_1    y_1    x_2    y_2    x_3    y_3
Row 2: designation      X      Y      X      Y      X      Y
Row 3: curve ids        1      1      2      2      3      3
Row 4: N_in             0.5    0.5    0.7    0.7    1.0    1.0
Row 5: variable names   delta  GdB    delta  GdB    delta  GdB
Row 6: condition        dj=1e-4
Row 7: (blank separator)
Row 8+: numerical data
```

Why this is AI-friendly:

```text
- N_in (Row 4) and variable names (Row 5) travel with the file, so the AI never
  infers them from conversation or column positions.
- Row 2 designation is a parser hard requirement; supplying it removes the most
  common failure mode (the backend rejects any sheet whose designation row is not
  X,Y,X,Y,... pairwise).
- One file = one panel; multi-panel figures use Fig1a_origin.xlsx / b / c.
- The AI can call the backend directly: no conversion step, no guessing.
```

## Minimum requirements when the source cannot produce the 8-row header

When the source exports plain column-oriented data (section 18) and must go
through `prepare_origin_data.py`, ask for these five rules so conversion almost
never fails:

```text
1. Wide table: first column is X, one Y per following column (x | A=1 | A=2 | A=3).
   Avoid long tables (one y column + a group/legend column).
2. Meaningful, non-duplicated header names in row 1 — the AI maps columns by name;
   do not use bare numbers as headers.
3. Clean data region: continuous numeric cells; no blank rows, no merged cells,
   no live formulas (or precomputed values), no units mixed into numeric cells.
4. One panel per sheet/file; never concatenate panels in one sheet separated by
   blank rows.
5. Scientific notation (1e-4) is fine; do not mix text and numeric styles in a
   column.
```

## File naming

```text
raw source:      Fig1a_raw.xlsx / Fig1b_raw.xlsx / Fig1c_raw.xlsx
standardized:    Fig1a_origin.xlsx / Fig1b_origin.xlsx / Fig1c_origin.xlsx
```

---

# 28. Tick-Label Number Format and Axis Ranges (current status)

Current implemented behavior:

```text
scale:      linear (style.yaml scale_defaults)
rescale:    auto — every backend calls layer.rescale() after plotting
tick label: Origin native auto-format (no pinning of decimals / 10^n style)
axis range: not exposed as CLI parameters; explicit From/To/Increment is NOT supported today
```

Accepted rules for now:

- Keep auto rescale. Do not hand-set ranges in the backends.
- If a figure needs explicit axis limits or a fixed tick format, this is a **pending
  enhancement**: add optional spec fields (`x_range`, `y_range`, `tick_format`,
  `tick_step`) and extend the backends behind the existing `deep_resolve` mechanism
  so that old specs remain valid.
- Until implemented, an explicit-range request is handled by the user adjusting the
  axis in Origin after opening the `.opju` (acceptable because the project stays
  editable).

---

# 29. Curve and Color Extension Rules

Implemented behavior (v2.1):

```text
color_sequence      = [#FB6F6F, #5E72FF, #00BB0C, #9D3CFF, #FF8C00, #000000]  (style.yaml)
line_style_sequence = [0, 6, 7, 1, 4, 5]                                       (style.yaml)
plot i uses color_seq[i % len(color_seq)] and style_seq[i % len(style_seq)]
```

So curves 1–6 get six distinct color + line-style pairs; curves 7+ repeat curve 1's
pair. To change the palette or the style order, edit `style.yaml` only (a global
standard change); do not leave it as per-figure improvisation.

Line-style indices follow the Origin LabTalk enumeration (`set name -d #`):
0=solid, 1=dash, 2=dot, 3=dash-dot, 4=dash-dot-dot, 5=short dash,
6=short dot, 7=short dash-dot. Verified on Origin 2024 by rendering six test
curves (N_in=1..6) and pixel-checking the rendered legend symbols.

Backends write the style with `plot.set_cmd(f"-d {style_idx}")` (the originpro
documented method). Names such as "dash" are NOT accepted — only the numeric
index works. The `plot.lstyle` property does not exist on originpro Plot objects,
and `set_int("line.style", n)` silently reads back 0; neither may be used.

Orange (#FF8C00) is a default pick and may be changed in style.yaml.

---

# 30. Panel Labels (a) / (b) / (c)

style.yaml reserves a `figure_labels` block:

```text
figure_labels:
  enabled: false      ← currently OFF
  font_family: Times New Roman
  size_pt: 26.0
  bold: true
```

Current accepted behavior:

- Panel labels are **off by default**. When they are wanted, flip
  `figure_labels.enabled` to `true` in style.yaml (a global standard change) or
  request them per figure.
- Recommended placement (not yet coded): each label at the top-left, outside the
  panel frame, offset ≈ 2 mm from the frame corner, 26 pt bold Times New Roman.

[v2.0 note] This rule is deliberately small because panel labels were not part of
the tested figures; confirm the exact placement once and then freeze it.

---

# 31. Output Verification and Manifest

Every successful run writes:

```text
<figure-name>_manifest.json
```

The manifest is machine-checkable evidence of what was plotted (verified against
`test_output\Fig1a_manifest.json`):

```json
{
  "series_count": 3,
  "series": [
    {
      "curve_id": 1,
      "x_short": "x_1",
      "y_short": "y_1",
      "x_variable": "delta",
      "y_variable": "GdB",
      "n_in": 0.5,
      "condition": "dj=1e-4",
      "n_points": 1769,
      "legend_label": "N_{in} = 0.5",
      "x_min": ...,
      "x_max": ...,
      "y_min": ...,
      "y_max": ...
    }
  ]
}
```

Post-run acceptance checklist:

```text
1. <figure-name>.opju exists and is non-empty
2. <figure-name>.pdf exists when PDF export is enabled
3. <figure-name>_manifest.json exists
4. manifest.series_count == number of y_columns in the spec for that panel
5. every expected legend_label appears in the manifest
6. physical page size in Origin matches the requested dimensions
   (the backends already check page width/height after sizing and warn on mismatch)
```

The user still does the final visual check in Origin; the manifest only catches
structural mismatches (wrong curve count, wrong data ranges, wrong legend).

---

# 32. Known Failures and Recovery

Recorded failure modes and the accepted recovery path:

```text
1. Origin not installed / originpro import fails
   → verify Origin 2024 exists and `import originpro` works in D:\python
   → never proceed to a real run without this check

2. Origin project (.opju) already open in the Origin GUI
   → Origin may refuse to overwrite; close the project in Origin (or use --hide-origin
     and let the backend open its own instance), then rerun

3. Origin shows a blocking dialog (e.g. update prompt, file-association prompt)
   → first run of a session may need a manual click; subsequent runs with
     --hide-origin are normally clean

4. Script fails during parsing (sheet too short, missing sheet, non-numeric data)
   → the error message lists the offending sheet/rows; fix the standardized workbook,
     keep the backend untouched, rerun with --dry-run first

5. Page size mismatch warning after sizing
   → backends apply a corrective scale on page.width/page.height; a warning is
     informational, but if the final PDF is cropped, check export.pdf.crop_to_page

6. Three-panel alignment check
   → the three layers carry exact mm geometry (sections 12-13); if the PDF looks
     misaligned, verify layer geometry readback (section 11) instead of editing
     margins ad hoc
```

General recovery rule (unchanged from section 22): identify the failing component,
modify only that part, keep everything else stable, test incrementally.

---

# 33. Versioning and Document Governance

The workspace contains several normative files. To prevent the v1.x conflicts
(page width, title size, PDF default) from reappearing:

```text
config\style.yaml                        → numeric single source of truth (values)
ORIGIN_STABLE_BASELINE.md (this file)    → architectural single source of truth (workflow, rules)
ORIGIN_PLOTTING_GUIDE.md                 → operation manual (how-to); keep in sync with this file
origin-scientific-plot\SKILL.md          → agent-facing entry point; references this file
README.md                                → changelog of the backends (V5 and up)
```

Conflict rule:

```text
style.yaml wins for numeric values.
This baseline wins for workflow and architecture.
Anything else that disagrees with both must be corrected, not treated as an alternative.
```

Maintenance rule: any change to geometry, style defaults, CLI, or the spec protocol
must be recorded here as a new version row at the top of this file, and the
conflicting files updated in the same change.

---

# 34. Future Skill Mapping (target: package this workflow as a Skill)

This section maps the baseline into the shape of a future installable Skill
(`<skill_root>\origin-scientific-plot\SKILL.md`), so the conversion is mechanical.

```text
Skill frontmatter (name / description):
  name: origin-scientific-plot
  description: create or modify scientific figures in Origin from Excel data;
               use absolute mm geometry from style.yaml, plot-spec JSON input,
               stable backends, editable .opju + PDF output.

Skill input protocol      ← section 26 (plot-spec JSON) + section 27 (standardized Excel)
Skill execution steps     ← sections 24–25 (environment + CLI) + validation checklist (27)
Skill style contract      ← config\style.yaml (single source of truth)
Skill verification        ← section 31 (manifest + post-run checklist)
Skill error recovery      ← section 32 (known failures)
Skill hard rules          ← sections 4, 12, 15, 16 (geometry, single-page three-layer, do-not-reuse)
Skill stability rule      ← section 22 (freeze confirmed versions)

Required skill assets (copied into the skill directory):
  config\style.yaml
  scripts\plot_origin.py
  scripts\plot_origin_two_panel.py
  scripts\plot_origin_three_panel.py
  (optional) plot_specs\Fig1.json as a template
```

Conversion checklist before shipping the Skill:

```text
1. resolve the pending items in sections 28/30 (axis-range support, panel-label placement)
   or document them as known limitations inside the Skill
2. promote a real prepare_origin_data.py helper — DONE: shipped in the Skill, frozen (section 27)
3. install the Skill into one of the skill roots and read its SKILL.md before use
4. run the sin(x) test dataset end-to-end from the Skill entry point
```

---

# 35. Short Reference (v2.0 supplement)

```text
Runtime:   Origin 2024 + D:\python\python.exe + originpro 1.1.15
Backends:  plot_origin.py / plot_origin_two_panel.py / plot_origin_three_panel.py
Input:     plot_specs\<figure>.json + standardized Excel (sections 26–27)
Config:    config\style.yaml (values) + this baseline (architecture)
Dry run:   always run --dry-run before a real run
Output:    .opju + .pdf + _manifest.json
Verify:    manifest + post-run checklist (section 31)
Recovery:  section 32
```

This document should be treated as the stable baseline unless explicitly updated.
