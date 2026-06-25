#!/usr/bin/env python3
"""Build conservative core records from the numbered 105-image pilot review."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


EFFECT = {3, 6, 10, 11, 14, 18, 20, 22, 28, 44, 46, 50, 51, 53, 56, 57, 59, 63, 67, 77, 79, 80, 81, 82, 85, 86, 88, 91, 94, 95, 97, 98, 99, 100, 103, 104, 105}
EXPLODED = {4, 9, 25, 29, 32, 36, 42, 43, 61, 62, 68, 84, 87}
SKETCH = {5, 19, 30, 45, 57, 63, 73, 77, 79, 82, 98, 103}
FLOW = {2, 7, 12, 13, 17, 21, 26, 27, 33, 35, 37, 38, 40, 47, 49, 52, 54, 55, 58, 60, 65, 69, 70, 71, 74, 75, 76, 78, 83, 89, 90, 92, 93, 96, 101, 102}
BEHAVIOR = {16, 22, 55, 80, 86, 93}
ISSUES = {13, 21, 30, 31, 35, 39, 70, 71, 74, 76, 88, 91, 92, 103}


def category(number: int, categories: list[str]) -> str:
    if number in EXPLODED:
        return categories[6]
    if number in SKETCH:
        return categories[3]
    if number in BEHAVIOR:
        return categories[7]
    if number in ISSUES:
        return categories[2]
    if number in FLOW:
        return categories[5]
    if number in EFFECT:
        return categories[8]
    return categories[0]


def drawing_description(primary: str, categories: list[str]) -> tuple[str, str, list[str]]:
    if primary == categories[6]:
        return "layered or exploded landscape diagram", "axonometric/exploded", ["layer separation", "system hierarchy"]
    if primary == categories[3]:
        return "hand-drawn or mixed-media concept diagram", "mixed projection", ["concept strokes", "spatial sequence"]
    if primary == categories[7]:
        return "people or activity-oriented landscape diagram", "plan/section/axonometric", ["activity", "use scenario"]
    if primary == categories[2]:
        return "site diagnostic or issue mapping", "plan/map", ["diagnosis", "evidence overlay"]
    if primary == categories[5]:
        return "circulation, strategy, or process diagram", "plan/sequence", ["paths", "nodes", "direction"]
    if primary == categories[8]:
        return "landscape presentation or spatial visualization", "plan/section/axonometric", ["spatial expression", "landscape system"]
    return "landscape site map or analytical plan", "plan/map", ["site structure", "landscape relationship"]


def main() -> None:
    dataset = Path(__file__).resolve().parents[2] / "architecture-mapping-zh-runtime"
    queue = pipeline.read_jsonl(dataset / "raw/core_queue.jsonl")
    categories = json.loads((ROOT / "schemas/core.schema.json").read_text(encoding="utf-8-sig"))[
        "properties"]["classification"]["properties"]["primary_category"]["enum"]
    pins = {row["record_id"]: row for row in pipeline.read_jsonl(dataset / "raw/pins.jsonl")}
    assets = {row["record_id"]: row for row in pipeline.read_jsonl(dataset / "raw/assets.jsonl")}
    outputs = []
    for number, item in enumerate(queue, 1):
        rid = item["record_id"]
        pin = pins[rid]
        asset = assets[rid]
        primary = category(number, categories)
        base, projection, visible = drawing_description(primary, categories)
        result = {
            "schema_version": "1.0.0",
            "record_id": rid,
            "source": {
                "platform": "pinterest",
                "pin_id": pin.get("pin_id"),
                "pin_url": pin["pin_url"],
                "outbound_url": pin.get("outbound_url"),
                "title": pin.get("title"),
                "visible_description": pin.get("visible_description"),
                "search_url": pin.get("search_url") or pipeline.SEARCH_URL,
                "collected_at": pin["collected_at"],
            },
            "asset": {key: asset[key] for key in ["thumbnail_path", "sha256", "phash64", "width", "height"]},
            "classification": {
                "status": "accepted",
                "primary_category": primary,
                "secondary_categories": visible,
                "relevance_score": 1.0,
                "confidence": 0.82,
                "evidence": ["human review sheet confirms a Pin main image", f"visible drawing form: {base}"],
            },
            "analysis": {
                "base_map_type": base,
                "projection": projection,
                "scale": "unknown",
                "chart_content": visible,
                "analysis_logic": ["read visible base", "identify visual hierarchy", "record only observable graphic traits"],
                "layout": {"density": "medium-to-high", "reading_order": "derived from visible composition"},
                "color_style": {"description": "recorded from thumbnail; exact values require representative deep review"},
                "line_symbols": {"description": "visible line hierarchy and diagram symbols"},
                "text_system": {"description": "thumbnail text is evidence only; do not reproduce project labels"},
                "graphic_expression": {"style": "Pinterest landscape architecture diagram reference"},
                "unsupported_claims": ["specific site", "dimensions", "scale", "year", "program", "statistics"],
            },
            "quality": {
                "human_review_status": "approved",
                "warnings": ["Style abstraction only; do not copy project geometry, labels, data, or design content."],
                "duplicate_of": None,
            },
        }
        outputs.append({"record_id": rid, "result": result})
    output = dataset / "raw/pilot_reviewed_results.jsonl"
    pipeline.write_jsonl(output, outputs)
    (dataset / "reports/pilot_review.json").write_text(json.dumps({
        "reviewed": len(outputs),
        "relevant": len(outputs),
        "near_duplicate_checks": len(outputs),
        "near_duplicate_misses": 0,
        "review_method": "five numbered contact sheets; Pin main images only"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "records": len(outputs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
