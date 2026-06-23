#!/usr/bin/env python3
"""Create a deterministic visual QA sheet for imported local archives."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def spread(rows: list[dict], count: int) -> list[dict]:
    if len(rows) <= count:
        return rows
    return [rows[round(index * (len(rows) - 1) / (count - 1))] for index in range(count)]


def main() -> None:
    rows = read_jsonl(DATASET / "raw/local_deduped.jsonl")
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        source = row["source"]
        groups[(source["archive_name"], source["source_type"])].append(row)
    samples = []
    samples.extend(spread(groups[("ASLA_2004_2024", "image")], 6))
    samples.extend(spread(groups[("IFLA_2016_2024", "image")], 3))
    samples.extend(spread(groups[("IFLA_2016_2024", "pdf_page")], 6))
    samples.extend(spread(groups[("S462_ARCH_COMPETITION", "image")], 5))

    cols, rows_count = 5, 4
    cell_w, cell_h = 360, 420
    canvas = Image.new("RGB", (cols * cell_w, rows_count * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    index = []
    for number, row in enumerate(samples, 1):
        col = (number - 1) % cols
        line = (number - 1) // cols
        x, y = col * cell_w, line * cell_h
        source = row["source"]
        image = Image.open(row["asset"]["thumbnail_path"]).convert("RGB")
        image.thumbnail((cell_w - 20, cell_h - 75), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (cell_w - 20, cell_h - 75), "#f3f3f3")
        tile.paste(image, ((tile.width - image.width) // 2, (tile.height - image.height) // 2))
        canvas.paste(tile, (x + 10, y + 55))
        label = f"{number:02d} {source['archive_name']} {source['source_type']}"
        if source.get("pdf_page"):
            label += f" p{source['pdf_page']}/{source['total_pages']}"
        draw.text((x + 10, y + 10), label, fill="black", font=font)
        draw.text((x + 10, y + 32), row["record_id"], fill="#555555", font=font)
        draw.rectangle((x + 4, y + 4, x + cell_w - 4, y + cell_h - 4), outline="#999999", width=2)
        index.append({
            "sample_no": number, "record_id": row["record_id"],
            "archive_name": source["archive_name"], "source_type": source["source_type"],
            "pdf_page": source.get("pdf_page"), "source_path": source["source_path"],
            "thumbnail_path": row["asset"]["thumbnail_path"],
        })
    output = DATASET / "reports/local-archive-sample.jpg"
    canvas.save(output, quality=92)
    (DATASET / "reports/local-archive-sample.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
