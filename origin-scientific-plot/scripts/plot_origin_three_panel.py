
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_origin.py

V1 execution script for the user's standardized Origin plotting workflow.

Current supported input format
------------------------------
A standardized Excel sheet like "Fig1_Standard", with:

Row 1 : short names       -> x_1, y_1, x_2, y_2, ...
Row 2 : designation       -> X,   Y,   X,   Y,   ...
Row 3 : curve_id          -> 1,   1,   2,   2,   ...
Row 4 : N_in              -> 0.5, 0.5, 0.7, 0.7, ...
Row 5 : variable          -> delta, GdB, delta, GdB, ...
Row 6 : condition/comment -> dj=1e-4, ...
Row 7 : blank separator
Row 8+ : numeric data

Main goals
----------
1. Read standardized Excel data.
2. Detect independent XY pairs: (x_1,y_1), (x_2,y_2), ...
3. Keep each curve's own X/Y range.
4. Use N_in as the curve attribute and legend label.
5. Build one Origin figure using the defaults in style.yaml.
6. Save editable .opju and export .pdf.

Notes
-----
- This script is designed for the user's local machine with Origin installed.
- It uses 'originpro' for Origin automation.
- A --dry-run mode is included so you can test parsing without Origin.
- V6 validates that Origin actually creates the expected data plots before
  it reports success. Geometry is set using Origin's documented physical units.

Recommended usage
-----------------
python plot_origin.py ^
  --excel "D:\\MyPaper\\Fig1_standardized_for_Origin.xlsx" ^
  --sheet "Fig1_Standard" ^
  --config "D:\\ResearchTools\\origin-scientific-plot\\config\\style.yaml" ^
  --output-dir "D:\\MyPaper\\Figures\\Fig1" ^
  --figure-name "Fig1a"

Dry-run test
------------
python plot_origin.py ^
  --excel "D:\\MyPaper\\Fig1_standardized_for_Origin.xlsx" ^
  --sheet "Fig1_Standard" ^
  --config "D:\\ResearchTools\\origin-scientific-plot\\config\\style.yaml" ^
  --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------

@dataclass
class SeriesInfo:
    curve_id: int
    x_short: str
    y_short: str
    x_variable: str
    y_variable: str
    n_in: float
    condition: str
    x: np.ndarray
    y: np.ndarray

    @property
    def legend_label(self) -> str:
        # You can change the exact legend wording here if needed.
        return rf"N_{{in}} = {self.n_in:g}"

    @property
    def x_title(self) -> str:
        return self.x_variable if self.x_variable else self.x_short

    @property
    def y_title(self) -> str:
        return self.y_variable if self.y_variable else self.y_short


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "canvas": {
        "width_mm": 245.0,
        "height_mm": 250.0,
        "background": "white",
    },
    "single_panel": {
        "width_mm": 110.0,
        "height_mm": 85.0,
        "position": {
            "anchor": "center",
            "offset_x_mm": 0.0,
            "offset_y_mm": 0.0,
        },
    },
    "axes": {
        "frame": {"left": True, "right": True, "top": True, "bottom": True},
        "line_width_pt": 1.5,
        "scale_defaults": {"x": "linear", "y": "linear", "rescale": "auto"},
        "ticks": {
            "direction": "in",
            "major": {"enabled": True, "line_width_pt": 1.5, "length_pt": 8.0},
            "minor": {"enabled": False},
        },
        "tick_labels": {
            "font_family": "Times New Roman",
            "size_pt": 26.0,
            "show_bottom": True,
            "show_top": False,
            "show_left": True,
            "show_right": False,
        },
        "grid": {
            "major_x": False, "major_y": False,
            "minor_x": False, "minor_y": False,
        },
    },
    "curves": {
        "default_plot_type": "line",
        "line_width_pt": 2.0,
        "color_sequence": ["#FB6F6F", "#5E72FF", "#00BB0C", "#9D3CFF", "#FF8C00", "#000000"],
        "line_style_sequence": [0, 6, 7, 1, 4, 5],
        "symbol": {"enabled": False, "type_sequence": None, "size_pt": None},
    },
    "text": {
        "font_family": "Times New Roman",
        "axis_title": {"size_pt": 26.0, "bold": False},
        "tick_label": {"size_pt": 26.0},
        "legend": {"enabled": "auto", "size_pt": 26.0, "frame": False, "position": "auto"},
    },
    "export": {
        "save_origin_project": True,
        "project_extension": "opju",
        "pdf": {"enabled": True, "vector": True, "overwrite": True,
                "embed_fonts": None, "crop_to_page": True},
    },
    "latex": {
        "axis_titles": {
            "enabled": True,
            "font_size_pt": 20.0,
            "y_font_size_pt": 20.0,
            "x_formula": "auto",
            "y_formula": "auto",
        },
        "extra_legend": {
            "enabled": True,
            "font_size_pt": 20.0,
            "as_individual_labels": True,
            "start_pos_percent": {"x": 73, "y": 24},
            "dy_percent": 5,
            "position": "blank_area",
        },
    },
    "behavior": {
        "require_absolute_geometry": True,
        "user_request_overrides_defaults": True,
        "preserve_editable_origin_project": True,
        "warn_on_fallback": True,
    },
}


def deep_resolve(user: Any, default: Any) -> Any:
    """
    Recursively resolve a user YAML object against defaults.

    Important behavior:
    - Missing keys use defaults.
    - None/null uses the default when the default is non-None.
    - Explicit null remains null for fields whose default is also None.
    """
    if isinstance(default, dict):
        user_dict = user if isinstance(user, dict) else {}
        return {
            key: deep_resolve(user_dict.get(key), value)
            for key, value in default.items()
        } | {
            key: value
            for key, value in user_dict.items()
            if key not in default
        }

    if user is None:
        return default

    return user


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in {path}: {e}") from e

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"Top level of YAML must be a mapping/object: {path}")

    cfg = deep_resolve(raw, DEFAULT_CONFIG)
    validate_config(cfg)
    return cfg


def cfg_float(value: Any, default: float) -> float:
    """Return a finite numeric config value, otherwise the supplied default."""
    try:
        out = float(value)
        if not math.isfinite(out):
            raise ValueError
        return out
    except (TypeError, ValueError):
        return float(default)


