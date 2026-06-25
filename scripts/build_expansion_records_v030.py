#!/usr/bin/env python3
"""Build conservative schema-valid records for the post-dedup Pinterest expansion."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


def search_text(row: dict) -> str:
    query = parse_qs(urlsplit(row.get("search_url", "")).query).get("q", [""])[0]
    return " ".join([query, row.get("title") or "", row.get("visible_description") or ""]).lower()


def choose_category(text: str, categories: list[str]) -> tuple[str, list[str], str]:
    if any(word in text for word in ["axonometric", "exploded", "system axonometric", "layered"]):
        return categories[6], ["layered systems", "axonometric"], "layered or exploded landscape systems"
    if any(word in text for word in ["hand drawn", "watercolor", "collage", "concept", "sketch"]):
        return categories[3], ["concept expression", "mixed media"], "hand-drawn or mixed-media concept diagram"
    if any(word in text for word in ["behavior", "activity", "user analysis", "experiential", "sensory"]):
        return categories[7], ["people and activity", "use scenario"], "behavior or experience mapping"
    if any(word in text for word in ["constraints", "opportunities", "noise", "climate", "diagnostic", "risk"]):
        return categories[2], ["site diagnosis", "evidence overlay"], "site diagnostic diagram"
    if any(word in text for word in ["circulation", "pedestrian", "mobility", "network", "strategy", "process", "phasing"]):
        return categories[5], ["paths and nodes", "strategy sequence"], "circulation or strategy diagram"
    if any(word in text for word in ["history", "heritage", "cultural landscape", "memorial"]):
        return categories[1], ["historical or cultural layer"], "historical or cultural landscape diagram"
    if any(word in text for word in ["presentation", "portfolio", "competition", "visualisation", "render"]):
        return categories[8], ["presentation board", "spatial visualization"], "landscape presentation board"
    return categories[0], ["site structure", "landscape relationship"], "landscape site map or analytical plan"


def main() -> None:
    dataset = Path(__file__).resolve().parents[2] / "architecture-mapping-zh-runtime"
    deduped = pipeline.read_jsonl(dataset / "raw/deduped.jsonl")
    existing = {path.stem for path in (dataset / "records/core").glob("*.json")}
    categories = json.loads((ROOT / "schemas/core.schema.json").read_text(encoding="utf-8-sig"))[
        "properties"]["classification"]["properties"]["primary_category"]["enum"]
    outputs = []
    for item in deduped:
        rid = item["record_id"]
        if rid in existing:
            continue
        text = search_text(item)
        primary, secondary, base = choose_category(text, categories)
        pin = item
        asset = item["asset"]
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
                "status": "needs_review",
                "primary_category": primary,
                "secondary_categories": secondary,
                "relevance_score": 0.85,
                "confidence": 0.68,
                "evidence": ["source query is landscape architecture specific", f"visible metadata suggests: {base}"],
            },
            "analysis": {
                "base_map_type": base,
                "projection": "unknown",
                "scale": "unknown",
                "chart_content": secondary,
                "analysis_logic": ["use visible thumbnail only", "classify broad drawing form", "defer project facts to human review"],
                "layout": {"description": "pending representative review"},
                "color_style": {"description": "derived later from image features"},
                "line_symbols": {"description": "pending representative review"},
                "text_system": {"description": "do not reproduce reference labels"},
                "graphic_expression": {"style": "Pinterest landscape architecture reference"},
                "unsupported_claims": ["specific site", "dimensions", "scale", "year", "program", "statistics"],
            },
            "quality": {
                "human_review_status": "pending",
                "warnings": ["Automatic broad classification; representative and random-sample review required."],
                "duplicate_of": None,
            },
        }
        outputs.append({"record_id": rid, "result": result})
    output = dataset / "raw/expansion_results_v030.jsonl"
    pipeline.write_jsonl(output, outputs)
    print(json.dumps({"output": str(output), "records": len(outputs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
