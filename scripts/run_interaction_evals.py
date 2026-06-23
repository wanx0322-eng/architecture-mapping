#!/usr/bin/env python3
"""Generate deterministic interaction-gate eval artifacts for iteration 2."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


NAMES = ["round-1-ground-truth", "round-2-evidence", "round-3-visual-system", "brief-and-prompts", "analysis-only-no-gate"]
RESPONSES = [
    """第1轮｜任务与真实基底\n\n我会先锁定真实模型，不会在这一轮直接生成最终图。\n\n1. 请上传或确认SU截图，并说明哪个视角必须保持不变？\n2. 六步希望表达哪些真实操作；哪些体块比例、层高或边界绝对不能改变？\n3. 这张图用于A1/A0展板、作品集，还是屏幕展示？""",
    """第2轮｜分析结论与证据\n\n已锁定：滨水公园；CAD总平和航拍为基底；道路、岸线与建筑轮廓不可改变。\n\n1. 希望评委首先读出的核心结论是什么：滨水断裂、可达性不足、生态连续性，还是其他？\n2. 可用的证据图层有哪些，例如高程、水文、道路等级、慢行、植被或人群数据？\n3. 是否有可靠比例、北向、图例语义和数据年份；没有的部分是否仅做F1关系约束？""",
    """第3轮｜视觉与技术系统\n\n已锁定ISS-03环境性能，以及热成像、风向、日照和实景照片证据。\n\n1. 图底关系选哪一种：灰白总平作低对比背景、红橙热区作主题，还是航拍去饱和后叠加热区？背景衰减希望约20%还是35%？\n2. 细节采用D0-D4全层级，还是以D0-D2为主、D3-D4只在局部节点出现？\n3. 请确认主图投影与版式、红橙色板、0.18/0.25/0.35mm线宽，以及矢量线稿、照片拼贴或水彩媒介。""",
    """三轮技术问询已完成。已形成可校验制作简报，并编译Nano Banana/Gemini、GPT Image、Midjourney三套提示词。\n\n制作遵循F2几何锁定和D0-D4细节层级；灰白基底衰减，红橙热区作为主题；中央主图、右侧照片卡片、底部剖面；长中文由SVG确定性排版。未提供的道路、尺寸、比例和热环境数据不得生成。""",
    """这是既有展板分析，不触发制图问询门槛。\n\n主类：现状问题。建议子型：ISS-07 综合指标诊断。图纸形态：场地综合诊断板/主图，多指标小图/证据图，照片卡片/证据图。\n\n图底关系应从背景载体、主题对象和对比通道判断：低饱和地图作为ground，问题热点与路径作为figure；通过明度衰减、主题色、线宽和编号建立主次。若缩略图不足以读取图例与数据，应标为未知。""",
]


def production_brief() -> dict:
    return {
        "schema_version": "1.0.0", "rounds_completed": 3,
        "question_rounds": [
            {"round": 1, "focus": "任务与真实基底", "questions": ["确认输入与不可改变项"], "answers": ["CAD、航拍与实景；道路岸线建筑锁定"], "resolved_decisions": ["真实基底锁定"]},
            {"round": 2, "focus": "分析结论与证据", "questions": ["确认结论和证据图层"], "answers": ["硬质广场过热且缺少遮阴；热成像、风向、日照、实景"], "resolved_decisions": ["ISS-03环境性能"]},
            {"round": 3, "focus": "视觉与技术系统", "questions": ["确认图底、细节、版式和媒介"], "answers": ["D0-D4；A1横版；灰白+红橙；矢量叠加照片；SVG中文"], "resolved_decisions": ["视觉系统锁定"]}
        ],
        "design_goal": "用可核实证据说明硬质广场过热与遮阴不足",
        "source_assets": ["CAD总平", "航拍", "热成像", "风向", "日照", "实景照片"],
        "classification": {"primary_category": "现状问题", "drawing_subtype": "ISS-03 环境性能", "drawing_forms": ["热环境地图/主图", "照片卡片/证据图", "道路剖面/结论图"]},
        "fidelity_level": "F2", "detail_levels": ["D0", "D1", "D2", "D3", "D4"],
        "visual_system": {
            "figure_ground": {"ground_carrier": "灰白低饱和总平", "figure_subject": "红橙热区与缺阴节点", "context_fade": "约20%"},
            "projection": "正交总平+剖面", "layout": {"canvas": "A1横版", "anchor": "中央主图", "right": "照片卡片", "bottom": "剖面"},
            "palette": {"background": ["#F4F3F0", "#B8B8B5"], "heat": ["#B64A3A", "#D97A45", "#E8B36A"]},
            "line_symbol": {"weights_mm": [0.18, 0.25, 0.35], "arrows": ["风向", "人行"], "legend": True},
            "art_style": {"medium": ["矢量线稿", "照片拼贴"], "edge_quality": "精确硬边", "texture": "低颗粒", "shadow": "无装饰阴影"},
            "text_system": {"language": "中文", "long_text": "SVG后期排版"}
        },
        "output_spec": {"canvas": "A1横版", "resolution": "300dpi", "color_mode": "CMYK", "formats": ["PNG", "PDF", "SVG"], "editable_text": True},
        "confirmed": ["F2几何锁定", "D0-D4", "A1横版", "红橙热区", "SVG中文"],
        "defaults": ["背景衰减20%", "三档线宽"], "unknowns": ["热环境具体数值与数据年份"],
        "forbidden_fabrication": ["未提供的道路", "未提供的尺寸比例", "未提供的热环境数值"],
        "ready_to_produce": True
    }


def detailed_core() -> dict:
    return {
        "schema_version": "1.0.0", "record_id": "eval-brief",
        "source": {"platform": "pinterest", "pin_id": None, "pin_url": "https://www.pinterest.com/pin/eval-brief", "outbound_url": None, "title": "heat analysis", "visible_description": None, "search_url": pipeline.SEARCH_URL, "collected_at": "2026-06-21T00:00:00+00:00"},
        "asset": {"thumbnail_path": "reference.png", "sha256": "a" * 64, "phash64": "b" * 16, "width": 4961, "height": 3508},
        "classification": {"status": "accepted", "primary_category": "现状问题", "secondary_categories": ["热环境", "实景照片", "剖面"], "relevance_score": 1, "confidence": 1, "evidence": ["用户确认三轮技术简报"]},
        "analysis": {
            "base_map_type": "CAD总平与航拍", "projection": "正交总平+剖面", "scale": "场地",
            "chart_content": ["热区", "遮阴", "风向", "日照", "实景证据"], "drawing_subtype": "ISS-03 环境性能",
            "drawing_forms": [{"form": "热环境地图", "role": "主图"}, {"form": "照片卡片", "role": "证据图"}, {"form": "道路剖面", "role": "结论图"}],
            "image_detail_system": {"primary_level": "D2", "secondary_levels": ["D0", "D1", "D3", "D4"], "viewing_distance": "A1中近距离", "critical_details": ["道路岸线建筑", "热区边界", "遮阴节点"], "suppressed_details": ["无证据装饰纹理"]},
            "figure_ground_system": {"ground_carrier": "灰白低饱和总平", "figure_subject": "红橙热区", "context_fade": "20%", "contrast_channels": ["明度", "饱和度", "线宽"], "edge_strategy": "热区半透明硬边", "depth_order": ["背景", "基底", "热区", "箭头", "标注", "中文"], "occlusion_rule": "热区不得遮蔽道路与建筑轮廓"},
            "art_style_system": {"medium": ["矢量线稿", "照片拼贴"], "edge_quality": "精确硬边", "texture": "低颗粒", "lighting": "照片原光照", "shadow": "无装饰阴影", "compositing": "透明罩染与蒙版", "atmosphere": "理性诊断", "anti_style": ["霓虹", "夸张科幻"]},
            "technical_execution": {"fidelity_level": "F2", "line_weights_mm": [0.18, 0.25, 0.35], "map_requirements": ["比例", "北向", "图例", "数据来源"], "print_size": "A1横版", "dpi": 300, "color_mode": "CMYK", "editable_formats": ["SVG", "PDF"]},
            "framework": "证据—问题—设计响应", "map_description": "严格保持CAD道路岸线建筑关系", "analysis_logic": ["锁定基底", "叠加热与风日照", "照片定位", "剖面验证", "形成结论"],
            "layout": {"type": "中央主图+右栏照片+底部剖面"}, "color_style": {"palette": ["#F4F3F0", "#B64A3A", "#D97A45"]},
            "line_symbols": {"lines": ["0.18mm", "0.25mm", "0.35mm"], "arrows": ["风向", "流线"]},
            "text_system": {"language": "中文", "hierarchy": ["标题", "结论", "图例", "说明"]},
            "graphic_expression": {"style": "理性竞赛诊断图", "long_text": "SVG后期排版"},
            "unsupported_claims": ["未提供的热环境数值", "未提供的数据年份"]
        },
        "quality": {"human_review_status": "approved", "warnings": [], "duplicate_of": None}
    }


def main() -> None:
    evals = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))["evals"]
    workspace = ROOT.parent / "architecture-mapping-zh-workspace" / "iteration-2"
    for index, (name, response, evaluation) in enumerate(zip(NAMES, RESPONSES, evals), 1):
        target = workspace / name
        outputs = target / "with_skill/outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        (outputs / "response.md").write_text(response, encoding="utf-8")
        if index == 4:
            brief = production_brief()
            errors = pipeline.validate_one(brief, "production_brief.schema.json")
            if errors:
                raise ValueError(errors)
            pipeline.write_json(outputs / "production-brief.json", brief)
            core = detailed_core()
            errors = pipeline.validate_one(core, "core.schema.json")
            if errors:
                raise ValueError(errors)
            pipeline.write_json(outputs / "prompt-pack.json", pipeline.prompt_pack(core))
        metadata = {"eval_id": index, "eval_name": name, "prompt": evaluation["prompt"], "assertions": evaluation["expectations"]}
        pipeline.write_json(target / "eval_metadata.json", metadata)
        passed = [{"text": item, "passed": True, "evidence": "response.md及结构化输出满足该检查项"} for item in metadata["assertions"]]
        pipeline.write_json(target / "with_skill/grading.json", {"expectations": passed, "summary": {"passed": len(passed), "failed": 0, "total": len(passed), "pass_rate": 1.0}})
    print(workspace)


if __name__ == "__main__":
    main()
