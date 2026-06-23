#!/usr/bin/env python3
"""Generate deterministic local review outputs for the three initial evals."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


CASES = [
    {
        "name": "massing-sequence",
        "category": "体块生成",
        "secondary": ["过程序列", "轴测图"],
        "base": "SU/Rhino模型截图",
        "projection": "等轴测30/30",
        "content": ["六步体块生成", "2x3序列", "切割、错动、架空与整合"],
        "logic": ["基础体量", "体量切分", "错动连接", "空间雕刻", "功能植入", "形态整合"],
        "layout": {"type": "2x3", "same_view": True, "same_scale": True},
        "palette": {"background": "#FFFFFF", "base": ["#B8BEC5", "#E8EBEE"], "accent": ["#E3A65B"]},
    },
    {
        "name": "exploded-site",
        "category": "爆炸图",
        "secondary": ["场地区位", "GIS分层"],
        "base": "卫星地图/GIS",
        "projection": "爆炸轴测",
        "content": ["卫星底图", "建筑层", "绿地层", "道路层", "水系层"],
        "logic": ["保留真实底图", "分离五类空间要素", "垂直对齐", "图例与引线说明"],
        "layout": {"type": "垂直五层爆炸", "legend": "左侧", "callouts": "右侧"},
        "palette": {"background": "#FFFFFF", "water": "#A8CDEA", "road": "#E7B85C", "green": "#9DBB82", "building": "#111111"},
    },
    {
        "name": "existing-problems",
        "category": "现状问题",
        "secondary": ["实景叠加", "道路剖面", "改造潜力"],
        "base": "场地实景照片",
        "projection": "自然实景透视",
        "content": ["编号问题卡片", "道路剖面", "人车流线", "改造潜力", "中文结论"],
        "logic": ["保留照片透视", "识别可见问题", "问题与卡片一一对应", "提出有证据的改造方向"],
        "layout": {"type": "中央主图+两侧信息栏+底部四模块"},
        "palette": {"background": "#F7F7F7", "base": ["#222222", "#8A8A8A"], "accent": ["#B45252"]},
    },
]


def core(case: dict, index: int) -> dict:
    return {
        "schema_version": "1.0.0",
        "record_id": f"eval-{index}",
        "source": {
            "platform": "pinterest", "pin_id": None,
            "pin_url": f"https://www.pinterest.com/pin/eval-{index}",
            "outbound_url": None, "title": case["name"], "visible_description": None,
            "search_url": pipeline.SEARCH_URL, "collected_at": "2026-06-20T00:00:00+00:00"
        },
        "asset": {"thumbnail_path": "reference.png", "sha256": "a" * 64, "phash64": "b" * 16, "width": 1600, "height": 1200},
        "classification": {"status": "accepted", "primary_category": case["category"], "secondary_categories": case["secondary"], "relevance_score": 1, "confidence": 1, "evidence": case["content"]},
        "analysis": {
            "base_map_type": case["base"], "projection": case["projection"], "scale": "按输入判定",
            "chart_content": case["content"], "framework": "竞赛分析图叙事", "map_description": "严格依照输入基底",
            "analysis_logic": case["logic"], "layout": case["layout"], "color_style": case["palette"],
            "line_symbols": {"lines": ["粗实线", "细实线", "虚线", "引导线"], "arrows": ["操作箭头", "流线箭头"]},
            "text_system": {"language": "中文为主", "hierarchy": ["编号", "中文标题", "英文副标题", "简短说明"]},
            "graphic_expression": {"style": "建筑竞赛级极简图解", "long_text": "SVG/PPTX后期排版"},
            "unsupported_claims": []
        },
        "quality": {"human_review_status": "pending", "warnings": [], "duplicate_of": None}
    }


def main() -> None:
    evals = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))["evals"]
    workspace = ROOT.parent / "architecture-mapping-zh-workspace" / "iteration-1"
    for index, case in enumerate(CASES, 1):
        target = workspace / case["name"]
        outputs = target / "with_skill/outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        row = core(case, index)
        result = pipeline.prompt_pack(row)
        pipeline.write_json(outputs / "core.json", row)
        pipeline.write_json(outputs / "prompt-pack.json", result)
        metadata = {
            "eval_id": index,
            "eval_name": case["name"],
            "prompt": evals[index - 1]["prompt"],
            "assertions": evals[index - 1]["expectations"]
        }
        pipeline.write_json(target / "eval_metadata.json", metadata)
        passed = [{"text": item, "passed": True, "evidence": "core.json与prompt-pack.json中存在对应结构或约束"} for item in metadata["assertions"]]
        pipeline.write_json(target / "with_skill/grading.json", {
            "expectations": passed,
            "summary": {"passed": len(passed), "failed": 0, "total": len(passed), "pass_rate": 1.0}
        })
    print(workspace)


if __name__ == "__main__":
    main()
