#!/usr/bin/env python3
"""Encode the visually reviewed expansion records needed to reach 500 accepted samples."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIMIT = 408  # 401 accepted + 7 rejected; active accepted baseline is 99.


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


pipeline = load_module("pipeline", ROOT / "scripts/pipeline.py")
batch2 = load_module("batch2", ROOT / "scripts/bootstrap_pilot_analysis_batch2.py")


REJECTED = {133, 153, 183, 191, 221, 346, 349}
HISTORY = {20, 28, 70, 93, 107, 112, 132, 163, 168, 169, 172, 186, 189, 210, 214, 217, 238, 276, 287, 292, 300, 308, 320, 365, 383, 385, 389}
MASSING = {6, 24, 41, 61, 62, 120, 174, 198, 234, 241, 271}
EXPLODED = {9, 21, 39, 42, 45, 50, 58, 80, 104, 113, 124, 128, 134, 140, 141, 187, 203, 232, 253, 259, 264, 338, 389, 398}
BEHAVIOR = {14, 32, 34, 48, 53, 69, 71, 105, 121, 149, 176, 184, 200, 208, 230, 278, 310, 313, 318, 336, 370, 388, 395}
SKETCH = {30, 38, 51, 60, 76, 99, 102, 111, 122, 127, 136, 139, 157, 167, 175, 182, 220, 231, 296, 306, 309, 319, 324, 334, 352, 360, 367}
FLOW = {3, 13, 17, 26, 27, 31, 44, 56, 66, 90, 91, 97, 108, 118, 129, 135, 147, 150, 151, 154, 158, 166, 173, 188, 195, 196, 199, 201, 204, 211, 212, 229, 237, 254, 261, 273, 290, 301, 303, 307, 315, 321, 322, 337, 341, 342, 345, 347, 348, 353, 354, 357, 359, 361, 364, 366, 368, 371, 374, 381, 387, 392, 397, 399, 400, 404, 405, 406}
EFFECT = {7, 8, 10, 11, 23, 35, 37, 55, 59, 64, 73, 79, 86, 88, 89, 96, 98, 101, 103, 106, 114, 119, 123, 126, 142, 144, 146, 160, 161, 164, 179, 185, 193, 197, 218, 223, 235, 236, 239, 244, 246, 251, 257, 258, 260, 262, 265, 266, 272, 283, 284, 291, 297, 298, 299, 302, 304, 305, 312, 317, 323, 325, 328, 330, 340, 344, 351, 355, 362, 369, 375, 376, 378, 379, 390, 391, 396, 401, 402, 403, 407}
LOCATION = {5, 12, 16, 18, 19, 25, 29, 33, 36, 40, 43, 45, 46, 47, 49, 52, 54, 57, 63, 65, 67, 68, 72, 74, 75, 77, 78, 81, 82, 83, 84, 85, 87, 94, 95, 100, 109, 110, 115, 116, 117, 125, 130, 131, 137, 138, 145, 152, 155, 156, 159, 165, 171, 178, 180, 181, 188, 190, 192, 194, 201, 202, 204, 205, 207, 209, 213, 215, 216, 222, 225, 226, 227, 228, 233, 237, 240, 242, 243, 248, 249, 252, 255, 256, 263, 267, 268, 269, 274, 275, 277, 280, 281, 282, 286, 288, 289, 293, 294, 307, 311, 316, 317, 322, 326, 327, 329, 331, 332, 341, 343, 345, 347, 350, 356, 358, 363, 364, 371, 373, 374, 377, 380, 381, 384, 386, 387, 392, 393, 394, 397, 399, 408}


TAGS = {
    "场地区位": ["区位关系", "城市肌理"],
    "历史文化": ["历史演变", "文化节点"],
    "现状问题": ["场地诊断", "综合分析"],
    "手绘构思": ["概念拼贴", "过程草图"],
    "体块生成": ["形态演变", "步骤序列"],
    "功能流线": ["路径组织", "方向箭头"],
    "爆炸图": ["系统分层", "轴测分解"],
    "人群行为": ["活动分布", "使用场景"],
    "效果图": ["空间表现", "方案展示"],
    "不相关": ["非分析图本体", "素材或课程封面"],
}


def category(number: int) -> str:
    if number in REJECTED:
        return "不相关"
    if number in HISTORY:
        return "历史文化"
    if number in MASSING:
        return "体块生成"
    if number in EXPLODED:
        return "爆炸图"
    if number in BEHAVIOR:
        return "人群行为"
    if number in SKETCH:
        return "手绘构思"
    if number in FLOW:
        return "功能流线"
    if number in EFFECT:
        return "效果图"
    if number in LOCATION:
        return "场地区位"
    return "现状问题"


def main() -> None:
    index = json.loads((ROOT / "dataset/reports/review-sheets/index.json").read_text(encoding="utf-8"))
    queue = {row["record_id"]: row for row in pipeline.read_jsonl(ROOT / "dataset/raw/core_queue.jsonl")}
    outputs = []
    counts: dict[str, int] = {}
    for row in index[:LIMIT]:
        number = row["review_no"]
        primary = category(number)
        item = queue[row["record_id"]]
        outputs.append({"record_id": item["record_id"], "result": batch2.build_result(item, primary, TAGS[primary])})
        counts[primary] = counts.get(primary, 0) + 1
    output = ROOT / "dataset/raw/expansion_to_500_results.jsonl"
    pipeline.write_jsonl(output, outputs)
    print(json.dumps({"output": str(output), "records": len(outputs), "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
