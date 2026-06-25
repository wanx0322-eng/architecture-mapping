from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline_v030_status", ROOT / "scripts/pipeline_v030.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


def test_collection_status_uses_merged_pin_index(tmp_path: Path):
    pipeline.base.ensure_dirs(tmp_path)
    pipeline.base.write_jsonl(tmp_path / "raw/captured.jsonl", [{"record_id": "pilot"}])
    pipeline.base.write_jsonl(tmp_path / "raw/pins.jsonl", [
        {"record_id": "pilot"},
        {"record_id": "expanded"},
    ])
    assert pipeline.collection_status(tmp_path)["captured"] == 2
