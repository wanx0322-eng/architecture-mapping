#!/usr/bin/env python3
"""Build deep reverse-engineering records from the visually reviewed Pilot-0 core set."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


def full_record(core: dict) -> dict:
    ana = core["analysis"]
    cls = core["classification"]
    return {
        "metadata": {
            "image_category": "建筑/景观/城市设计竞赛分析图",
            "mood_atmosphere": ana["graphic_expression"].get("style", "理性、学术、信息密集")
        },
        "domain_specific_analysis": {
            "data_chart_attributes": {
                "chart_type": "、".join(cls["secondary_categories"]),
                "axes_and_legends": "以图例、编号、颜色和引线建立信息层级",
                "core_trends": "缩略图不支持可靠读取具体数据趋势"
            },
            "document_attributes": {
                "document_type": "竞赛/作品集分析图",
                "layout_structure": ana["layout"].get("type", "未知"),
                "special_marks_and_seals": []
            },
            "architectural_diagram_attributes": {
                "diagram_type": cls["primary_category"],
                "base_map": ana["base_map_type"],
                "projection": ana["projection"],
                "analysis_framework": ana.get("framework", "未知"),
                "map_description": ana.get("map_description", "未知"),
                "layout_system": ana["layout"].get("type", "未知"),
                "line_and_symbol_system": "、".join(ana["line_symbols"].get("lines", []) + ana["line_symbols"].get("symbols", [])),
                "text_explanation_system": "标题—标签—说明三级文字；细节需原Pin复核",
                "diagram_expression": ana["graphic_expression"].get("style", "竞赛分析图")
            }
        },
        "visual_elements": {
            "color_palette": [ana["color_style"].get("description", "按图中可见色彩")],
            "lighting": "以平面图解为主，无可靠写实光照信息",
            "composition": ana["layout"].get("type", "未知")
        },
        "content_and_subjects": [
            {
                "type": "architectural_mapping_diagram",
                "detailed_description": "、".join(ana["chart_content"]),
                "attributes": {"material_or_texture": ana["graphic_expression"].get("texture", "未知")}
            }
        ],
        "environment_and_space": {
            "setting_and_weather": "不适用或无法从缩略图确认",
            "spatial_relationships": ana.get("map_description", "未知")
        },
        "text_data": {"extracted_text": []},
        "global_summary": f"该图以{ana['base_map_type']}为基底，采用{ana['projection']}表达{cls['primary_category']}，版式为{ana['layout'].get('type', '未知')}。"
    }


def style_record(core: dict) -> dict:
    ana = core["analysis"]
    cls = core["classification"]
    style = ana["graphic_expression"].get("style", "architectural competition diagram")
    tags = [
        "architectural competition diagram", "mapping visualization", "academic layout",
        "precise vector linework", "information hierarchy", "clean annotations",
        "restrained color palette", "diagrammatic graphics", "editorial composition",
        "urban analysis", "white space", "technical illustration"
    ]
    return {
        "aesthetic_overview": {"core_style": style, "mood_and_vibe": "理性、学术、克制、可读"},
        "technical_execution": {
            "artistic_expression": {"medium_and_brushwork": "数字地图、矢量线稿与必要拼贴", "technique": "图层叠加、色块编码、引线标注"},
            "architectural_graphics": {"projection": ana["projection"], "layout": ana["layout"].get("type", "未知"), "diagram_type": cls["primary_category"]}
        },
        "visual_language": {
            "color_grading": [ana["color_style"].get("description", "克制配色")],
            "lighting_setup": "以平面图解为主，无写实光影或仅有统一弱阴影",
            "composition_rules": ana["layout"].get("type", "模块化信息布局")
        },
        "surface_and_tactility": {"material_properties": "以平面色块和线条为主", "texture_details": ana["graphic_expression"].get("texture", "低纹理")},
        "style_prompt_tags": tags
    }


def main() -> None:
    dataset = ROOT / "dataset"
    results = []
    for rep in pipeline.read_jsonl(dataset / "clusters/representatives.jsonl"):
        rid = rep["record_id"]
        core = pipeline.read_json(dataset / "records/core" / f"{rid}.json")
        results.append({"record_id": rid, "mode": "full", "result": full_record(core)})
        results.append({"record_id": rid, "mode": "style", "result": style_record(core)})
    output = dataset / "raw/pilot_deep_results.jsonl"
    pipeline.write_jsonl(output, results)
    print(output)


if __name__ == "__main__":
    main()
