#!/usr/bin/env python3
"""Create human-inspected core records for the first public Pinterest viewport."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)


ANALYSIS = {
    "pin-1101763496401238181": ("场地区位", ["灾害数据", "专题地图"], "GIS专题地图", "正交平面", "州域", "单幅主地图+侧栏数据", "低饱和灰白+少量蓝红", 0.82),
    "pin-12244230231130904": ("效果图", ["叙事拼贴", "建筑图解"], "建筑照片与图纸拼贴", "混合投影", "建筑/街区", "自由拼贴+中心主轴", "黑白灰+克莱因蓝", 0.96),
    "pin-16114511160240690": ("场地区位", ["生态节点", "卫星叠加"], "卫星/航拍", "高空正射", "城市滨水", "纵向主图+节点编号", "灰阶底图+低饱和红", 0.93),
    "pin-1688918607047915": ("功能流线", ["节点网络", "手绘构思"], "建筑线稿", "鸟瞰轴测", "街区", "散点节点+连续流线", "黑白线稿+红色流线", 0.95),
    "pin-248683210666736788": ("场地区位", ["城市肌理", "网格分析"], "城市线稿地图", "正交平面", "城市", "中心方形主图+网格", "黑白灰单色", 0.92),
    "pin-2533343538153095": ("场地区位", ["手绘构思", "混合表现"], "地图与手绘拼贴", "正交平面", "区域", "中心纵向拼贴+外围注释", "粉红/青绿/黑白混合", 0.86),
    "pin-314900198936916006": ("场地区位", ["多指标分析", "数据图表"], "GIS专题地图", "正交平面", "区域/城市", "纵向多模块报告", "深蓝+橙黄分级", 0.97),
    "pin-422281211512069": ("场地区位", ["节点分析", "城市更新"], "城市总平与实景拼贴", "正交平面", "城市廊道", "纵向廊道主轴+节点放大", "黑白灰+低饱和红绿", 0.98),
    "pin-459015387041966535": ("场地区位", ["城市肌理", "照片拼贴"], "Google Earth与城市线稿", "正交平面", "城市", "规则网格+图像镶嵌", "黑白灰", 0.90),
    "pin-465630048996769529": ("不相关", ["装饰地图"], "复古世界地图", "正交平面", "全球", "单幅装饰画", "棕金复古", 0.18),
    "pin-468163323788154480": ("场地区位", ["导览地图", "节点分析"], "简化街区地图", "正交平面", "街区", "主地图+编号清单", "多色扁平矢量", 0.67),
    "pin-49187820914775766": ("效果图", ["场地区位", "地形可视化"], "数字高程模型", "三维鸟瞰", "城市/区域", "中心三维地形+侧边数据", "深蓝底+橙色高亮", 0.91),
    "pin-498351515035961523": ("场地区位", ["手绘构思", "热区分析"], "抽象水彩地图", "正交平面", "城市", "纵向自由构图", "青蓝绿+橙色热点", 0.82),
    "pin-5066618331527578": ("场地区位", ["城市肌理", "图底关系"], "城市线稿与航拍拼贴", "正交平面", "城市", "规则网格+黑白镶嵌", "黑底白线", 0.92),
    "pin-637329784745291879": ("场地区位", ["城市肌理", "照片拼贴"], "城市地图与街景照片", "正交平面", "街区", "网格镶嵌+底部说明", "黑白灰+少量橙红", 0.94),
    "pin-639792690846319740": ("场地区位", ["节点分析", "图底关系"], "城市总平图", "正交平面", "城市", "圆形聚焦主图+侧栏", "黑白高对比+红色节点", 0.95),
    "pin-6755468173636370": ("手绘构思", ["混合表现", "叙事拼贴"], "手绘/图纸/照片混合", "混合投影", "建筑/场地", "上下分区+自由信息叠加", "黑白灰+粉绿黄点缀", 0.88),
    "pin-697776536052255625": ("场地区位", ["数据地图", "地形可视化"], "国家轮廓数据图", "三维正交", "国家", "上下双图+数据标注", "浅粉紫蓝渐层", 0.74),
    "pin-78953799712320062": ("场地区位", ["地形分析", "水系分析"], "地形等高线地图", "正交平面", "区域", "单幅连续地形", "低饱和青绿红", 0.78),
    "pin-848436017328599885": ("场地区位", ["城市肌理", "网格拼贴"], "地图纹理拼贴", "正交平面", "城市", "规则方格矩阵", "黑白灰单色", 0.88),
    "pin-889038782734642135": ("历史文化", ["效果图", "叙事地图"], "历史地景插画", "鸟瞰轴测", "文化线路", "纵向全景主图+两侧注释", "自然土色+蓝绿", 0.72),
}


def main() -> None:
    dataset = ROOT / "dataset"
    pins = {x["record_id"]: x for x in pipeline.read_jsonl(dataset / "raw/pins.jsonl")}
    assets = {x["record_id"]: x for x in pipeline.read_jsonl(dataset / "raw/assets.jsonl")}
    outputs = []
    for rid, values in ANALYSIS.items():
        if rid not in pins or rid not in assets:
            continue
        primary, secondary, base, projection, scale, layout, palette, relevance = values
        accepted = primary != "不相关"
        pin = pins[rid]
        asset = assets[rid]
        outputs.append({
            "record_id": rid,
            "result": {
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
                    "status": "accepted" if accepted else "rejected",
                    "primary_category": primary,
                    "secondary_categories": secondary,
                    "relevance_score": relevance,
                    "confidence": min(0.95, relevance + 0.03),
                    "evidence": [f"可见底图为{base}", f"版式为{layout}"]
                },
                "analysis": {
                    "base_map_type": base,
                    "projection": projection,
                    "scale": scale,
                    "chart_content": secondary,
                    "framework": "从基础地图/图像提取主题信息并通过视觉层级表达",
                    "map_description": "仅记录缩略图中可见的空间与图形关系，具体地点和数据含义未核实",
                    "analysis_logic": ["提取底图", "突出主题要素", "组织标注与视觉层级"],
                    "layout": {"type": layout, "information_density": "中高"},
                    "color_style": {"description": palette},
                    "line_symbols": {"lines": ["细实线", "必要的引导线"], "symbols": secondary},
                    "text_system": {"detected_language": "以英文为主或文字不可辨", "hierarchy": ["标题", "标签", "说明"]},
                    "graphic_expression": {"style": "竞赛/作品集式地图图解", "texture": "按图中可见表现记录"},
                    "unsupported_claims": ["具体地点", "精确尺寸", "比例尺", "未辨识的数据含义"]
                },
                "quality": {
                    "human_review_status": "pending",
                    "warnings": ["Pinterest缩略图分辨率有限，OCR和细节需以原Pin复核"],
                    "duplicate_of": None
                }
            }
        })
    output = dataset / "raw/pilot_analysis_results.jsonl"
    pipeline.write_jsonl(output, outputs)
    print(output)


if __name__ == "__main__":
    main()
