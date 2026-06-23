#!/usr/bin/env python3
"""Import local competition archives as resumable thumbnail/page records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import imagehash  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402


Image.MAX_IMAGE_PIXELS = None
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
PDF_EXTENSION = ".pdf"
SCHEMA_VERSION = "1.0.0"


ARCHIVES = [
    ("ASLA_2004_2024", Path(r"D:\新建文件夹\01-ASLA合集（2004-2024）")),
    ("IFLA_2016_2024", Path(r"D:\新建文件夹\03-IFLA合集（2016-2024）")),
    ("S462_ARCH_COMPETITION", Path(r"D:\新建文件夹\s462建筑竞赛排版")),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def stable_id(archive: str, relative_path: str, page: int | None = None) -> str:
    seed = f"{archive}|{relative_path.casefold()}|{page or 0}"
    return "local-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def year_from_path(path: str) -> str | None:
    values = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", path)
    return values[-1] if values else None


def normalize_image(image: Image.Image, max_edge: int) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if getattr(image, "is_animated", False):
        image.seek(0)
    if image.mode not in {"RGB", "L"}:
        background = Image.new("RGB", image.size, "white")
        if "A" in image.getbands():
            background.paste(image.convert("RGBA"), mask=image.convert("RGBA").getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
    else:
        image = image.convert("RGB")
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return image


def save_asset(image: Image.Image, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "JPEG", quality=88, optimize=True, progressive=True)
    payload = destination.read_bytes()
    return {
        "thumbnail_path": str(destination.resolve()),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "phash64": str(imagehash.phash(image, hash_size=8)),
        "width": image.width,
        "height": image.height,
    }


def source_record(archive: str, root: Path, path: Path, page: int | None, total_pages: int | None, asset: dict) -> dict:
    relative = str(path.relative_to(root))
    rid = stable_id(archive, relative, page)
    return {
        "record_id": rid,
        "platform": "local_archive",
        "archive_name": archive,
        "source_path": str(path.resolve()),
        "relative_path": relative,
        "source_type": "pdf_page" if page else "image",
        "pdf_page": page,
        "total_pages": total_pages,
        "title": path.stem,
        "year_hint": year_from_path(relative),
        "collected_at": now_iso(),
        "asset": {"record_id": rid, **asset},
    }


def enumerate_media(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS | {PDF_EXTENSION}),
        key=lambda path: str(path).casefold(),
    )


def import_archives(dataset: Path, max_edge: int, archives: list[tuple[str, Path]] | None = None) -> tuple[list[dict], list[dict]]:
    source_path = dataset / "raw/local_sources.jsonl"
    failures_path = dataset / "raw/local_import_failures.jsonl"
    existing = {row["record_id"]: row for row in read_jsonl(source_path)}
    failures = read_jsonl(failures_path)
    processed_files = 0

    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None

    for archive, archive_root in (archives or ARCHIVES):
        if not archive_root.exists():
            failures.append({"archive_name": archive, "source_path": str(archive_root), "error": "archive root missing"})
            continue
        for path in enumerate_media(archive_root):
            processed_files += 1
            relative = str(path.relative_to(archive_root))
            try:
                if path.suffix.lower() == PDF_EXTENSION:
                    if fitz is None:
                        raise RuntimeError("PyMuPDF is required to render PDF pages")
                    with fitz.open(path) as document:
                        total = document.page_count
                        for page_index in range(total):
                            page_number = page_index + 1
                            rid = stable_id(archive, relative, page_number)
                            old = existing.get(rid)
                            if old and Path(old["asset"]["thumbnail_path"]).exists():
                                continue
                            page = document.load_page(page_index)
                            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                            image = normalize_image(image, max_edge)
                            destination = dataset / "thumbnails/local" / archive / f"{rid}.jpg"
                            existing[rid] = source_record(archive, archive_root, path, page_number, total, save_asset(image, destination))
                else:
                    rid = stable_id(archive, relative)
                    old = existing.get(rid)
                    if old and Path(old["asset"]["thumbnail_path"]).exists():
                        continue
                    with Image.open(path) as opened:
                        image = normalize_image(opened, max_edge)
                        destination = dataset / "thumbnails/local" / archive / f"{rid}.jpg"
                        existing[rid] = source_record(archive, archive_root, path, None, None, save_asset(image, destination))
            except Exception as exc:
                failures.append({"archive_name": archive, "source_path": str(path), "error": f"{type(exc).__name__}: {exc}"})
            if processed_files % 100 == 0:
                write_jsonl(source_path, sorted(existing.values(), key=lambda row: row["record_id"]))
                write_jsonl(failures_path, failures)
                write_json(dataset / "local_import_status.json", {
                    "state": "importing", "processed_files": processed_files,
                    "local_records": len(existing), "failures": len(failures), "updated_at": now_iso(),
                })

    rows = sorted(existing.values(), key=lambda row: row["record_id"])
    write_jsonl(source_path, rows)
    write_jsonl(failures_path, failures)
    return rows, failures


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def phash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def near_band_values(value: int) -> list[int]:
    return [value] + [value ^ (1 << bit) for bit in range(16)]


def unified_dedupe(dataset: Path, local_rows: list[dict], threshold: int) -> tuple[list[dict], dict[str, str]]:
    pinterest = read_jsonl(dataset / "raw/deduped.jsonl")
    rows: list[dict] = []
    for item in pinterest:
        rows.append({
            "record_id": item["record_id"], "platform": "pinterest", "source": item,
            "asset": item["asset"],
        })
    for item in local_rows:
        rows.append({
            "record_id": item["record_id"], "platform": "local_archive", "source": item,
            "asset": item["asset"],
        })

    uf = UnionFind(len(rows))
    exact: dict[str, int] = {}
    bands: list[dict[int, list[int]]] = [defaultdict(list) for _ in range(4)]
    for index, row in enumerate(rows):
        asset = row["asset"]
        sha = asset["sha256"]
        if sha in exact:
            uf.union(index, exact[sha])
        else:
            exact[sha] = index
        phash = int(asset["phash64"], 16)
        candidates: set[int] = set()
        for band_index in range(4):
            band_value = (phash >> (band_index * 16)) & 0xFFFF
            for neighbor in near_band_values(band_value):
                candidates.update(bands[band_index].get(neighbor, []))
        for candidate in candidates:
            if phash_distance(asset["phash64"], rows[candidate]["asset"]["phash64"]) <= threshold:
                uf.union(index, candidate)
        for band_index in range(4):
            band_value = (phash >> (band_index * 16)) & 0xFFFF
            bands[band_index][band_value].append(index)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(rows)):
        groups[uf.find(index)].append(index)
    keepers: list[dict] = []
    duplicate_map: dict[str, str] = {}
    for indices in groups.values():
        best = max(indices, key=lambda idx: (
            rows[idx]["asset"]["width"] * rows[idx]["asset"]["height"],
            1 if rows[idx]["platform"] == "local_archive" else 0,
        ))
        keeper = rows[best]
        duplicates = []
        for index in indices:
            if index == best:
                continue
            duplicate_map[rows[index]["record_id"]] = keeper["record_id"]
            duplicates.append({"record_id": rows[index]["record_id"], "platform": rows[index]["platform"]})
        keepers.append({**keeper, "duplicate_sources": duplicates})
    keepers.sort(key=lambda row: row["record_id"])
    write_jsonl(dataset / "raw/unified_deduped.jsonl", keepers)
    write_json(dataset / "raw/unified_duplicate_map.json", duplicate_map)
    local_keepers = [row for row in keepers if row["platform"] == "local_archive"]
    write_jsonl(dataset / "raw/local_deduped.jsonl", local_keepers)
    return keepers, duplicate_map


def infer_primary(relative_path: str) -> str:
    text = relative_path.casefold()
    if any(word in text for word in ["heritage", "historic", "history", "文化", "遗产", "考古"]):
        return "历史文化"
    if any(word in text for word in ["mapping", "masterplan", "planning", "规划", "区位"]):
        return "场地区位"
    if any(word in text for word in ["render", "效果", "perspective"]):
        return "效果图"
    return "现状问题"


def local_core(row: dict) -> dict:
    source = row["source"]
    primary = infer_primary(source["relative_path"])
    is_qr = "二维码" in source["relative_path"] or "qrcode" in source["relative_path"].casefold()
    status = "rejected" if is_qr else "needs_review"
    if is_qr:
        primary = "不相关"
    asset = row["asset"]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": row["record_id"],
        "source": {
            "platform": "local_archive", "archive_name": source["archive_name"],
            "source_path": source["source_path"], "relative_path": source["relative_path"],
            "source_type": source["source_type"], "pdf_page": source.get("pdf_page"),
            "total_pages": source.get("total_pages"), "title": source.get("title"),
            "collected_at": source["collected_at"],
        },
        "asset": {key: asset[key] for key in ["thumbnail_path", "sha256", "phash64", "width", "height"]},
        "classification": {
            "status": status, "primary_category": primary,
            "secondary_categories": [source["archive_name"], "本地竞赛合集", "PDF页面" if source["source_type"] == "pdf_page" else "图片"],
            "relevance_score": 0.05 if is_qr else 0.88, "confidence": 0.98 if is_qr else 0.45,
            "evidence": ["来源目录为用户指定的竞赛合集", f"文件类型：{source['source_type']}", "尚未完成逐图九类视觉复核"],
        },
        "analysis": {
            "base_map_type": "待视觉复核", "projection": "待视觉复核", "scale": "待视觉复核",
            "chart_content": ["竞赛图纸或项目图像", "来源路径可追溯"],
            "framework": "本记录已完成文件遍历、缩略图生成和来源登记；视觉语义字段等待后续批量复核",
            "map_description": "不依据文件名补造图中地点、尺寸、比例、功能或数据",
            "analysis_logic": ["读取本地文件", "规范化缩略图或PDF页面", "哈希去重", "等待视觉分类"],
            "layout": {"type": "待视觉复核", "information_density": "未知"},
            "color_style": {"description": "待视觉复核"},
            "line_symbols": {"lines": [], "symbols": []},
            "text_system": {"detected_language": "未知", "hierarchy": []},
            "graphic_expression": {"style": "竞赛合集来源，待视觉复核", "texture": "未知"},
            "unsupported_claims": ["具体地点", "尺寸", "比例", "年代", "功能", "统计数据"],
        },
        "quality": {
            "human_review_status": "rejected" if is_qr else "recheck",
            "warnings": ["本地合集已遍历并入库，但该条尚未进行逐图视觉语义复核"],
            "duplicate_of": None,
        },
    }


def write_local_core(dataset: Path, unified_rows: list[dict]) -> int:
    count = 0
    core_dir = dataset / "records/core"
    core_dir.mkdir(parents=True, exist_ok=True)
    for row in unified_rows:
        if row["platform"] != "local_archive":
            continue
        write_json(core_dir / f"{row['record_id']}.json", local_core(row))
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(ROOT / "dataset"))
    parser.add_argument("--max-edge", type=int, default=1600)
    parser.add_argument("--phash-distance", type=int, default=6)
    parser.add_argument(
        "--archive", action="append", default=[], metavar="NAME=PATH",
        help="Local archive mapping; repeat for multiple roots. Defaults to the configured workspace archives.",
    )
    args = parser.parse_args()
    dataset = Path(args.dataset)
    archives = []
    for value in args.archive:
        if "=" not in value:
            parser.error(f"invalid --archive value: {value!r}; expected NAME=PATH")
        name, path = value.split("=", 1)
        archives.append((name.strip(), Path(path.strip())))
    rows, failures = import_archives(dataset, args.max_edge, archives or None)
    unified, duplicate_map = unified_dedupe(dataset, rows, args.phash_distance)
    core_count = write_local_core(dataset, unified)
    summary = {
        "state": "complete", "local_source_records": len(rows),
        "unified_unique_records": len(unified), "duplicate_count": len(duplicate_map),
        "local_core_records": core_count, "failures": len(failures), "updated_at": now_iso(),
    }
    write_json(dataset / "local_import_status.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