def cfg_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "1", "on"}:
            return True
        if v in {"false", "no", "0", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def validate_config(cfg: Dict[str, Any]) -> None:
    """Fail early with useful messages instead of obscure NoneType errors."""
    canvas = cfg.get("canvas", {})
    panel = cfg.get("single_panel", {})
    pos = panel.get("position", {}) if isinstance(panel, dict) else {}

    cw = cfg_float(canvas.get("width_mm"), 250.0)
    ch = cfg_float(canvas.get("height_mm"), 250.0)
    pw = cfg_float(panel.get("width_mm"), 110.0)
    ph = cfg_float(panel.get("height_mm"), 85.0)
    ox = cfg_float(pos.get("offset_x_mm"), 0.0)
    oy = cfg_float(pos.get("offset_y_mm"), 0.0)

    if min(cw, ch, pw, ph) <= 0:
        raise ValueError("Canvas and panel dimensions must all be positive.")
    if pw > cw or ph > ch:
        raise ValueError(
            f"Panel ({pw} x {ph} mm) cannot be larger than canvas "
            f"({cw} x {ch} mm)."
        )

    left = (cw - pw) / 2 + ox
    top = (ch - ph) / 2 + oy
    if left < 0 or top < 0 or left + pw > cw or top + ph > ch:
        raise ValueError(
            "Panel offsets place part of the panel outside the canvas. "
            f"Resolved left={left:g} mm, top={top:g} mm."
        )

    default_colors = ["#FB6F6F", "#5E72FF", "#00BB0C", "#9D3CFF", "#FF8C00", "#000000"]
    default_styles = [0, 6, 7, 1, 4, 5]
    colors = cfg.get("curves", {}).get("color_sequence")
    if not isinstance(colors, list) or len(colors) == 0:
        cfg.setdefault("curves", {})["color_sequence"] = list(default_colors)
    else:
        cleaned = [str(c).strip() for c in colors if str(c).strip()]
        cfg["curves"]["color_sequence"] = cleaned or list(default_colors)

    styles = cfg.get("curves", {}).get("line_style_sequence")
    if not isinstance(styles, list) or not styles:
        cfg.setdefault("curves", {})["line_style_sequence"] = list(default_styles)
    else:
        cleaned_s = []
        for s in styles:
            try:
                v = int(s)
            except (TypeError, ValueError):
                continue
            if 0 <= v <= 7:
                cleaned_s.append(v)
        cfg["curves"]["line_style_sequence"] = cleaned_s or list(default_styles)


def mm_to_inch(mm: float) -> float:
    return mm / 25.4


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise NotADirectoryError(f"Output path is not a directory: {path}")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def to_number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None




def lt_quote(text: str) -> str:
    """Escape only double quotes for LabTalk; keep LaTeX backslashes untouched."""
    return str(text).replace('"', '\"')


def infer_latex_formula(name: str, fallback: str = "") -> str:
    r"""
    Convert a known variable name into the exact LaTeX-style equation string
    wanted by the user for Origin \\q(...).
    """
    src = (name or fallback or "").strip()
    key = src.lower().replace(" ", "").replace("_", "")

    mapping = {
        "delta": r"\delta",
        "gdb": r"G_{\rm{dB}}",
        "gaindb": r"G_{\rm{dB}}",
        "gaindb": r"G_{\rm{dB}}",
        "gain_db": r"G_{\rm{dB}}",
        "omega": r"\omega",
        "kappa": r"\kappa",
        "nin": r"N_{\rm{in}}",
    }
    if key in mapping:
        return mapping[key]

    if src == "N_in":
        return r"N_{\rm{in}}"

    return src or fallback or ""


def build_axis_latex_formulas(cfg: Dict[str, Any], series_list: List[SeriesInfo]) -> Dict[str, str]:
    latex_cfg = cfg.get("latex", {})
    axis_cfg = latex_cfg.get("axis_titles", {})
    x_formula = axis_cfg.get("x_formula", "auto")
    y_formula = axis_cfg.get("y_formula", "auto")

    first = series_list[0]
    if str(x_formula).lower() == "auto":
        x_formula = infer_latex_formula(first.x_variable, first.x_short)
    if str(y_formula).lower() == "auto":
        y_formula = infer_latex_formula(first.y_variable, first.y_short)

    return {"x": str(x_formula), "y": str(y_formula)}


def create_latex_axis_titles(op, cfg: Dict[str, Any], series_list: List[SeriesInfo]) -> None:
    r"""
    Replace only the built-in axis-title text with LaTeX-rendered text objects.

    Exact default formulas:
      X: \\delta
      Y: G_{\\rm{dB}}

    The Y title is rotated counter-clockwise by +90 degrees and enlarged.
    Tick-label numbers are untouched.
    """
    latex_cfg = cfg.get("latex", {})
    axis_cfg = latex_cfg.get("axis_titles", {})
    if not cfg_bool(axis_cfg.get("enabled"), True):
        return

    formulas = build_axis_latex_formulas(cfg, series_list)
    x_fsize = int(round(cfg_float(axis_cfg.get("font_size_pt"), 20.0)))
    y_fsize = int(round(cfg_float(axis_cfg.get("y_font_size_pt"), 20.0)))

    # Clear built-in axis title text only.
    for cmd in ['xb.text$="";', 'xt.text$="";', 'yl.text$="";', 'yr.text$="";']:
        try:
            op.lt_exec(cmd)
        except Exception as e:
            print(f"[WARN] Could not clear built-in axis-title text: {e}")

    x_formula = formulas["x"]
    y_formula = formulas["y"]

    # IMPORTANT: lt_quote does NOT double LaTeX backslashes.
    # The actual LabTalk strings sent to Origin are:
    #   \q(\delta)
    #   \q(G_{\rm{dB}})
    x_cmd = 'label -p 50 94 -j 1 -n AxisXLatex "\\q(' + lt_quote(x_formula) + ')";'
    y_cmd = 'label -p 6 50 -j 1 -n AxisYLatex "\\q(' + lt_quote(y_formula) + ')";'

    print(f"[LATEX COMMAND] X: \\q({x_formula})")
    print(f"[LATEX COMMAND] Y: \\q({y_formula})")

    # X title
    for cmd in [
        x_cmd,
        f'AxisXLatex.fsize={x_fsize};',
        'AxisXLatex.font=font(Times New Roman);',
        'AxisXLatex.x = layer.x.from + (layer.x.to-layer.x.from)/2;',
        'AxisXLatex.y = layer.y.from - 0.16*(layer.y.to-layer.y.from);',
    ]:
        try:
            op.lt_exec(cmd)
        except Exception as e:
            print(f"[WARN] Could not create/set AxisXLatex: {e}")

    # Y title
    for cmd in [
        y_cmd,
        f'AxisYLatex.fsize={y_fsize};',
        'AxisYLatex.font=font(Times New Roman);',
        'AxisYLatex.x = layer.x.from - 0.18*(layer.x.to-layer.x.from);',
        'AxisYLatex.y = layer.y.from + (layer.y.to-layer.y.from)/2;',
    ]:
        try:
            op.lt_exec(cmd)
        except Exception as e:
            print(f"[WARN] Could not create/set AxisYLatex: {e}")

    # First try direct named-object rotation.
    try:
        op.lt_exec("AxisYLatex.angle=90;")
    except Exception as e:
        print(f"[WARN] Direct Y-title rotation failed: {e}")

    # Force rotation using the documented selected-object property S.ANGLE.
    # Positive angle = counter-clockwise.
    try:
        op.lt_exec("page -s AxisYLatex;")
        op.lt_exec("s.angle=90;")
        actual_angle = op.lt_float("s.angle")
        print(f"[LATEX Y ROTATION] requested=+90 deg CCW, actual={actual_angle:g} deg")
    except Exception as e:
        print(f"[WARN] Could not force/read Y-title rotation through selected object: {e}")
    finally:
        try:
            op.lt_exec("page -s;")
        except Exception:
            pass

    print(
        "[LATEX AXIS] "
        f'x={x_formula}, x_size={x_fsize} pt; '
        f'y={y_formula}, y_size={y_fsize} pt, CCW +90 deg'
    )


def create_extra_latex_legend(op, cfg: Dict[str, Any], series_list: List[SeriesInfo]) -> None:
    """
    Keep the built-in legend but remove its frame.
    Also create separate LaTeX-style text labels in a blank area for later manual adjustment.
    """
    latex_cfg = cfg.get("latex", {})
    extra_cfg = latex_cfg.get("extra_legend", {})

    try:
        op.lt_exec("legend.showframe=0;")
    except Exception as e:
        print(f"[WARN] Could not remove built-in legend frame: {e}")

    if not cfg_bool(extra_cfg.get("enabled"), True):
        return

    fsize = int(round(cfg_float(extra_cfg.get("font_size_pt"), 20.0)))
    pos = extra_cfg.get("start_pos_percent", {}) if isinstance(extra_cfg.get("start_pos_percent"), dict) else {}
    px = cfg_float(pos.get("x"), 73.0)
    py = cfg_float(pos.get("y"), 24.0)
    dy = cfg_float(extra_cfg.get("dy_percent"), 5.0)

    for i, s in enumerate(series_list, start=1):
        formula = rf"N_{{\rm{{in}}}} = {s.n_in:g}" if math.isfinite(s.n_in) else rf"Curve\ {s.curve_id}"
        obj_name = f"LegendLatex{i}"
        ypos = py + (i - 1) * dy
        cmds = [
            f'label -p {px:.6g} {ypos:.6g} -j 0 -n {obj_name} "\\q(' + lt_quote(formula) + ')";',
            f'{obj_name}.fsize={fsize};',
            f'{obj_name}.font=font(Times New Roman);',
        ]
        for cmd in cmds:
            try:
                op.lt_exec(cmd)
            except Exception as e:
                print(f"[WARN] Could not create/set {obj_name}: {e}")

    print(
        "[LATEX LEGEND] built-in legend kept and made frameless; "
        f"created {len(series_list)} standalone LaTeX labels, size={fsize} pt"
    )

def color_name_to_origin_index(color_name: str) -> int:
    """
    A small mapping for the user's current default color sequence.
    If you want exact custom RGB later, we can extend this.
    """
    table = {
        "black": 1,
        "red": 2,
        "green": 3,
        "blue": 4,
        "cyan": 5,
        "magenta": 6,
        "yellow": 7,
    }
    return table.get(str(color_name).strip().lower(), 1)


# ---------------------------------------------------------------------
# Parsing the standardized Excel format
# ---------------------------------------------------------------------

def parse_standardized_sheet(excel_path: Path, sheet_name: str) -> List[SeriesInfo]:
    try:
        xls = pd.ExcelFile(excel_path)
    except Exception as e:
        raise RuntimeError(f"Could not open Excel workbook '{excel_path}': {e}") from e

    if sheet_name not in xls.sheet_names:
        available = ", ".join(xls.sheet_names)
        raise ValueError(
            f"Sheet '{sheet_name}' was not found in '{excel_path.name}'. "
            f"Available sheets: {available}"
        )

    try:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    except Exception as e:
        raise RuntimeError(f"Could not read sheet '{sheet_name}': {e}") from e

    if df.shape[0] < 8:
        raise ValueError(
            f"Sheet '{sheet_name}' is too short. Expected at least 8 rows."
        )

    # Metadata rows
    short_names = df.iloc[0, :].tolist()
    designations = df.iloc[1, :].tolist()
    curve_ids = df.iloc[2, :].tolist()
    n_in_row = df.iloc[3, :].tolist()
    variable_row = df.iloc[4, :].tolist()
    condition_row = df.iloc[5, :].tolist()

    # Numeric data begins at row 8 (index 7)
    data = df.iloc[7:, :].copy()

    ncols = df.shape[1]
    series_list: List[SeriesInfo] = []

    col = 0
    while col < ncols - 1:
        desig_this = normalize_text(designations[col]).upper()
        desig_next = normalize_text(designations[col + 1]).upper()

        # V1 rule: treat adjacent X,Y columns as one independent curve.
        if desig_this == "X" and desig_next == "Y":
            x_raw = pd.to_numeric(data.iloc[:, col], errors="coerce")
            y_raw = pd.to_numeric(data.iloc[:, col + 1], errors="coerce")
            mask = x_raw.notna() & y_raw.notna()

            x = x_raw[mask].to_numpy(dtype=float)
            y = y_raw[mask].to_numpy(dtype=float)

            if len(x) == 0:
                col += 2
                continue

            curve_id_value = to_number(curve_ids[col])
            curve_id = int(curve_id_value) if curve_id_value is not None else (len(series_list) + 1)
            n_in_value = to_number(n_in_row[col])
            n_in = float(n_in_value) if n_in_value is not None else float("nan")
            x_short = normalize_text(short_names[col]) or f"x_{curve_id}"
            y_short = normalize_text(short_names[col + 1]) or f"y_{curve_id}"
            x_variable = normalize_text(variable_row[col]) or x_short
            y_variable = normalize_text(variable_row[col + 1]) or y_short
            condition = normalize_text(condition_row[col]) or ""

            series_list.append(
                SeriesInfo(
                    curve_id=curve_id,
                    x_short=x_short,
                    y_short=y_short,
                    x_variable=x_variable,
                    y_variable=y_variable,
                    n_in=n_in,
                    condition=condition,
                    x=x,
                    y=y,
                )
            )
            col += 2
        else:
            col += 1

    if not series_list:
        raise ValueError(
            f"No valid X/Y pairs found in sheet '{sheet_name}'. "
            "Check Row 2 designations."
        )

    return series_list


def build_numeric_dataframe(series_list: List[SeriesInfo]) -> pd.DataFrame:
    """
    Convert a list of independent XY curves to one rectangular DataFrame
    with NaN padding, so it can be easily imported into Origin.
    """
    data_dict: Dict[str, pd.Series] = {}
    for s in series_list:
        data_dict[s.x_short] = pd.Series(s.x, dtype=float)
        data_dict[s.y_short] = pd.Series(s.y, dtype=float)

    df = pd.DataFrame(data_dict)

    # Reorder strictly as x_1,y_1,x_2,y_2,...
    ordered_cols = []
    for s in series_list:
        ordered_cols.extend([s.x_short, s.y_short])
    df = df[ordered_cols]

    return df


def write_manifest_json(series_list: List[SeriesInfo], out_path: Path) -> None:
    manifest = {
        "series_count": len(series_list),
        "series": [
            {
                "curve_id": s.curve_id,
                "x_short": s.x_short,
                "y_short": s.y_short,
                "x_variable": s.x_variable,
                "y_variable": s.y_variable,
                "n_in": s.n_in,
                "condition": s.condition,
                "n_points": int(len(s.x)),
                "legend_label": s.legend_label,
                "x_min": float(np.min(s.x)),
                "x_max": float(np.max(s.x)),
                "y_min": float(np.min(s.y)),
                "y_max": float(np.max(s.y)),
            }
            for s in series_list
        ],
    }
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------
# Origin plotting
# ---------------------------------------------------------------------

def set_origin_page_and_layer_geometry(op, graph, cfg: Dict[str, Any]) -> None:
    """
    Set physical graph page and layer geometry, then force layer element scaling
    to Fixed Factor = 1.

    Origin facts:
      layer.unit = 4  -> mm
      page.width/page.height are page dimensions in dots
      page.resx/page.resy are dots-per-inch values
    """
    canvas = cfg.get("canvas", {})
    panel = cfg.get("single_panel", {})
    position = panel.get("position", {}) if isinstance(panel, dict) else {}

    target_page_w_mm = cfg_float(canvas.get("width_mm"), 245.0)
    target_page_h_mm = cfg_float(canvas.get("height_mm"), 250.0)
    panel_w = cfg_float(panel.get("width_mm"), 110.0)
    panel_h = cfg_float(panel.get("height_mm"), 85.0)
    offset_x = cfg_float(position.get("offset_x_mm"), 0.0)
    offset_y = cfg_float(position.get("offset_y_mm"), 0.0)

    left_mm = (target_page_w_mm - panel_w) / 2.0 + offset_x
    top_mm = (target_page_h_mm - panel_h) / 2.0 + offset_y

    try:
        graph.activate()
    except Exception:
        pass

    # Initial page size set using current page DPI.
    page_w_in = target_page_w_mm / 25.4
    page_h_in = target_page_h_mm / 25.4
    op.lt_exec(
        f"page.width=page.resx*{page_w_in:.12g};"
        f"page.height=page.resy*{page_h_in:.12g};"
    )

    # Calibrate once by reading back the actual physical page size and correcting.
    try:
        actual_w_mm = op.lt_float("page.width/page.resx*25.4")
        actual_h_mm = op.lt_float("page.height/page.resy*25.4")
        if actual_w_mm and abs(actual_w_mm - target_page_w_mm) > 0.05:
            scale_w = target_page_w_mm / actual_w_mm
            op.lt_exec(f"page.width=page.width*{scale_w:.12g};")
        if actual_h_mm and abs(actual_h_mm - target_page_h_mm) > 0.05:
            scale_h = target_page_h_mm / actual_h_mm
            op.lt_exec(f"page.height=page.height*{scale_h:.12g};")
    except Exception as e:
        print(f"[WARN] Could not calibrate physical page size: {e}")

    # Set layer geometry in millimeters.
    op.lt_exec(
        "layer.unit=4;"
        f"layer.left={left_mm:.12g};"
        f"layer.top={top_mm:.12g};"
        f"layer.width={panel_w:.12g};"
        f"layer.height={panel_h:.12g};"
    )

    # Fixed Factor = 1 (do not scale elements with layer frame).
    # page -afu1 is the documented graph-page command to set all layers to fixed factor 1.
    try:
        op.lt_exec("page -afu1;")
    except Exception as e:
        print(f"[WARN] Could not run page -afu1: {e}")
        try:
            op.lt_exec("layer.fixed=1;layer.factor=1;")
        except Exception as e2:
            print(f"[WARN] Could not set layer.fixed/layer.factor: {e2}")

    # Read back geometry and scaling.
    try:
        actual_page_w_mm = op.lt_float("page.width/page.resx*25.4")
        actual_page_h_mm = op.lt_float("page.height/page.resy*25.4")
        actual_unit = op.lt_int("layer.unit")
        actual_left = op.lt_float("layer.left")
        actual_top = op.lt_float("layer.top")
        actual_width = op.lt_float("layer.width")
        actual_height = op.lt_float("layer.height")
        actual_fixed = op.lt_int("layer.fixed")
        actual_factor = op.lt_float("layer.factor")

        print(
            "[ORIGIN GEOMETRY] "
            f"page={actual_page_w_mm:.3f}x{actual_page_h_mm:.3f} mm; "
            f"layer.unit={actual_unit} (4=mm); "
            f"left={actual_left:.3f}, top={actual_top:.3f}, "
            f"width={actual_width:.3f}, height={actual_height:.3f} mm; "
            f"fixed={actual_fixed}, factor={actual_factor:.3f}"
        )
    except Exception as e:
        print(f"[WARN] Could not fully verify physical geometry: {e}")


def apply_origin_style(op, graph, layer, plots, cfg: Dict[str, Any],
                       series_list: List[SeriesInfo]) -> None:
    """
    Apply the user's native Origin axis/tick style.

    Important:
    - Tick-label NUMBERS are ordinary Origin tick labels, not LaTeX objects.
    - Bottom/left tick labels: Times New Roman, 26 pt.
    - Top/right axis lines and major ticks are shown, but duplicate tick-label
      numbers are hidden.
    - Bottom/top share the same line/tick options.
    - Left/right share the same line/tick options.
    """
    axes_cfg = cfg.get("axes", {})
    ticks_cfg = axes_cfg.get("ticks", {})
    major_cfg = ticks_cfg.get("major", {})
    minor_cfg = ticks_cfg.get("minor", {})
    ticklabel_cfg = axes_cfg.get("tick_labels", {})
    curves_cfg = cfg.get("curves", {})
    text_cfg = cfg.get("text", {})
    legend_cfg = text_cfg.get("legend", {})

    axis_lw = cfg_float(axes_cfg.get("line_width_pt"), 1.5)
    major_tick_lw = cfg_float(major_cfg.get("line_width_pt"), 1.5)
    major_tick_len = cfg_float(major_cfg.get("length_pt"), 8.0)
    curve_lw = cfg_float(curves_cfg.get("line_width_pt"), 2.0)

    tick_font = ticklabel_cfg.get("font_family") or "Times New Roman"
    tick_size = cfg_float(ticklabel_cfg.get("size_pt"), 26.0)

    legend_size = cfg_float(legend_cfg.get("size_pt"), 26.0)
    color_seq = curves_cfg.get("color_sequence")
    if not isinstance(color_seq, list) or not color_seq:
        color_seq = ["#FB6F6F", "#5E72FF", "#00BB0C", "#9D3CFF", "#FF8C00", "#000000"]
    style_seq = curves_cfg.get("line_style_sequence")
    if not isinstance(style_seq, list) or not style_seq:
        style_seq = [0, 6, 7, 1, 4, 5]

    try:
        graph.activate()
    except Exception:
        pass

    # --------------------------------------------------------------
    # Axis scale
    # --------------------------------------------------------------
    scale_cfg = axes_cfg.get("scale_defaults", {})
    xscale = str(scale_cfg.get("x") or "linear").lower()
    yscale = str(scale_cfg.get("y") or "linear").lower()
    try:
        layer.xscale = xscale
        layer.yscale = yscale
    except Exception as e:
        print(f"[WARN] Could not set axis scale through GLayer API: {e}")

    # --------------------------------------------------------------
    # Four-sided axes.
    # showAxes=3 means primary + opposite axis line/ticks.
    # Bottom/Top and Left/Right then receive the same explicit options.
    # --------------------------------------------------------------
    axis_cmds = [
        # Show both axes for each direction.
        "layer.x.showAxes=3;",
        "layer.y.showAxes=3;",

        # Tick-label numbers: bottom and left only.
        "layer.x.showLabels=1;",
        "layer.y.showLabels=1;",
        "layer.x2.showlabel=0;",
        "layer.y2.showlabel=0;",

        # Axis lines: identical thickness.
        f"layer.x.thickness={axis_lw};",
        f"layer.x2.thickness={axis_lw};",
        f"layer.y.thickness={axis_lw};",
        f"layer.y2.thickness={axis_lw};",

        # Major ticks only, inward.
        "layer.x.ticks=1;",
        "layer.x2.ticks=1;",
        "layer.y.ticks=1;",
        "layer.y2.ticks=1;",

        # Major tick length/thickness identical on opposite axes.
        f"layer.x.ticklength={major_tick_len};",
        f"layer.x2.ticklength={major_tick_len};",
        f"layer.y.ticklength={major_tick_len};",
        f"layer.y2.ticklength={major_tick_len};",

        f"layer.x.tickthickness={major_tick_lw};",
        f"layer.x2.tickthickness={major_tick_lw};",
        f"layer.y.tickthickness={major_tick_lw};",
        f"layer.y2.tickthickness={major_tick_lw};",

        # No minor ticks.
        "layer.x.minorTicks=0;",
        "layer.x2.minorTicks=0;",
        "layer.y.minorTicks=0;",
        "layer.y2.minorTicks=0;",

        # Ordinary numeric tick labels: no rotation, no bold, transparent background.
        "layer.x.label.type=1;",
        "layer.y.label.type=1;",
        "layer.x.label.rotate=0;",
        "layer.y.label.rotate=0;",
        "layer.x.label.bold=0;",
        "layer.y.label.bold=0;",
        "layer.x.label.whiteout=0;",
        "layer.y.label.whiteout=0;",

        # Native Origin tick-label font and point size.
        f"layer.x.label.font=font({tick_font});",
        f"layer.y.label.font=font({tick_font});",
        f"layer.x.label.pt={tick_size};",
        f"layer.y.label.pt={tick_size};",
    ]

    for cmd in axis_cmds:
        try:
            result = op.lt_exec(cmd)
            if result is False:
                print(f"[WARN] Origin rejected axis command: {cmd}")
        except Exception as e:
            print(f"[WARN] Axis command failed: {cmd} -> {e}")

    # Read back the most important settings.
    try:
        print(
            "[ORIGIN AXES] "
            f"x.showAxes={op.lt_int('layer.x.showAxes')}, "
            f"y.showAxes={op.lt_int('layer.y.showAxes')}, "
            f"x2.ticks={op.lt_int('layer.x2.ticks')}, "
            f"y2.ticks={op.lt_int('layer.y2.ticks')}, "
            f"tick_font={tick_font}, tick_size={tick_size:g} pt, top/right labels hidden"
        )
    except Exception as e:
        print(f"[WARN] Could not read back axis settings: {e}")

    # --------------------------------------------------------------
    # Built-in legend: keep it, no frame.
    # --------------------------------------------------------------
    legend_lines = []
    for plot_index, s in enumerate(series_list, start=1):
        label = s.legend_label if math.isfinite(s.n_in) else f"Curve {s.curve_id}"
        legend_lines.append(f"\\l({plot_index}) {label}")
    legend_text = "\n".join(legend_lines)

    try:
        lgnd = layer.label("Legend")
        lgnd.text = legend_text
        lgnd.set_int("fsize", int(round(legend_size)))
        lgnd.set_int("showframe", 0)
    except Exception as e:
        print(f"[WARN] Could not fully customize built-in legend: {e}")

    # --------------------------------------------------------------
    # Curves
    # --------------------------------------------------------------
    for i, plot in enumerate(plots):
        color_name = str(color_seq[i % len(color_seq)]).strip() or "black"
        style_idx = int(style_seq[i % len(style_seq)])

        try:
            plot.color = color_name
        except Exception as e:
            print(f"[WARN] Could not set color for plot {i+1}: {e}")

        try:
            plot.set_float("line.width", curve_lw)
        except Exception as e:
            print(f"[WARN] Could not set {curve_lw:g} pt line width for plot {i+1}: {e}")

        try:
            plot.set_cmd(f"-d {style_idx}")
        except Exception as e:
            print(f"[WARN] Could not set line style {style_idx} for plot {i+1}: {e}")



def save_origin_project_and_pdf(op, graph, out_dir: Path, figure_name: str,
                                cfg: Dict[str, Any]) -> Dict[str, Optional[Path]]:
    export_cfg = cfg.get("export", {})
    pdf_cfg = export_cfg.get("pdf", {})

    save_project = cfg_bool(export_cfg.get("save_origin_project"), True)
    export_pdf = cfg_bool(pdf_cfg.get("enabled"), True)
    project_ext = str(export_cfg.get("project_extension") or "opju").lstrip(".")
    overwrite = cfg_bool(pdf_cfg.get("overwrite"), True)

    opju_path = out_dir / f"{figure_name}.{project_ext}"
    pdf_path = out_dir / f"{figure_name}.pdf"

    saved_opju: Optional[Path] = None
    saved_pdf: Optional[Path] = None

    if save_project:
        try:
            op.save(str(opju_path))
            if opju_path.exists():
                saved_opju = opju_path
            else:
                print(f"[WARN] Origin save returned but project file was not found yet: {opju_path}")
                saved_opju = opju_path
        except Exception as e:
            raise RuntimeError(f"Failed to save Origin project '{opju_path}': {e}") from e

    if export_pdf:
        try:
            graph.activate()
        except Exception:
            pass

        # Official expGraph syntax separates output directory ('path')
        # and filename. For overwrite, 'replace' is the documented value.
        overwrite_mode = "replace" if overwrite else "rename"
        pdf_dir = str(out_dir).replace("\\", "\\\\")
        pdf_name = figure_name.replace('"', "'")
        cmd = (
            f'expGraph type:=pdf path:="{pdf_dir}" '
            f'filename:="{pdf_name}" overwrite:={overwrite_mode};'
        )

        try:
            op.lt_exec(cmd)
        except Exception as e:
            print(f"[WARN] PDF export command failed: {e}")

        if pdf_path.exists():
            saved_pdf = pdf_path
        else:
            print(
                "[WARN] PDF was not found after export. "
                "The expGraph options may need one Origin-version-specific adjustment."
            )

    return {"opju": saved_opju, "pdf": saved_pdf}





# ---------------------------------------------------------------------
# Layout-page three-panel composition
# ---------------------------------------------------------------------

LAYOUT_DEFAULTS: Dict[str, Any] = {
    "layout_page_width_mm": 245.0,
    "layout_page_height_mm": 250.0,

    # Deprecated keys kept for config compatibility. The single-graph-page
    # three-layer backend (build_three_panel_graph) uses only:
    #   layout_page_width_mm, layout_page_height_mm,
    #   top_panel_width_mm, top_panel_height_mm, horizontal_gap_mm,
    #   bottom_panel_width_mm, bottom_panel_height_mm, layout_vertical_gap,
    #   panel_labels.
    "source_page_width_mm": 220.0,

    # Top graph row: A + B
    "top_panel_width_mm": 85.0,
    "top_panel_height_mm": 73.0,
    "horizontal_gap_mm": 20.0,

    # Bottom source graph: C
    "bottom_panel_width_mm": 190.0,
    "bottom_panel_height_mm": 55.0,

    # Deprecated margin keys kept for config compatibility (unused by the
    # single-page backend). Outer margins are implicit in the mm geometry.
    "layout_left_margin": 10,
    "layout_right_margin": 10,
    "layout_top_margin": 10,
    "layout_bottom_margin": 10,
    "layout_vertical_gap": 6,

    "panel_labels": {
        "enabled": True,
        "font_family": "Times New Roman",
        "size_pt": 26.0,
        "bold": True,
        "a": "(a)",
        "b": "(b)",
        "c": "(c)",
    },
}


def resolve_layout_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    user = cfg.get("three_panel_layout", {})
    if not isinstance(user, dict):
        user = {}
    layout = deep_resolve(user, LAYOUT_DEFAULTS)

    # Hard rule: outer margins must be symmetric.
    lm = cfg_float(layout.get("layout_left_margin"), 10)
    rm = cfg_float(layout.get("layout_right_margin"), 10)
    tm = cfg_float(layout.get("layout_top_margin"), 10)
    bm = cfg_float(layout.get("layout_bottom_margin"), 10)

    # If a user edits only one side, enforce symmetry rather than silently
    # allowing the whole group to move off center.
    hx = 0.5 * (lm + rm)
    hy = 0.5 * (tm + bm)
    layout["layout_left_margin"] = hx
    layout["layout_right_margin"] = hx
    layout["layout_top_margin"] = hy
    layout["layout_bottom_margin"] = hy

    return layout


def create_origin_worksheet(op, excel_path: Path, sheet_name: str,
                            figure_name: str, panel_name: str):
    series_list = parse_standardized_sheet(excel_path, sheet_name)
    numeric_df = build_numeric_dataframe(series_list)

    book_name = f"{figure_name}_{panel_name}_Data"
    try:
        wb = op.new_book("w", lname=book_name)
        wks = wb[0]
    except Exception:
        wb = op.new_sheet("w", lname=book_name)
        wks = wb

    try:
        wks.from_df(numeric_df, index=False, addindex=False)
    except TypeError:
        wks.from_df(numeric_df)

    designation = "".join(["xy" for _ in series_list])
    wks.cols_axis(
        designation,
        c1=0,
        c2=(2 * len(series_list) - 1),
        repeat=False,
    )

    origin_df = wks.to_df()
    print(
        f"[ORIGIN WORKSHEET {panel_name}] "
        f"rows={len(origin_df)}, cols={origin_df.shape[1]}, designation={designation}"
    )
    if origin_df.empty or origin_df.shape[1] < 2 * len(series_list):
        raise RuntimeError(
            f"Panel {panel_name} worksheet does not contain the expected data."
        )

    return wks, series_list


def add_series_to_layer(layer, wks, series_list: List[SeriesInfo],
                        panel_name: str):
    plots = []
    for i, _ in enumerate(series_list):
        xcol = 2 * i
        ycol = 2 * i + 1
        plot = layer.add_plot(wks, coly=ycol, colx=xcol, type="l")
        if plot is None:
            raise RuntimeError(
                f"Origin returned no plot for panel {panel_name}, curve {i+1}."
            )
        plots.append(plot)

    actual = layer.plot_list()
    print(
        f"[ORIGIN PLOT CHECK {panel_name}] "
        f"expected={len(series_list)}, actual={len(actual)}"
    )
    if len(actual) != len(series_list):
        raise RuntimeError(
            f"Panel {panel_name} has {len(actual)} plots; "
            f"{len(series_list)} expected."
        )

    layer.rescale()
    return plots


def add_panel_label(op, layer_index: int, text: str,
                    obj_name: str, layout_cfg: Dict[str, Any]) -> None:
    lab_cfg = layout_cfg.get("panel_labels", {})
    if not cfg_bool(lab_cfg.get("enabled"), True):
        return

    font = lab_cfg.get("font_family") or "Times New Roman"
    size = int(round(cfg_float(lab_cfg.get("size_pt"), 26.0)))
    bold = cfg_bool(lab_cfg.get("bold"), True)

    op.lt_exec(f"page.active={layer_index};")
    op.lt_exec(f'label -p 2 3 -j 0 -n {obj_name} "{text}";')
    op.lt_exec(f"{obj_name}.font=font({font});")
    op.lt_exec(f"{obj_name}.fsize={size};")
    op.lt_exec(f"{obj_name}.bold={1 if bold else 0};")


def set_page_physical_size(op, width_mm: float, height_mm: float) -> None:
    # page.kar is "Keep Aspect Ratio" (1=on). It must be disabled, otherwise
    # setting page.height rescales page.width proportionally and the intended
    # physical size is silently changed (e.g. 222x100 becomes 290x100).
    op.lt_exec(
        "page.kar=0;"
        f"page.width=page.resx*{width_mm/25.4:.12g};"
        f"page.height=page.resy*{height_mm/25.4:.12g};"
    )


def build_three_panel_graph(
    op,
    wks_a, series_a,
    wks_b, series_b,
    wks_c, series_c,
    cfg: Dict[str, Any],
    layout_cfg: Dict[str, Any],
    figure_name: str,
    arrangement: str = "ab-top",
):
    """
    Build ONE graph page with three layers and deterministic mm geometry.

    All three panels share one right edge by construction (no g2layout /
    Layout page involved -- g2layout scales each source graph independently
    and cannot guarantee edge alignment).

    arrangement="ab-top" (default): A+B pair on row 1, C full-width on row 2:

        A: (27.5,  58, 85, 73)   right = 112.5
        B: (132.5, 58, 85, 73)   right = 217.5
        C: (27.5, 137, 190, 55)  right = 217.5

    arrangement="a-top": A full-width on row 1, B+C pair on row 2 (vertical
    flip of ab-top; same group width/height, same shared right edge):

        A: (27.5,  58, 190, 55)  right = 217.5
        B: (27.5, 119, 85, 73)   right = 112.5
        C: (132.5,119, 85, 73)   right = 217.5

    Page = layout_page_width_mm x layout_page_height_mm (245x250), the whole
    A+B+C group is centered both horizontally and vertically on the page.
    """
    page_w = cfg_float(layout_cfg.get("layout_page_width_mm"), 245.0)
    page_h = cfg_float(layout_cfg.get("layout_page_height_mm"), 250.0)
    top_w = cfg_float(layout_cfg.get("top_panel_width_mm"), 85.0)
    top_h = cfg_float(layout_cfg.get("top_panel_height_mm"), 73.0)
    bot_w = cfg_float(layout_cfg.get("bottom_panel_width_mm"), 190.0)
    bot_h = cfg_float(layout_cfg.get("bottom_panel_height_mm"), 55.0)
    hgap = cfg_float(layout_cfg.get("horizontal_gap_mm"), 20.0)
    vgap = cfg_float(layout_cfg.get("layout_vertical_gap"), 6)

    group_w = 2.0 * top_w + hgap
    group_h = top_h + vgap + bot_h
    left_a = (page_w - group_w) / 2.0
    top_a = (page_h - group_h) / 2.0
    left_b = left_a + top_w + hgap
    top_c = top_a + top_h + vgap

    if arrangement == "a-top":
        # A spans the full width on row 1; B+C pair sits on row 2.
        top_row2 = top_a + bot_h + vgap
        geoms = [
            (1, left_a, top_a, bot_w, bot_h),
            (2, left_a, top_row2, top_w, top_h),
            (3, left_b, top_row2, top_w, top_h),
        ]
        print(
            "[THREE-PANEL ARRANGEMENT] a-top: A full-width on top, "
            f"B/C on bottom (row1 top={top_a:.3f}, row2 top={top_row2:.3f})"
        )
    else:
        # Default ab-top: A+B pair on row 1; C spans the full width on row 2.
        if arrangement != "ab-top":
            print(
                f"[THREE-PANEL ARRANGEMENT] unknown arrangement "
                f"'{arrangement}', falling back to ab-top."
            )
        geoms = [
            (1, left_a, top_a, top_w, top_h),
            (2, left_b, top_a, top_w, top_h),
            (3, left_a, top_c, bot_w, bot_h),
        ]
        print(
            "[THREE-PANEL ARRANGEMENT] ab-top: A/B on top, "
            f"C full-width on bottom (row1 top={top_a:.3f}, row2 top={top_c:.3f})"
        )

    try:
        gp = op.new_graph(template="Line")
    except Exception:
        gp = op.new_graph()

    try:
        gp.set_name(f"{figure_name}_ThreePanel")
    except Exception:
        pass

    layer_a = gp[0]
    layer_b = gp.add_layer(type=0)
    layer_c = gp.add_layer(type=0)

    plots_a = add_series_to_layer(layer_a, wks_a, series_a, "A")
    plots_b = add_series_to_layer(layer_b, wks_b, series_b, "B")
    plots_c = add_series_to_layer(layer_c, wks_c, series_c, "C")

    gp.activate()
    set_page_physical_size(op, page_w, page_h)

    for idx, l, t, w, h in geoms:
        op.lt_exec(f"page.active={idx};")
        op.lt_exec(
            "layer.unit=4;"
            f"layer.left={l:.12g};"
            f"layer.top={t:.12g};"
            f"layer.width={w:.12g};"
            f"layer.height={h:.12g};"
        )
    op.lt_exec("page -afu1;")

    op.lt_exec("page.active=1;")
    apply_origin_style(op, gp, layer_a, plots_a, cfg, series_a)
    create_latex_axis_titles(op, cfg, series_a)
    create_extra_latex_legend(op, cfg, series_a)

    op.lt_exec("page.active=2;")
    apply_origin_style(op, gp, layer_b, plots_b, cfg, series_b)
    create_latex_axis_titles(op, cfg, series_b)
    create_extra_latex_legend(op, cfg, series_b)

    op.lt_exec("page.active=3;")
    apply_origin_style(op, gp, layer_c, plots_c, cfg, series_c)
    create_latex_axis_titles(op, cfg, series_c)
    create_extra_latex_legend(op, cfg, series_c)

    labels = layout_cfg.get("panel_labels", {})
    add_panel_label(op, 1, str(labels.get("a") or "(a)"),
                    "PanelLabelA", layout_cfg)
    add_panel_label(op, 2, str(labels.get("b") or "(b)"),
                    "PanelLabelB", layout_cfg)
    add_panel_label(op, 3, str(labels.get("c") or "(c)"),
                    "PanelLabelC", layout_cfg)

    try:
        actual_w = op.lt_float("page.width/page.resx*25.4")
        actual_h = op.lt_float("page.height/page.resy*25.4")
        print(
            f"[THREE-PANEL GRAPH PAGE] width={actual_w:.3f} mm, "
            f"height={actual_h:.3f} mm"
        )
    except Exception:
        pass

    return gp


def export_active_layout_pdf(op, out_dir: Path, figure_name: str) -> Optional[Path]:
    pdf_path = out_dir / f"{figure_name}.pdf"
    # expGraph also exports Layout pages when the Layout is active.
    out_path = str(out_dir).replace("\\", "\\\\")
    fname = figure_name.replace('"', '\\"')

    cmd = (
        f'expGraph type:=pdf filename:="{fname}" '
        f'path:="{out_path}" overwrite:=replace;'
    )
    print("[LAYOUT PDF EXPORT]")
    print(cmd)
    op.lt_exec(cmd)

    return pdf_path if pdf_path.exists() else None


def plot_three_panel_layout(
    excel_a: Path, sheet_a: str,
    excel_b: Path, sheet_b: str,
    excel_c: Path, sheet_c: str,
    cfg: Dict[str, Any],
    out_dir: Path,
    figure_name: str,
    show_origin: bool = True,
    arrangement: str = "ab-top",
) -> Dict[str, Optional[Path]]:

    try:
        import originpro as op
    except ImportError as e:
        raise RuntimeError(
            "originpro is not installed in this Python environment."
        ) from e

    try:
        op.set_show(show_origin)
    except Exception:
        pass

    layout_cfg = resolve_layout_config(cfg)

    wks_a, series_a = create_origin_worksheet(
        op, excel_a, sheet_a, figure_name, "A"
    )
    wks_b, series_b = create_origin_worksheet(
        op, excel_b, sheet_b, figure_name, "B"
    )
    wks_c, series_c = create_origin_worksheet(
        op, excel_c, sheet_c, figure_name, "C"
    )

    graph = build_three_panel_graph(
        op, wks_a, series_a, wks_b, series_b, wks_c, series_c,
        cfg, layout_cfg, figure_name, arrangement=arrangement
    )

    # Save the full editable Origin project.
    opju_path = out_dir / f"{figure_name}.opju"
    op.save(str(opju_path))

    pdf_path = export_active_layout_pdf(op, out_dir, figure_name)

    graph_name = "graph"
    try:
        gname = graph.name
        if callable(gname):
            gname = gname()
        graph_name = str(gname)
    except Exception:
        pass
    print(f"[LAYOUT RESULT] graph={graph_name}")
    print(f"[LAYOUT RESULT] OPJU={opju_path}")
    print(f"[LAYOUT RESULT] PDF={pdf_path or '[export not verified]'}")

    return {
        "opju": opju_path if opju_path.exists() else None,
        "pdf": pdf_path,
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a three-panel figure on ONE graph page with three layers "
            "(deterministic mm geometry). Arrangement 'ab-top' (default) puts "
            "A/B on the top row and full-width C on the bottom; 'a-top' puts "
            "full-width A on the top and B/C on the bottom row."
        )
    )

    parser.add_argument("--excel-a", required=True)
    parser.add_argument("--sheet-a", required=True)

    parser.add_argument("--excel-b", default=None)
    parser.add_argument("--sheet-b", default=None)

    parser.add_argument("--excel-c", default=None)
    parser.add_argument("--sheet-c", default=None)

    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--figure-name", default="Fig1abc")
    parser.add_argument("--hide-origin", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--arrangement",
        choices=["ab-top", "a-top"],
        default="ab-top",
        help="ab-top: A/B top row, C full-width bottom (default); "
             "a-top: A full-width top, B/C bottom row.",
    )

    args = parser.parse_args()

    excel_a = Path(args.excel_a).expanduser().resolve()
    sheet_a = args.sheet_a

    excel_b = (
        Path(args.excel_b).expanduser().resolve()
        if args.excel_b else excel_a
    )
    sheet_b = args.sheet_b or sheet_a

    excel_c = (
        Path(args.excel_c).expanduser().resolve()
        if args.excel_c else excel_a
    )
    sheet_c = args.sheet_c or sheet_a

    config_path = Path(args.config).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve()
    ensure_dir(out_dir)

    cfg = load_yaml(config_path)
    layout_cfg = resolve_layout_config(cfg)

    print(
        "[THREE-PANEL LAYOUT CONFIG] "
        f"arrangement={args.arrangement}; "
        f"page={layout_cfg['layout_page_width_mm']}x"
        f"{layout_cfg['layout_page_height_mm']} mm"
    )

    # Parse all three sources before Origin is called.
    series_a = parse_standardized_sheet(excel_a, sheet_a)
    series_b = parse_standardized_sheet(excel_b, sheet_b)
    series_c = parse_standardized_sheet(excel_c, sheet_c)

    for name, series in [("A", series_a), ("B", series_b), ("C", series_c)]:
        print("=" * 72)
        print(f"Panel {name}")
        for s in series:
            print(
                f"Curve {s.curve_id}: ({s.x_short}, {s.y_short}), "
                f"N_in={s.n_in:g}, points={len(s.x)}"
            )
    print("=" * 72)

    if args.dry_run:
        print(
            "[DRY-RUN] All three panels parsed successfully. "
            "Origin/Layout was not called."
        )
        return

    outputs = plot_three_panel_layout(
        excel_a, sheet_a,
        excel_b, sheet_b,
        excel_c, sheet_c,
        cfg, out_dir, args.figure_name,
        show_origin=(not args.hide_origin),
        arrangement=args.arrangement,
    )

    print("Three-panel Layout plotting finished.")
    print(f"OPJU : {outputs.get('opju') or '[not saved / not found]'}")
    print(f"PDF  : {outputs.get('pdf') or '[not exported / not found]'}")


if __name__ == "__main__":
    main()
