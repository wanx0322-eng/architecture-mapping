#!/usr/bin/env python3
"""Encode visual review decisions for the final nine Pilot thumbnails."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


pipeline = load_module("pipeline", ROOT / "scripts/pipeline.py")
batch2 = load_module("batch2", ROOT / "scripts/bootstrap_pilot_analysis_batch2.py")


DECISIONS = {
    1: ("人群行为", ["活动分区", "使用场景"]),
    2: ("爆炸图", ["景观系统", "轴测分层"]),
    3: ("人群行为", ["花园类型", "活动原型"]),
    4: ("功能流线", ["路径概念", "线性组织"]),
    5: ("爆炸图", ["生态系统", "景观分层"]),
    6: ("现状问题", ["景观节点", "剖面诊断"]),
    7: ("现状问题", ["场地剖面", "节点对比"]),
    8: ("爆炸图", ["生态图层", "垂直关系"]),
    9: ("手绘构思", ["设计原则", "生态概念"]),
}


def main() -> None:
    index = json.loads((ROOT / "dataset/reports/review-sheets/index.json").read_text(encoding="utf-8"))
    queue = {row["record_id"]: row for row in pipeline.read_jsonl(ROOT / "dataset/raw/core_queue.jsonl")}
    outputs = []
    for row in index:
        category, tags = DECISIONS[row["review_no"]]
        item = queue[row["record_id"]]
        outputs.append({"record_id": item["record_id"], "result": batch2.build_result(item, category, tags)})
    output = ROOT / "dataset/raw/pilot_analysis_results_batch3.jsonl"
    pipeline.write_jsonl(output, outputs)
    print(json.dumps({"output": str(output), "records": len(outputs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
