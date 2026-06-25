#!/usr/bin/env python3
"""Pinterest dataset and opt-in style extensions for architecture-mapping-zh 0.3."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline_base", ROOT / "scripts/pipeline.py")
base = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(base)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ingest_browser_batch(root: Path, input_path: Path) -> dict[str, int]:
    base.ensure_dirs(root)
    payload = read_json(input_path, {})
    batch = payload if isinstance(payload, list) else payload.get("pins", [])
    batch_query = None if isinstance(payload, list) else payload.get("query")
    target = root / "raw/captured.jsonl"
    merged = {row["record_id"]: row for row in base.read_jsonl(target) if row.get("record_id")}
    before = len(merged)
    for raw in batch:
        if not isinstance(raw, dict):
            continue
        pin_url = base.normalize_url(raw.get("pin_url"))
        image_url = raw.get("image_url")
        pin_id = raw.get("pin_id")
        if not pin_url or not pin_id or not image_url or "i.pinimg.com/" not in image_url:
            continue
        rid = base.record_id(raw)
        current = merged.get(rid, {})
        query = raw.get("query") or batch_query
        queries = set(current.get("queries", []))
        search_urls = set(current.get("search_urls", []))
        if query:
            queries.add(str(query))
        if raw.get("search_url"):
            search_urls.add(raw["search_url"])
        merged[rid] = {
            "record_id": rid,
            "pin_id": str(pin_id),
            "pin_url": pin_url,
            "image_url": image_url,
            "title": raw.get("title") or current.get("title"),
            "visible_description": raw.get("visible_description") or current.get("visible_description"),
            "outbound_url": base.normalize_url(raw.get("outbound_url")) or current.get("outbound_url"),
            "search_url": raw.get("search_url") or current.get("search_url") or base.SEARCH_URL,
            "query": query or current.get("query"),
            "queries": sorted(queries),
            "search_urls": sorted(search_urls),
            "collected_at": raw.get("collected_at") or current.get("collected_at") or base.now_iso(),
        }
    rows = sorted(merged.values(), key=lambda item: item["record_id"])
    base.write_jsonl(target, rows)
    base.write_jsonl(root / "raw/pins.jsonl", rows)
    result = {"captured": len(rows), "added": len(rows) - before, "batch_size": len(batch)}
    base.update_status(root, state="browser_batch_ingested", raw_count=len(rows), last_batch=result)
    return result


def collection_status(root: Path) -> dict[str, int]:
    core = [read_json(path, {}) for path in sorted((root / "records/core").glob("*.json"))]
    result = {
        "captured": max(len(base.read_jsonl(root / "raw/captured.jsonl")), len(base.read_jsonl(root / "raw/pins.jsonl"))),
        "downloaded": len(base.read_jsonl(root / "raw/assets.jsonl")),
        "unique": len(base.read_jsonl(root / "raw/deduped.jsonl")),
        "accepted": sum(row.get("classification", {}).get("status") == "accepted" for row in core),
        "rejected": sum(row.get("classification", {}).get("status") == "rejected" for row in core),
        "download_failures": len(base.read_jsonl(root / "raw/download_failures.jsonl")),
        "target_valid": 2000,
        "pilot_target": 100,
    }
    base.update_status(root, **result)
    return result


def quality_gate(root: Path) -> dict[str, Any]:
    review = read_json(root / "reports/pilot_review.json", {}) or {}
    validation = read_json(root / "reports/validation.json", {}) or {}
    status = collection_status(root)
    rate = lambda n, d: float(n) / float(d) if d else 0.0
    reviewed = int(review.get("reviewed", 0))
    relevant = int(review.get("relevant", 0))
    duplicate_checks = int(review.get("near_duplicate_checks", 0))
    duplicate_misses = int(review.get("near_duplicate_misses", 0))
    checked = int(validation.get("checked", 0))
    failed = int(validation.get("failed", 0))
    checks = {
        "pilot_review_count": {"value": reviewed, "threshold": 100, "passed": reviewed >= 100},
        "relevance_rate": {"value": rate(relevant, reviewed), "threshold": 0.90, "passed": rate(relevant, reviewed) >= 0.90},
        "schema_pass_rate": {"value": rate(checked - failed, checked), "threshold": 1.0, "passed": checked >= 100 and failed == 0},
        "near_duplicate_miss_rate": {"value": rate(duplicate_misses, duplicate_checks), "threshold": 0.05, "passed": duplicate_checks >= 100 and rate(duplicate_misses, duplicate_checks) <= 0.05},
        "download_success_rate": {"value": rate(status["downloaded"], status["captured"]), "threshold": 0.90, "passed": status["captured"] >= 100 and rate(status["downloaded"], status["captured"]) >= 0.90},
    }
    result = {"passed": all(item["passed"] for item in checks.values()), "checks": checks, "evaluated_at": base.now_iso()}
    base.write_json(root / "reports/quality_gate.json", result)
    base.update_status(root, state="pilot_passed" if result["passed"] else "pilot_blocked", quality_gate_passed=result["passed"])
    return result


def choose_style_cluster(row: dict[str, Any], profiles: dict[str, Any]) -> str:
    """Choose a stable style prior from observable task terms, never from sample popularity."""
    text = json.dumps(row, ensure_ascii=False).lower()
    rules = [
        ("ecological_layered_wash", ["ecology", "ecological", "hydrology", "water", "green infrastructure"]),
        ("layered_landscape_axonometric", ["axonometric", "isometric", "exploded", "layers"]),
        ("diagnostic_heat_overlay", ["heat", "risk", "diagnostic", "intensity", "opportunity"]),
        ("desaturated_paper_collage", ["collage", "history", "narrative", "atmosphere"]),
        ("hand_drawn_mixed_media", ["hand drawn", "sketch", "concept evolution", "marker"]),
        ("dark_high_contrast_narrative", ["night", "dark", "infrastructure narrative"]),
        ("precision_vector_analysis", ["technical", "constraint", "land use", "circulation"]),
        ("minimal_grey_competition", ["site analysis", "figure-ground", "competition board"]),
    ]
    scored = []
    for cluster, keywords in rules:
        if cluster not in profiles:
            continue
        score = sum(keyword in text for keyword in keywords)
        scored.append((score, cluster))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return "minimal_grey_competition"


def resolve_style(
    style_source: str | None,
    style_cluster: str | None,
    style_strength: float,
    row: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not style_source:
        return None
    if style_source != "pinterest_dataset":
        raise ValueError("style_source must be pinterest_dataset")
    profiles = read_json(ROOT / "assets/pinterest_style_profiles.json", {"clusters": {}})["clusters"]
    selection_mode = "auto" if style_cluster in {None, "auto"} else "explicit"
    if selection_mode == "auto":
        style_cluster = choose_style_cluster(row or {}, profiles)
    profile = profiles.get(style_cluster)
    if not profile:
        raise ValueError(f"unknown Pinterest style cluster: {style_cluster}")
    if not 0 <= style_strength <= 1:
        raise ValueError("style_strength must be between 0 and 1")
    band = "low" if style_strength < 0.4 else "medium" if style_strength < 0.8 else "high"
    return {
        "source": style_source,
        "cluster": style_cluster,
        "selection_mode": selection_mode,
        "strength": style_strength,
        "strength_band": band,
        **profile,
        "source_policy": "abstract visual traits only; never copy project geometry, labels, data, or design content"
    }


def prompt_pack(row: dict[str, Any], style_source: str | None = None, style_cluster: str | None = None, style_strength: float = 0.7) -> dict[str, Any]:
    result = base.prompt_pack(row)
    style = resolve_style(style_source, style_cluster, style_strength, row)
    if not style:
        return result
    universal = result["universal_json_prompt"]
    universal["style_reference"] = style
    universal["negative_constraints"].extend(style["negative_terms"])
    phrase = ", " + ", ".join(style["positive_terms"])
    result["gpt_image"]["prompt"] += phrase
    result["midjourney"]["prompt"] += phrase
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest-browser-batch")
    ingest.add_argument("--root", required=True)
    ingest.add_argument("--input", required=True)
    for name in ["collection-status", "quality-gate"]:
        item = sub.add_parser(name)
        item.add_argument("--root", required=True)
    compile_item = sub.add_parser("compile-prompts")
    compile_item.add_argument("--root", required=True)
    compile_item.add_argument("--style-source", choices=["pinterest_dataset"])
    compile_item.add_argument("--style-cluster")
    compile_item.add_argument("--style-strength", type=float, default=0.7)
    args = parser.parse_args()
    root = Path(args.root)
    if args.command == "ingest-browser-batch":
        result = ingest_browser_batch(root, Path(args.input))
    elif args.command == "collection-status":
        result = collection_status(root)
    elif args.command == "quality-gate":
        result = quality_gate(root)
    else:
        count = 0
        for path in sorted((root / "records/core").glob("*.json")):
            row = read_json(path)
            if row["classification"]["status"] == "rejected":
                continue
            result = prompt_pack(row, args.style_source, args.style_cluster, args.style_strength)
            base.write_json(root / "prompts" / f"{row['record_id']}.json", result)
            count += 1
        result = {"compiled": count}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
