#!/usr/bin/env python3
"""Retry truncated local archive images without modifying their source files."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageFile


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
ImageFile.LOAD_TRUNCATED_IMAGES = True


def load_importer():
    spec = importlib.util.spec_from_file_location("local_importer", ROOT / "scripts/import_local_archives.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    importer = load_importer()
    failure_path = DATASET / "raw/local_import_failures.jsonl"
    source_path = DATASET / "raw/local_sources.jsonl"
    failures = importer.read_jsonl(failure_path)
    sources = {row["record_id"]: row for row in importer.read_jsonl(source_path)}
    roots = dict(importer.ARCHIVES)
    remaining = []
    recovered = 0
    for failure in failures:
        archive = failure["archive_name"]
        path = Path(failure["source_path"])
        archive_root = roots[archive]
        try:
            relative = str(path.relative_to(archive_root))
            rid = importer.stable_id(archive, relative)
            with Image.open(path) as opened:
                image = importer.normalize_image(opened, 1600)
                destination = DATASET / "thumbnails/local" / archive / f"{rid}.jpg"
                sources[rid] = importer.source_record(
                    archive, archive_root, path, None, None,
                    importer.save_asset(image, destination),
                )
            recovered += 1
        except Exception as exc:
            remaining.append({**failure, "recovery_error": f"{type(exc).__name__}: {exc}"})
    rows = sorted(sources.values(), key=lambda row: row["record_id"])
    importer.write_jsonl(source_path, rows)
    importer.write_jsonl(failure_path, remaining)
    unified, duplicate_map = importer.unified_dedupe(DATASET, rows, 6)
    core_count = importer.write_local_core(DATASET, unified)
    status = {
        "state": "complete", "local_source_records": len(rows),
        "unified_unique_records": len(unified), "duplicate_count": len(duplicate_map),
        "local_core_records": core_count, "failures": len(remaining),
        "recovered_truncated_images": recovered, "updated_at": importer.now_iso(),
    }
    importer.write_json(DATASET / "local_import_status.json", status)
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
