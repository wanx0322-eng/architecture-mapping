#!/usr/bin/env python3
"""Render deterministic Chinese competition-board text as editable SVG."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="layout JSON")
    parser.add_argument("--output", required=True, help="output SVG")
    args = parser.parse_args()
    spec = json.loads(Path(args.input).read_text(encoding="utf-8"))
    width = int(spec.get("width", 1600))
    height = int(spec.get("height", 1200))
    background = spec.get("background", "#FFFFFF")
    font = spec.get("font_family", "Microsoft YaHei, Noto Sans CJK SC, sans-serif")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="{esc(background)}"/>',
        f'<g font-family="{esc(font)}">',
    ]
    for item in spec.get("texts", []):
        x, y = int(item["x"]), int(item["y"])
        size = int(item.get("font_size", 28))
        color = item.get("color", "#222222")
        weight = item.get("font_weight", 400)
        anchor = item.get("anchor", "start")
        lines = str(item.get("text", "")).splitlines() or [""]
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{esc(color)}" text-anchor="{esc(anchor)}">')
        for index, line in enumerate(lines):
            dy = 0 if index == 0 else round(size * 1.4)
            parts.append(f'<tspan x="{x}" dy="{dy}">{esc(line)}</tspan>')
        parts.append('</text>')
    for line in spec.get("leader_lines", []):
        parts.append(
            f'<line x1="{int(line["x1"])}" y1="{int(line["y1"])}" x2="{int(line["x2"])}" y2="{int(line["y2"])}" '
            f'stroke="{esc(line.get("color", "#777777"))}" stroke-width="{float(line.get("width", 1.5))}"/>'
        )
    parts.extend(["</g>", "</svg>"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()

