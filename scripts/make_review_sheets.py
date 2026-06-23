#!/usr/bin/env python3
"""Render queued thumbnails into numbered contact sheets for human review."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def main() -> None:
    queue = read_jsonl(ROOT / "dataset/raw/core_queue.jsonl")
    out_dir = ROOT / "dataset/reports/review-sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=20)
    cols, rows = 4, 4
    cell_w, cell_h = 320, 400
    index_rows = []

    for sheet_no, start in enumerate(range(0, len(queue), cols * rows), 1):
        canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
        draw = ImageDraw.Draw(canvas)
        for local_no, item in enumerate(queue[start:start + cols * rows]):
            absolute_no = start + local_no + 1
            x = (local_no % cols) * cell_w
            y = (local_no // cols) * cell_h
            rid = item["record_id"]
            source = item.get("source_record", {})
            image = Image.open(item["thumbnail_path"]).convert("RGB")
            image.thumbnail((cell_w - 20, cell_h - 75))
            tile = Image.new("RGB", (cell_w - 20, cell_h - 75), "#f2f2f2")
            tile.paste(image, ((tile.width - image.width) // 2, (tile.height - image.height) // 2))
            canvas.paste(tile, (x + 10, y + 45))
            draw.rectangle((x + 5, y + 5, x + cell_w - 5, y + cell_h - 5), outline="#999999", width=2)
            draw.text((x + 12, y + 12), f"{absolute_no:03d}  {rid}", fill="black", font=font)
            index_rows.append({
                "review_no": absolute_no,
                "record_id": rid,
                "thumbnail_path": item["thumbnail_path"],
                "pin_url": source.get("pin_url"),
                "search_url": source.get("search_url"),
                "title": source.get("title"),
            })
        canvas.save(out_dir / f"sheet-{sheet_no:02d}.jpg", quality=92)

    (out_dir / "index.json").write_text(
        json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"queued": len(queue), "sheets": (len(queue) + 15) // 16, "out_dir": str(out_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
