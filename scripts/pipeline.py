#!/usr/bin/env python3
"""Resumable dataset pipeline for architecture-mapping-zh."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

LOCAL_DEPS = Path(__file__).resolve().parents[1] / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import imagehash
import numpy as np
import requests
from jsonschema import Draft202012Validator, FormatChecker
from PIL import Image


CATEGORIES = [
    "场地区位", "历史文化", "现状问题", "手绘构思", "体块生成",
    "功能流线", "爆炸图", "人群行为", "效果图", "不相关",
]
SEARCH_URL = "https://www.pinterest.com/search/pins/?q=mapping&rs=typed"
SCHEMA_VERSION = "1.0.0"
USER_AGENT = "architecture-mapping-zh/1.0 research-thumbnail-client"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if isinstance(value, list):
            rows.extend(x for x in value if isinstance(x, dict))
        elif isinstance(value, dict):
            rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def current_unique_ids(root: Path) -> set[str]:
    """Return the active post-deduplication record IDs, if available."""
    unified = read_jsonl(root / "raw/unified_deduped.jsonl")
    if unified:
        return {row["record_id"] for row in unified if row.get("record_id")}
    rows = read_jsonl(root / "raw/deduped.jsonl")
    rows.extend(read_jsonl(root / "raw/local_deduped.jsonl"))
    return {row["record_id"] for row in rows if row.get("record_id")}


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        return None
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def record_id(row: dict[str, Any]) -> str:
    if row.get("pin_id"):
        return f"pin-{row['pin_id']}"
    seed = normalize_url(row.get("pin_url")) or row.get("image_url") or json.dumps(row, sort_keys=True)
    return "url-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def ensure_dirs(root: Path) -> None:
    for rel in ["raw", "thumbnails", "records/core", "records/deep", "prompts", "reports", "clusters"]:
        (root / rel).mkdir(parents=True, exist_ok=True)


def status_path(root: Path) -> Path:
    return root / "status.json"


def update_status(root: Path, **changes: Any) -> None:
    status = read_json(status_path(root), {}) or {}
    status.setdefault("schema_version", SCHEMA_VERSION)
    status.setdefault("search_url", SEARCH_URL)
    status.setdefault("target_unique_valid", 2100)
    status.setdefault("pilot_target", 100)
    status.update(changes)
    status["updated_at"] = now_iso()
    write_json(status_path(root), status)


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.root)
    ensure_dirs(root)
    update_status(root, state="initialized", raw_count=0, unique_count=0, accepted_count=0, rejected_count=0, last_error=None)
    print(root.resolve())


def load_input(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path)
    value = read_json(path)
    if isinstance(value, dict) and isinstance(value.get("pins"), list):
        value = value["pins"]
    if not isinstance(value, list):
        raise ValueError("input must be a JSON array, {pins:[...]}, or JSONL")
    return [x for x in value if isinstance(x, dict)]


def cmd_ingest(args: argparse.Namespace) -> None:
    root = Path(args.root)
    ensure_dirs(root)
    destination = root / "raw/pins.jsonl"
    existing = read_jsonl(destination)
    merged: dict[str, dict[str, Any]] = {record_id(x): x for x in existing}
    for item in load_input(Path(args.input)):
        pin_url = normalize_url(item.get("pin_url"))
        image_url = item.get("image_url")
        if not pin_url or not image_url:
            continue
        item = {
            "record_id": record_id(item),
            "pin_id": str(item["pin_id"]) if item.get("pin_id") else None,
            "pin_url": pin_url,
            "image_url": image_url,
            "title": item.get("title"),
            "visible_description": item.get("visible_description"),
            "outbound_url": normalize_url(item.get("outbound_url")),
            "search_url": item.get("search_url") or SEARCH_URL,
            "collected_at": item.get("collected_at") or now_iso(),
        }
        merged[item["record_id"]] = item
    rows = sorted(merged.values(), key=lambda x: x["record_id"])
    write_jsonl(destination, rows)
    update_status(root, state="ingested", raw_count=len(rows), last_error=None)
    print(json.dumps({"raw_count": len(rows)}, ensure_ascii=False))


def thumbnail_bytes(url: str, timeout: int) -> bytes:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT}, stream=True)
    response.raise_for_status()
    content = response.content
    if len(content) > 15 * 1024 * 1024:
        raise ValueError("image exceeds 15MB limit")
    return content


def cmd_thumbnails(args: argparse.Namespace) -> None:
    root = Path(args.root)
    ensure_dirs(root)
    rows = read_jsonl(root / "raw/pins.jsonl")
    existing = {x["record_id"]: x for x in read_jsonl(root / "raw/assets.jsonl")}
    failures = {x["record_id"]: x for x in read_jsonl(root / "raw/download_failures.jsonl")}
    for index, item in enumerate(rows, 1):
        rid = item["record_id"]
        if rid in existing and Path(existing[rid]["thumbnail_path"]).exists():
            continue
        try:
            raw = thumbnail_bytes(item["image_url"], args.timeout)
            sha = hashlib.sha256(raw).hexdigest()
            with Image.open(BytesIO(raw)) as image:
                image = image.convert("RGB")
                image.thumbnail((768, 768), Image.Resampling.LANCZOS)
                out = root / "thumbnails" / f"{rid}.jpg"
                image.save(out, "JPEG", quality=88, optimize=True)
                existing[rid] = {
                    "record_id": rid,
                    "thumbnail_path": str(out.resolve()),
                    "sha256": sha,
                    "phash64": str(imagehash.phash(image, hash_size=8)),
                    "width": image.width,
                    "height": image.height,
                    "downloaded_at": now_iso(),
                }
            failures.pop(rid, None)
        except Exception as exc:  # preserve error for resume
            failures[rid] = {"record_id": rid, "image_url": item["image_url"], "error": str(exc), "failed_at": now_iso()}
        if index % 25 == 0:
            write_jsonl(root / "raw/assets.jsonl", sorted(existing.values(), key=lambda x: x["record_id"]))
            write_jsonl(root / "raw/download_failures.jsonl", sorted(failures.values(), key=lambda x: x["record_id"]))
    write_jsonl(root / "raw/assets.jsonl", sorted(existing.values(), key=lambda x: x["record_id"]))
    write_jsonl(root / "raw/download_failures.jsonl", sorted(failures.values(), key=lambda x: x["record_id"]))
    update_status(root, state="thumbnails_ready", thumbnail_count=len(existing), download_failure_count=len(failures))
    print(json.dumps({"downloaded": len(existing), "failures": len(failures)}, ensure_ascii=False))


def hamming_hex(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def cmd_dedupe(args: argparse.Namespace) -> None:
    root = Path(args.root)
    pins = {x["record_id"]: x for x in read_jsonl(root / "raw/pins.jsonl")}
    assets = {x["record_id"]: x for x in read_jsonl(root / "raw/assets.jsonl")}
    candidates = [dict(pins[rid], asset=asset) for rid, asset in assets.items() if rid in pins]
    candidates.sort(key=lambda x: (x["asset"]["width"] * x["asset"]["height"], x["record_id"]), reverse=True)
    kept: list[dict[str, Any]] = []
    exact: dict[str, str] = {}
    duplicate_map: dict[str, str] = {}
    for item in candidates:
        sha = item["asset"]["sha256"]
        if sha in exact:
            duplicate_map[item["record_id"]] = exact[sha]
            continue
        near = None
        for current in kept:
            if hamming_hex(item["asset"]["phash64"], current["asset"]["phash64"]) <= args.phash_distance:
                ratio_a = item["asset"]["width"] / item["asset"]["height"]
                ratio_b = current["asset"]["width"] / current["asset"]["height"]
                if abs(math.log(ratio_a / ratio_b)) <= 0.08:
                    near = current["record_id"]
                    break
        if near:
            duplicate_map[item["record_id"]] = near
            continue
        exact[sha] = item["record_id"]
        kept.append(item)
    for item in kept:
        item["duplicate_sources"] = sorted([rid for rid, target in duplicate_map.items() if target == item["record_id"]])
    kept.sort(key=lambda x: x["record_id"])
    write_jsonl(root / "raw/deduped.jsonl", kept)
    write_json(root / "raw/duplicate_map.json", duplicate_map)
    update_status(root, state="deduped", unique_count=len(kept), duplicate_count=len(duplicate_map))
    print(json.dumps({"unique": len(kept), "duplicates": len(duplicate_map)}, ensure_ascii=False))


def analysis_instruction() -> str:
    return (
        "你是建筑、景观与城市设计竞赛分析图研究员。只根据图像和可见元数据输出符合core.schema.json的JSON。"
        "主类只能为九类之一或不相关；允许次级多标签。不得猜测图中没有证据的地点、尺寸、比例、年代、功能或统计数据。"
        "识别底图、投影、尺度、图表内容、分析逻辑、排版、色板、线型符号、文字系统和图面表现。"
        "建筑景观相关度低于0.65时status设为rejected或needs_review。不要输出Markdown。"
    )


def cmd_core_queue(args: argparse.Namespace) -> None:
    root = Path(args.root)
    rows = read_jsonl(root / "raw/deduped.jsonl")
    existing = {p.stem for p in (root / "records/core").glob("*.json")}
    queue = []
    for item in rows:
        rid = item["record_id"]
        if rid in existing:
            continue
        queue.append({
            "record_id": rid,
            "thumbnail_path": item["asset"]["thumbnail_path"],
            "source_record": {
                "platform": "pinterest",
                "pin_id": item.get("pin_id"),
                "pin_url": item["pin_url"],
                "outbound_url": item.get("outbound_url"),
                "title": item.get("title"),
                "visible_description": item.get("visible_description"),
                "search_url": item.get("search_url") or SEARCH_URL,
                "collected_at": item.get("collected_at") or now_iso(),
            },
            "asset_record": {key: item["asset"][key] for key in ["thumbnail_path", "sha256", "phash64", "width", "height"]},
            "visible_metadata": {"title": item.get("title"), "description": item.get("visible_description")},
            "instruction": analysis_instruction() + " 必须原样复制source_record与asset_record，并使用schema_version=1.0.0、quality.human_review_status=pending。",
            "schema_path": str((Path(__file__).resolve().parents[1] / "schemas/core.schema.json")),
        })
        if args.limit and len(queue) >= args.limit:
            break
    write_jsonl(root / "raw/core_queue.jsonl", queue)
    update_status(root, state="core_queue_ready", core_queue_count=len(queue))
    print(json.dumps({"queued": len(queue)}, ensure_ascii=False))


def cmd_deep_queue(args: argparse.Namespace) -> None:
    root = Path(args.root)
    representatives = read_jsonl(root / "clusters/representatives.jsonl")
    queue = []
    for item in representatives:
        rid = item["record_id"]
        core_path = root / "records/core" / f"{rid}.json"
        if not core_path.exists():
            continue
        asset = read_json(core_path)["asset"]
        full_path = root / "records/deep" / f"{rid}.full.json"
        style_path = root / "records/deep" / f"{rid}.style.json"
        if not full_path.exists():
            queue.append({
                "record_id": rid,
                "mode": "full",
                "thumbnail_path": asset["thumbnail_path"],
                "core_record": read_json(core_path),
                "schema_path": str(project_root() / "schemas/full_reverse.schema.json"),
                "instruction": "全面反推该竞赛分析图。必须且只能输出符合full_reverse.schema.json的合法JSON；只写图像证据，不虚构地点、尺寸、比例、年代、功能或统计数据。"
            })
        if not style_path.exists():
            queue.append({
                "record_id": rid,
                "mode": "style",
                "thumbnail_path": asset["thumbnail_path"],
                "core_record": read_json(core_path),
                "schema_path": str(project_root() / "schemas/style_reverse.schema.json"),
                "instruction": "忽略具体项目内容，仅做视觉风格逆向。必须且只能输出符合style_reverse.schema.json的合法JSON，并给出10至15个英文风格标签。"
            })
    write_jsonl(root / "raw/deep_queue.jsonl", queue)
    update_status(root, state="deep_queue_ready", deep_queue_count=len(queue))
    print(json.dumps({"queued": len(queue)}, ensure_ascii=False))


def cmd_import_deep(args: argparse.Namespace) -> None:
    root = Path(args.root)
    imported = failed = 0
    failures = []
    for row in read_jsonl(Path(args.input)):
        rid = row.get("record_id")
        mode = row.get("mode")
        result = row.get("result")
        if not rid or mode not in {"full", "style"} or not isinstance(result, dict):
            failures.append({"record_id": rid, "errors": ["record_id, mode and result are required"]})
            failed += 1
            continue
        schema_name = "full_reverse.schema.json" if mode == "full" else "style_reverse.schema.json"
        errors = validate_one(result, schema_name)
        if errors:
            failures.append({"record_id": rid, "mode": mode, "errors": errors})
            failed += 1
            continue
        write_json(root / "records/deep" / f"{rid}.{mode}.json", result)
        imported += 1
    write_jsonl(root / "raw/deep_import_failures.jsonl", failures)
    update_status(root, state="deep_analysis_imported", deep_record_count=len(list((root / "records/deep").glob("*.json"))), deep_import_failures=failed)
    print(json.dumps({"imported": imported, "failed": failed}, ensure_ascii=False))


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def validator(name: str) -> Draft202012Validator:
    schema = read_json(project_root() / "schemas" / name)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_one(value: dict[str, Any], schema_name: str) -> list[str]:
    errors = sorted(validator(schema_name).iter_errors(value), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '$'}: {e.message}" for e in errors]


def cmd_import_analysis(args: argparse.Namespace) -> None:
    root = Path(args.root)
    imported = failed = 0
    failures = []
    for row in read_jsonl(Path(args.input)):
        rid = row.get("record_id")
        result = row.get("result", row)
        if not rid:
            rid = result.get("record_id")
        if not rid:
            failures.append({"record_id": None, "errors": ["missing record_id"]})
            failed += 1
            continue
        result["record_id"] = rid
        errors = validate_one(result, "core.schema.json")
        if errors:
            failures.append({"record_id": rid, "errors": errors})
            failed += 1
            continue
        write_json(root / "records/core" / f"{rid}.json", result)
        imported += 1
    write_jsonl(root / "raw/analysis_import_failures.jsonl", failures)
    active_ids = current_unique_ids(root)
    all_records = [read_json(path) for path in (root / "records/core").glob("*.json") if not active_ids or path.stem in active_ids]
    accepted_count = sum(1 for item in all_records if item["classification"]["status"] == "accepted")
    rejected_count = sum(1 for item in all_records if item["classification"]["status"] == "rejected")
    review_count = sum(1 for item in all_records if item["classification"]["status"] == "needs_review")
    update_status(
        root,
        state="core_analysis_imported",
        core_record_count=len(all_records),
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        needs_review_count=review_count,
        analysis_import_failures=failed,
    )
    print(json.dumps({"imported": imported, "failed": failed}, ensure_ascii=False))


def image_features(path: str) -> np.ndarray:
    with Image.open(path) as image:
        image = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
        hsv = np.asarray(image.convert("HSV"), dtype=np.float32)
        hist = []
        for channel in range(3):
            values, _ = np.histogram(hsv[:, :, channel], bins=16, range=(0, 256), density=True)
            hist.extend(values.tolist())
        gray = np.asarray(image.convert("L").resize((16, 16)), dtype=np.float32).reshape(-1) / 255.0
        vector = np.asarray(hist + gray.tolist(), dtype=np.float32)
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector


def cmd_cluster(args: argparse.Namespace) -> None:
    root = Path(args.root)
    active_ids = current_unique_ids(root)
    core = [read_json(p) for p in sorted((root / "records/core").glob("*.json")) if not active_ids or p.stem in active_ids]
    core = [x for x in core if x and x["classification"]["status"] != "rejected"]
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in core:
        by_category[row["classification"]["primary_category"]].append(row)
    assets = {x["record_id"]: x for x in read_jsonl(root / "raw/assets.jsonl")}
    representatives: list[dict[str, Any]] = []
    try:
        from sklearn.cluster import MiniBatchKMeans
    except ImportError:
        MiniBatchKMeans = None
    budget_per_category = max(1, args.max_representatives // max(1, len(by_category)))
    for category, rows in sorted(by_category.items()):
        usable = [r for r in rows if r["record_id"] in assets]
        if not usable:
            continue
        features = np.vstack([image_features(assets[r["record_id"]]["thumbnail_path"]) for r in usable])
        cluster_count = min(budget_per_category, max(1, round(math.sqrt(len(usable)))))
        if MiniBatchKMeans and len(usable) > cluster_count:
            model = MiniBatchKMeans(n_clusters=cluster_count, random_state=42, n_init="auto")
            labels = model.fit_predict(features)
            for label in range(cluster_count):
                indices = np.where(labels == label)[0]
                if len(indices) == 0:
                    continue
                center = model.cluster_centers_[label]
                best = min(indices, key=lambda i: float(np.linalg.norm(features[i] - center)))
                representatives.append({"record_id": usable[int(best)]["record_id"], "primary_category": category, "cluster_id": f"{category}-{label:03d}", "reason": "cluster_medoid"})
        else:
            for label, row in enumerate(usable[:cluster_count]):
                representatives.append({"record_id": row["record_id"], "primary_category": category, "cluster_id": f"{category}-{label:03d}", "reason": "fallback_representative"})
        low_conf = sorted(usable, key=lambda r: r["classification"]["confidence"])
        for row in low_conf[: min(3, len(low_conf))]:
            if not any(x["record_id"] == row["record_id"] for x in representatives):
                representatives.append({"record_id": row["record_id"], "primary_category": category, "cluster_id": f"{category}-review", "reason": "low_confidence"})
    representatives = representatives[: args.max_representatives]
    write_jsonl(root / "clusters/representatives.jsonl", representatives)
    update_status(root, state="representatives_selected", representative_count=len(representatives), last_error=None)
    print(json.dumps({"representatives": len(representatives)}, ensure_ascii=False))


def prompt_pack(row: dict[str, Any]) -> dict[str, Any]:
    cls = row["classification"]
    ana = row["analysis"]
    universal = {
        "language": "zh-CN",
        "diagram_type": cls["primary_category"],
        "drawing_subtype": ana.get("drawing_subtype", "待确认"),
        "drawing_forms": ana.get("drawing_forms", []),
        "secondary_categories": cls["secondary_categories"],
        "input_base": ana["base_map_type"],
        "preserve": ["输入图中可见的场地边界、道路、建筑比例和空间关系"],
        "analysis_goal": ana["chart_content"],
        "analysis_logic": ana["analysis_logic"],
        "fidelity_level": ana.get("technical_execution", {}).get("fidelity_level", "待3-7轮问询确认"),
        "image_detail_system": ana.get("image_detail_system", {"primary_level": "待确认"}),
        "figure_ground_system": ana.get("figure_ground_system", {"ground_carrier": "待确认", "figure_subject": "待确认"}),
        "projection": ana["projection"],
        "layout": ana["layout"],
        "color_system": ana["color_style"],
        "line_and_symbol_system": ana["line_symbols"],
        "art_style_system": ana.get("art_style_system", {"medium": ["待确认"], "atmosphere": "待确认"}),
        "technical_execution": ana.get("technical_execution", {}),
        "text_system": {**ana["text_system"], "long_chinese_text": "reserve_space_for_deterministic_svg_or_pptx_overlay"},
        "graphic_expression": ana["graphic_expression"],
        "negative_constraints": [
            "不得改变输入基底中的真实实体关系",
            "不得虚构道路、尺寸、比例、年代、功能或统计数据",
            "不得生成不可读的长段中文",
            "不得引入色板和线型系统之外的视觉语言"
        ],
        "output": {"background": "clean", "resolution": "print-ready", "editable_chinese_overlay": True}
    }
    summary = f"{cls['primary_category']}竞赛分析图；{ana['projection']}；{ana['base_map_type']}；保持输入关系；中文后期排版"
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": row["record_id"],
        "universal_json_prompt": universal,
        "nano_banana_gemini": {"mode": "structured_json", "prompt": universal},
        "gpt_image": {
            "prompt": f"基于参考图制作{summary}。先生成无长段文字版本，保留中文标题、编号与说明区的留白。",
            "preserve": universal["preserve"],
            "negative_constraints": universal["negative_constraints"]
        },
        "midjourney": {
            "prompt": f"architectural competition analytical diagram, {cls['primary_category']}, {ana['projection']}, clean academic layout, restrained palette, precise vector linework, Chinese label placeholders, white space, no fabricated site data",
            "parameters": "--ar 4:3 --stylize 75 --chaos 0"
        }
    }


def cmd_compile_prompts(args: argparse.Namespace) -> None:
    root = Path(args.root)
    active_ids = current_unique_ids(root)
    count = 0
    for path in sorted((root / "records/core").glob("*.json")):
        if active_ids and path.stem not in active_ids:
            continue
        row = read_json(path)
        if row["classification"]["status"] == "rejected":
            continue
        write_json(root / "prompts" / f"{row['record_id']}.json", prompt_pack(row))
        count += 1
    update_status(root, state="prompts_compiled", prompt_count=count)
    print(json.dumps({"compiled": count}, ensure_ascii=False))


def cmd_validate(args: argparse.Namespace) -> None:
    root = Path(args.root)
    checks = [
        (root / "records/core", "core.schema.json"),
        (root / "records/deep", None),
    ]
    failures = []
    checked = 0
    for directory, schema_name in checks:
        for path in sorted(directory.glob("*.json")):
            value = read_json(path)
            selected = schema_name
            if selected is None:
                if path.name.endswith(".full.json"):
                    selected = "full_reverse.schema.json"
                elif path.name.endswith(".style.json"):
                    selected = "style_reverse.schema.json"
                else:
                    continue
            checked += 1
            errors = validate_one(value, selected)
            if errors:
                failures.append({"file": str(path), "schema": selected, "errors": errors})
    write_json(root / "reports/validation.json", {"checked": checked, "failed": len(failures), "failures": failures})
    update_status(root, validation_checked=checked, validation_failed=len(failures), state="validation_failed" if failures else "validated")
    print(json.dumps({"checked": checked, "failed": len(failures)}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


def cmd_report(args: argparse.Namespace) -> None:
    root = Path(args.root)
    status = read_json(status_path(root), {})
    local_status = read_json(root / "local_import_status.json", {}) or {}
    unified_count = len(read_jsonl(root / "raw/unified_deduped.jsonl"))
    active_ids = current_unique_ids(root)
    records = [read_json(p) for p in sorted((root / "records/core").glob("*.json")) if not active_ids or p.stem in active_ids]
    category_counts = Counter(r["classification"]["primary_category"] for r in records)
    status_counts = Counter(r["classification"]["status"] for r in records)
    update_status(
        root,
        active_core_count=len(records),
        unified_unique_count=unified_count or status.get("unique_count", 0),
        local_source_record_count=local_status.get("local_source_records", 0),
        local_import_failure_count=local_status.get("failures", 0),
        accepted_count=status_counts.get("accepted", 0),
        rejected_count=status_counts.get("rejected", 0),
        needs_review_count=status_counts.get("needs_review", 0),
    )
    status = read_json(status_path(root), {})
    lines = [
        "# Architecture Mapping Dataset Report", "",
        f"- Generated: {now_iso()}",
        f"- Raw Pins: {status.get('raw_count', 0)}",
        f"- Pinterest unique thumbnails: {status.get('unique_count', 0)}",
        f"- Local source records: {local_status.get('local_source_records', 0)}",
        f"- Unified unique records: {unified_count or status.get('unique_count', 0)}",
        f"- Skipped local failures: {local_status.get('failures', 0)}",
        f"- Active core records: {len(records)}", "",
        "## Status", "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(status_counts.items()))
    lines.extend(["", "## Primary categories", ""])
    lines.extend(f"- {key}: {value}" for key, value in category_counts.most_common())
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "reports/summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    write_json(root / "reports/summary.json", {"status": status, "record_status": status_counts, "primary_categories": category_counts})
    print(root / "reports/summary.md")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    for name, handler in [("init", cmd_init), ("validate", cmd_validate), ("report", cmd_report), ("compile-prompts", cmd_compile_prompts)]:
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        p.set_defaults(handler=handler)
    p = sub.add_parser("ingest")
    p.add_argument("--root", required=True); p.add_argument("--input", required=True); p.set_defaults(handler=cmd_ingest)
    p = sub.add_parser("thumbnails")
    p.add_argument("--root", required=True); p.add_argument("--timeout", type=int, default=30); p.set_defaults(handler=cmd_thumbnails)
    p = sub.add_parser("dedupe")
    p.add_argument("--root", required=True); p.add_argument("--phash-distance", type=int, default=6); p.set_defaults(handler=cmd_dedupe)
    p = sub.add_parser("core-queue")
    p.add_argument("--root", required=True); p.add_argument("--limit", type=int, default=0); p.set_defaults(handler=cmd_core_queue)
    p = sub.add_parser("import-analysis")
    p.add_argument("--root", required=True); p.add_argument("--input", required=True); p.set_defaults(handler=cmd_import_analysis)
    p = sub.add_parser("deep-queue")
    p.add_argument("--root", required=True); p.set_defaults(handler=cmd_deep_queue)
    p = sub.add_parser("import-deep")
    p.add_argument("--root", required=True); p.add_argument("--input", required=True); p.set_defaults(handler=cmd_import_deep)
    p = sub.add_parser("cluster")
    p.add_argument("--root", required=True); p.add_argument("--max-representatives", type=int, default=180); p.set_defaults(handler=cmd_cluster)
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        args.handler(args)
    except Exception as exc:
        root = Path(args.root) if getattr(args, "root", None) else None
        if root:
            ensure_dirs(root)
            update_status(root, state="error", last_error=str(exc))
        print(f"ERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
