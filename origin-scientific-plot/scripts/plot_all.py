#!/usr/bin/env python3
"""Prepare and plot multiple Origin figures from plot-spec JSON files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


SCRIPTS = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS.parent
CONFIG = SKILL_ROOT / "config" / "style.yaml"

BACKENDS = {
    "single": "plot_origin.py",
    "two_panel": "plot_origin_two_panel.py",
    "three_panel": "plot_origin_three_panel.py",
}

PANEL_SHEET_NAMES = {"a": "FigA", "b": "FigB", "c": "FigC"}


def load_spec(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"Could not read spec {path}: {e}")
    if not isinstance(data, dict):
        raise SystemExit(f"Spec must be a JSON object: {path}")
    return data


def run(cmd: List[str]) -> None:
    print("$ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True)


def resolve_spec_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base_dir / path).resolve()


def verify_outputs(figure_name: str, out_dir: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[VERIFY] {figure_name}: dry-run only, no outputs expected")
        return
    opju = out_dir / f"{figure_name}.opju"
    if not opju.exists():
        print(f"[VERIFY] MISSING OPJU: {opju}")
        raise SystemExit(f"Output verification failed for {figure_name}")
    print(f"[VERIFY] OPJU: {opju} ({opju.stat().st_size} bytes)")
    pdf = out_dir / f"{figure_name}.pdf"
    if pdf.exists():
        print(f"[VERIFY] PDF: {pdf} ({pdf.stat().st_size} bytes)")


def backend_command(spec: Dict[str, Any], spec_dir: Path, out_dir: Path,
                    dry_run: bool, hide_origin: bool) -> List[str]:
    layout = str(spec.get("layout", "")).strip().lower()
    figure_name = str(spec.get("figure_name", "")).strip()
    if layout not in BACKENDS:
        raise SystemExit(f"Unsupported layout '{layout}' in {spec_dir}")

    generated = resolve_spec_path(
        str(spec.get("output_excel") or f"../generated/{figure_name}_origin.xlsx"),
        spec_dir,
    )
    cmd: List[str] = [
        sys.executable,
        SCRIPTS / BACKENDS[layout],
        "--config",
        CONFIG,
        "--output-dir",
        out_dir,
        "--figure-name",
        figure_name,
    ]
    if layout == "single":
        cmd += ["--excel", generated, "--sheet", f"{figure_name}_Standard"]
    else:
        panel_keys = list(spec.get("panels", {}).keys())
        for key in panel_keys:
            sheet = PANEL_SHEET_NAMES.get(str(key).lower(), f"Fig{key}")
            cmd += [f"--excel-{key}", generated, f"--sheet-{key}", sheet]
    if hide_origin:
        cmd += ["--hide-origin"]
    if dry_run:
        cmd += ["--dry-run"]
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare standardized workbooks and plot multiple Origin figures."
    )
    parser.add_argument("--specs", nargs="+", required=True, help="Plot-spec JSON files.")
    parser.add_argument("--out-dir", default=None, help="Output dir for OPJU (and PDF when requested); defaults to <spec>/excel.")
    parser.add_argument("--hide-origin", action="store_true", help="Keep Origin hidden.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and parse only; do not call Origin.")
    args = parser.parse_args()

    for spec_value in args.specs:
        spec_path = Path(spec_value).resolve()
        spec = load_spec(spec_path)
        spec_dir = spec_path.parent
        out_dir = Path(args.out_dir).resolve() if args.out_dir else (spec_dir / "excel").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        run([sys.executable, SCRIPTS / "prepare_origin_data.py", "--spec", spec_path])
        run(backend_command(spec, spec_dir, out_dir, args.dry_run, args.hide_origin))
        verify_outputs(str(spec.get("figure_name", "")).strip(), out_dir, args.dry_run)


if __name__ == "__main__":
    main()
