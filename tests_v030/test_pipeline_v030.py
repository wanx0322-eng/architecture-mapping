from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline_v030", ROOT / "scripts/pipeline_v030.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def pin(pin_id: str, query: str) -> dict:
    return {
        "pin_id": pin_id,
        "pin_url": f"https://jp.pinterest.com/pin/{pin_id}/",
        "image_url": f"https://i.pinimg.com/474x/{pin_id}.jpg",
        "query": query,
        "search_url": f"https://jp.pinterest.com/search/pins/?q={query}",
        "collected_at": "2026-06-24T00:00:00+00:00"
    }


def test_resumable_browser_ingest_merges_query_provenance(tmp_path: Path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_json(first, {"query": "landscape", "pins": [pin("1", "landscape")]})
    write_json(second, {"query": "ecology", "pins": [pin("1", "ecology"), pin("2", "ecology")]})
    pipeline.ingest_browser_batch(tmp_path, first)
    result = pipeline.ingest_browser_batch(tmp_path, second)
    rows = pipeline.base.read_jsonl(tmp_path / "raw/captured.jsonl")
    assert result["captured"] == 2
    assert rows[0]["queries"] == ["ecology", "landscape"]


def test_quality_gate_thresholds(tmp_path: Path):
    pipeline.base.ensure_dirs(tmp_path)
    pipeline.base.write_jsonl(tmp_path / "raw/captured.jsonl", [{"record_id": str(i)} for i in range(105)])
    pipeline.base.write_jsonl(tmp_path / "raw/assets.jsonl", [{"record_id": str(i)} for i in range(105)])
    write_json(tmp_path / "reports/pilot_review.json", {
        "reviewed": 105, "relevant": 105,
        "near_duplicate_checks": 105, "near_duplicate_misses": 0
    })
    write_json(tmp_path / "reports/validation.json", {"checked": 105, "failed": 0})
    assert pipeline.quality_gate(tmp_path)["passed"] is True


def test_pinterest_style_is_opt_in():
    row = {
        "record_id": "test",
        "classification": {"primary_category": "场地区位", "secondary_categories": [], "status": "accepted"},
        "analysis": {
            "base_map_type": "vector", "projection": "orthographic",
            "chart_content": ["site"], "analysis_logic": ["observe"],
            "layout": {}, "color_style": {}, "line_symbols": {},
            "text_system": {}, "graphic_expression": {}
        }
    }
    plain = pipeline.prompt_pack(row)
    styled = pipeline.prompt_pack(row, "pinterest_dataset", "ecological_layered_wash", 0.7)
    assert "style_reference" not in plain["universal_json_prompt"]
    assert styled["universal_json_prompt"]["style_reference"]["strength_band"] == "medium"
    assert "ecological layered wash" in styled["midjourney"]["prompt"]


def test_pinterest_style_auto_selects_a_suitable_cluster():
    row = {
        "record_id": "ecology",
        "classification": {
            "primary_category": "生态水文",
            "drawing_subtype": "green infrastructure",
            "secondary_categories": [],
            "status": "accepted",
        },
        "analysis": {
            "base_map_type": "vector",
            "projection": "orthographic",
            "chart_content": ["ecology", "hydrology"],
            "analysis_logic": ["overlay"],
            "layout": {},
            "color_style": {},
            "line_symbols": {},
            "text_system": {},
            "graphic_expression": {},
        },
    }
    styled = pipeline.prompt_pack(row, "pinterest_dataset", "auto", 0.3)
    reference = styled["universal_json_prompt"]["style_reference"]
    assert reference["cluster"] == "ecological_layered_wash"
    assert reference["strength_band"] == "low"
    assert reference["selection_mode"] == "auto"