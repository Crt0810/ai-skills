---
name: origin-scientific-plot
description: Create or edit publication-ready scientific figures in Origin from MATLAB-exported Excel data, using the shared style.yaml standard, absolute mm geometry, and editable OPJU projects.
---

# Origin Scientific Plot

Automate the MATLAB -> Excel -> Origin -> editable OPJU workflow while keeping data, style, and layout separate. PDF is exported only when the user explicitly requests it.

## Read first

Before any plotting task, read [references/origin-plotting-guide.md](references/origin-plotting-guide.md). It defines the workspace layout, standardized Excel format, plot-spec JSON schema, validation rules, and backend routing.

## Core rules

- The shared `config/style.yaml` is the single source of truth for appearance. Never invent visual settings absent from the YAML or the user's current request.
- Per-figure changes belong in the raw data, plot-spec JSON, and generated Excel. Do not modify `config/style.yaml` or the plotting backends for a new figure.
- Use absolute physical mm geometry, never percentages.
- Keep and save the editable `.opju`. Do not export PDF unless the user explicitly asks.
- Do not silently substitute missing rows, sheets, curves, or data. Report the issue.
- Legends use backend defaults. Optionally set `parameter_name` in the spec (e.g. `"A"`) when the curve parameter is not `N_in`; the prepare script stores it in the workbook and backends use it for legend labels.
- Do not reopen an `.opju` to relabel, reposition, or polish legends unless the user asks for it.

## Workflow

1. Read the guide and inspect the raw numerical data.
2. Parse the user's row/column selection instructions.
3. Create or update `plot_specs/<figure>.json` using the guide's schema.
4. Run `python scripts/prepare_origin_data.py --spec <spec>` to build the standardized workbook.
5. Verify the workbook: requested sheets, X/Y pairs, numeric data, and expected curve counts.
6. Route by layout:
   - `single` -> `scripts/plot_origin.py`
   - `two_panel` -> `scripts/plot_origin_two_panel.py`
   - `three_panel` -> `scripts/plot_origin_three_panel.py`
7. Run the backend with the shared `config/style.yaml` and the figure output directory.
8. Verify the `.opju` exists and curve counts match; report exact output paths. Check PDF only when the user requested it.

For multiple figures, use one batch command:

```powershell
python scripts/plot_all.py --specs plot_specs/Fig1.json plot_specs/Fig2.json --out-dir excel --hide-origin
```

`plot_all.py` prepares each workbook, routes to the correct backend, and verifies the OPJU outputs.

## Origin execution

Use Origin through the `originpro` Python package. The backends support `--dry-run` to validate parsing and configuration without launching Origin. When editing an existing `.opju`, open that project and change only the requested properties instead of rebuilding the figure from scratch. Backends close the Origin session when they finish.

## Quality checks

- Each panel has at least one valid curve; X/Y values are numeric; no unexpected NaN/Inf values.
- Physical page and layer sizes match the configuration; frame on all four sides; major ticks inward; minor ticks off.
- Number of plotted curves equals the requested series.
- OPJU exists after plotting; PDF only when explicitly requested.
