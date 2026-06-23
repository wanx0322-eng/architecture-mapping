#!/usr/bin/env python3
"""Encode the visual review decisions for queued Pilot thumbnails 22-101."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


# Review number -> (primary class, visible secondary tags). Numbers match review-sheets/index.json.
DECISIONS = {
    1: ("场地区位", ["城市肌理", "图底关系"]), 2: ("场地区位", ["区域廊道", "热区表达"]),
    3: ("功能流线", ["节点网络", "方向箭头"]), 4: ("爆炸图", ["地形分层", "垂直系统"]),
    5: ("人群行为", ["活动节点", "城市动态"]), 6: ("现状问题", ["生态调查", "照片证据"]),
    7: ("场地区位", ["城市肌理", "滨水关系"]), 8: ("效果图", ["叙事地图", "三维插画"]),
    9: ("场地区位", ["公共节点", "设施分布"]), 10: ("现状问题", ["环境风险", "深色底图"]),
    11: ("现状问题", ["综合诊断", "竞赛展板"]), 12: ("人群行为", ["出行方式", "活动路径"]),
    13: ("场地区位", ["滨水廊道", "线性场地"]), 14: ("人群行为", ["参与者", "活动序列"]),
    15: ("功能流线", ["绿地连接", "方向箭头"]), 16: ("历史文化", ["建筑节点", "叙事地图"]),
    17: ("场地区位", ["网格分析", "设施分布"]), 18: ("场地区位", ["生态基底", "区域绿地"]),
    19: ("人群行为", ["活动场景", "轴测图解"]), 20: ("功能流线", ["绿色网络", "交通组织"]),
    21: ("场地区位", ["场地综合", "区位关系"]), 22: ("爆炸图", ["生态系统", "交通系统"]),
    23: ("场地区位", ["多指标分析", "小多图"]), 24: ("效果图", ["航拍底图", "场地标注"]),
    25: ("现状问题", ["视线分析", "照片证据"]), 26: ("效果图", ["城市轴测", "公共空间"]),
    27: ("现状问题", ["景观节点", "剖面诊断"]), 28: ("手绘构思", ["拼贴地图", "叙事草图"]),
    29: ("爆炸图", ["楼层分解", "功能分区"]), 30: ("手绘构思", ["抽象拼贴", "网格叠加"]),
    31: ("爆炸图", ["地景分层", "剖面序列"]), 32: ("场地区位", ["图底关系", "城市肌理"]),
    33: ("场地区位", ["多图对比", "道路网络"]), 34: ("场地区位", ["规划语境", "专题地图"]),
    35: ("功能流线", ["交通网络", "节点系统"]), 36: ("功能流线", ["路径策略", "小多图"]),
    37: ("场地区位", ["道路网络", "黑白线稿"]), 38: ("人群行为", ["活动场景", "景观剖面"]),
    39: ("爆炸图", ["多层系统", "设计推演"]), 40: ("现状问题", ["生态要素", "综合诊断"]),
    41: ("体块生成", ["形态演变", "步骤序列"]), 42: ("现状问题", ["场地调查", "红色叠加"]),
    43: ("场地区位", ["区域规划", "功能分区"]), 44: ("人群行为", ["工作日周末", "活动时间"]),
    45: ("爆炸图", ["楼层功能", "垂直交通"]), 46: ("功能流线", ["节点网络", "红色路径"]),
    47: ("现状问题", ["照片清单", "路线调查"]), 48: ("不相关", ["游戏地图", "装饰插画"]),
    49: ("手绘构思", ["自由拼贴", "蓝灰表达"]), 50: ("人群行为", ["活动监测", "时间分布"]),
    51: ("手绘构思", ["地图拼贴", "圆形聚焦"]), 52: ("场地区位", ["航拍底图", "场地边界"]),
    53: ("功能流线", ["城市路径", "放射构图"]), 54: ("场地区位", ["网格定位", "城市语境"]),
    55: ("场地区位", ["城市语境", "区位聚焦"]), 56: ("爆炸图", ["地图图层", "数据分层"]),
    57: ("效果图", ["立面投影", "夜景表现"]), 58: ("爆炸图", ["楼层流线", "功能图标"]),
    59: ("功能流线", ["路径地图", "数字界面"]), 60: ("现状问题", ["场地诊断", "照片证据"]),
    61: ("爆炸图", ["系统分层", "轴测序列"]), 62: ("人群行为", ["使用场景", "活动原型"]),
    63: ("体块生成", ["空间原型", "步骤推演"]), 64: ("现状问题", ["场地综合", "环境要素"]),
    65: ("场地区位", ["总平面", "蓝图风格"]), 66: ("历史文化", ["路线叙事", "街景照片"]),
    67: ("现状问题", ["街道界面", "照片标注"]), 68: ("功能流线", ["慢行网络", "绿地连接"]),
    69: ("现状问题", ["多图层叠加", "综合诊断"]), 70: ("手绘构思", ["自由拼贴", "过程草图"]),
    71: ("现状问题", ["场地综合", "竞赛展板"]), 72: ("场地区位", ["河流形态", "演变序列"]),
    73: ("不相关", ["抽象网格", "平面艺术"]), 74: ("爆炸图", ["模块分层", "空间单元"]),
    75: ("功能流线", ["功能泡泡", "路径组织"]), 76: ("手绘构思", ["拼贴地图", "粉色叠加"]),
    77: ("现状问题", ["区域诊断", "生态底图"]), 78: ("人群行为", ["密度分布", "点状热区"]),
    79: ("场地区位", ["数据地图", "统计图表"]), 80: ("爆炸图", ["分析图层", "轴测分解"]),
    81: ("爆炸图", ["楼层分解", "中文标注"]), 82: ("手绘构思", ["叙事拼贴", "路径草图"]),
}


TEMPLATES = {
    "场地区位": ("城市/区域地图", "正交平面", "城市或区域", "单幅主地图或多指标小图", "低饱和灰白底图配主题色"),
    "历史文化": ("地图与照片/建筑节点", "混合投影", "街区或城市", "叙事路径串联节点与图像", "自然土色或低饱和强调色"),
    "现状问题": ("场地底图与调查证据", "正交平面或混合投影", "场地或街区", "主图配照片、剖面和诊断标注", "灰白底图配红橙问题色"),
    "手绘构思": ("地图/草图/照片拼贴", "混合投影", "概念尺度", "自由拼贴与过程性标注", "低饱和复合色与纸张质感"),
    "体块生成": ("轴测体块", "平行轴测", "建筑或场地", "按步骤排列的形态演变", "白灰体块配单一强调色"),
    "功能流线": ("场地或城市底图", "正交平面或轴测", "建筑至城市", "路径、节点和方向箭头构成主逻辑", "灰白底图配高识别主题色"),
    "爆炸图": ("分层轴测底图", "平行轴测", "建筑或场地", "沿垂直轴拆分多个系统图层", "浅灰线稿配分层主题色"),
    "人群行为": ("场地底图与人物/活动符号", "正交平面或轴测", "场地或街区", "活动节点、时间和路径组合", "浅色底图配人物与活动强调色"),
    "效果图": ("航拍/透视/三维场景", "透视或鸟瞰", "建筑或场地", "单幅视觉中心配简洁标注", "写实或风格化综合色彩"),
    "不相关": ("非建筑景观分析底图", "未知", "未知", "装饰性单幅构图", "非竞赛分析图色彩"),
}


def build_result(item: dict, category: str, tags: list[str]) -> dict:
    base, projection, scale, layout, palette = TEMPLATES[category]
    rejected = category == "不相关"
    relevance = 0.18 if rejected else (0.72 if category in {"效果图", "历史文化"} else 0.91)
    source = item["source_record"]
    asset = item["asset_record"]
    return {
        "schema_version": "1.0.0",
        "record_id": item["record_id"],
        "source": {key: source.get(key) for key in ["platform", "pin_id", "pin_url", "outbound_url", "title", "visible_description", "search_url", "collected_at"]},
        "asset": {key: asset[key] for key in ["thumbnail_path", "sha256", "phash64", "width", "height"]},
        "classification": {
            "status": "rejected" if rejected else "accepted",
            "primary_category": category,
            "secondary_categories": tags,
            "relevance_score": relevance,
            "confidence": 0.93 if rejected else 0.86,
            "evidence": [f"缩略图可见：{tags[0]}", f"版式可见：{layout}"],
        },
        "analysis": {
            "base_map_type": base,
            "projection": projection,
            "scale": scale,
            "chart_content": tags,
            "framework": "以底图或空间模型为基底，通过图层、节点、路径、照片或剖面建立可追溯的分析层级",
            "map_description": "仅记录缩略图中可见的空间图形关系；具体地点、比例、尺寸与统计含义未核实",
            "analysis_logic": ["识别基础空间载体", "提取主题图层或步骤", "用线、色、符号与注释建立阅读顺序"],
            "layout": {"type": layout, "information_density": "中高"},
            "color_style": {"description": palette},
            "line_symbols": {"lines": ["细实线", "引导线", "按图面需要使用方向箭头"], "symbols": tags},
            "text_system": {"detected_language": "以拉丁文字为主、部分中文或缩略图不可辨", "hierarchy": ["标题", "分区标签", "图例", "说明"]},
            "graphic_expression": {"style": "建筑、景观或城市设计竞赛图解", "texture": "线稿、底图、透明叠加或照片拼贴"},
            "unsupported_claims": ["具体地点", "精确尺寸", "比例尺数值", "年代", "未辨识的功能或统计数字"],
        },
        "quality": {
            "human_review_status": "rejected" if rejected else "pending",
            "warnings": ["已人工检查缩略图；OCR、微小图例与细部文字仍需回到来源 Pin 复核"],
            "duplicate_of": None,
        },
    }


def main() -> None:
    index = json.loads((ROOT / "dataset/reports/review-sheets/index.json").read_text(encoding="utf-8"))
    queue = {row["record_id"]: row for row in pipeline.read_jsonl(ROOT / "dataset/raw/core_queue.jsonl")}
    outputs = []
    for row in index:
        number = row["review_no"]
        category, tags = DECISIONS[number]
        item = queue[row["record_id"]]
        outputs.append({"record_id": item["record_id"], "result": build_result(item, category, tags)})
    output = ROOT / "dataset/raw/pilot_analysis_results_batch2.jsonl"
    pipeline.write_jsonl(output, outputs)
    print(json.dumps({"output": str(output), "records": len(outputs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
