#!/usr/bin/env python3
"""Compile one three-model prompt example for each Pinterest style cluster."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline_v030", ROOT / "scripts/pipeline_v030.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


def main() -> None:
    dataset = Path(__file__).resolve().parents[2] / "architecture-mapping-zh-runtime"
    clusters = pipeline.read_json(dataset / "clusters/pinterest_style_clusters.json")
    out = dataset / "prompts/style_catalog"
    out.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for cluster_id, cluster in clusters["clusters"].items():
        record_id = cluster["representative_record_ids"][0]
        record = pipeline.read_json(dataset / "records/core" / f"{record_id}.json")
        prompt = pipeline.prompt_pack(record, "pinterest_dataset", cluster_id, 0.7)
        pipeline.base.write_json(out / f"{cluster_id}.json", prompt)
        catalog[cluster_id] = {
            "sample_count": cluster["sample_count"],
            "representative_record_id": record_id,
            "prompt_path": str((out / f"{cluster_id}.json").resolve())
        }
    pipeline.base.write_json(dataset / "reports/pinterest_style_catalog.json", catalog)
    print(json.dumps({"styles": len(catalog), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
