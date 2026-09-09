"""Prepare standardized Origin workbook from a raw column-oriented Excel file.

Raw layout expected (MATLAB-style, baseline section 18):
    Row 1 (header):  x | A=1 | A=2 | A=3 ...
    Data rows:       x | y1  | y2  | y3  ...

Output: standardized workbook (baseline section 17) with the 8-row metadata
header consumed by the stable backends.

Usage:
    python prepare_origin_data.py --input raw.xlsx --sheet Data \
        --x-column 1 --y-columns 2,3,4 --n-in 1,2,3 \
        [--variable x,y --condition "note"] --output std.xlsx

Rules:
    --x-column / --y-columns are 1-based column numbers.
    --n-in values drive the legend labels; repeat per y column.
    --variable (optional) overrides the default variable names "x","y",...
    Non-numeric cells in data rows are coerced to NaN.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--sheet", default="Data")
    p.add_argument("--x-column", type=int, required=True)
    p.add_argument("--y-columns", required=True, help="comma-separated 1-based column numbers")
    p.add_argument("--n-in", required=True, help="comma-separated legend parameter values")
    p.add_argument("--variable", default=None, help="comma-separated variable names (default: x,y,...)")
    p.add_argument("--condition", default="")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    src = Path(args.input).resolve()
    out = Path(args.output).resolve()
    if not src.exists():
        raise FileNotFoundError(f"input not found: {src}")

    y_cols = [int(v) for v in args.y_columns.split(",")]
    n_in = [float(v) for v in args.n_in.split(",")]
    if len(n_in) != len(y_cols):
        raise ValueError("--n-in count must equal --y-columns count")

    df = pd.read_excel(src, sheet_name=args.sheet, header=0)
    x = pd.to_numeric(df.iloc[:, args.x_column - 1], errors="coerce").to_numpy()
    if x.size == 0 or np.all(np.isnan(x)):
        raise ValueError("x column contains no valid numeric data")

    vars_ = (args.variable.split(",") if args.variable else
             ["x"] + [f"y{i+1}" for i in range(len(y_cols))])
    if len(vars_) != len(y_cols) + 1:
        raise ValueError("--variable count must equal x + y columns")

    n = len(y_cols)
    wb = Workbook()
    ws = wb.active
    ws.title = "Standard"
    # Row 1 short names
    row1 = []
    for i in range(n):
        row1 += [f"x_{i+1}", f"y_{i+1}"]
    ws.append(row1)
    # Row 2 designations
    ws.append(["X", "Y"] * n)
    # Row 3 curve ids
    ws.append([i + 1 for i in range(n) for _ in (0, 1)])
    # Row 4 N_in
    ws.append([v for v in n_in for _ in (0, 1)])
    # Row 5 variable names
    row5 = [vars_[0]]
    for i in range(n):
        row5 += [vars_[0], vars_[i + 1]]
    ws.append(row5)
    # Row 6 condition
    ws.append([args.condition] + [None] * (2 * n - 1))
    # Row 7 blank separator
    ws.append([None] * (2 * n))
    # Row 8+ data
    for k in range(len(x)):
        row = []
        for i, col in enumerate(y_cols):
            row.append(x[k])
            row.append(pd.to_numeric(df.iloc[:, col - 1], errors="coerce").to_numpy()[k])
        ws.append(row)

    wb.save(out)
    print(f"[PREPARED] {out}  curves={n}  rows={len(x)}  n_in={n_in}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
