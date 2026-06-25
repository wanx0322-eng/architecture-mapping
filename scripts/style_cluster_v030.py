#!/usr/bin/env python3
"""Cluster Pinterest thumbnails into eight reproducible visual style groups."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from sklearn.cluster import MiniBatchKMeans


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline)

PROFILE_IDS = [
    "minimal_grey_competition",
    "ecological_layered_wash",
    "desaturated_paper_collage",
    "precision_vector_analysis",
    "layered_landscape_axonometric",
    "diagnostic_heat_overlay",
    "hand_drawn_mixed_media",
    "dark_high_contrast_narrative",
]


def features(path: str) -> np.ndarray:
    with Image.open(path) as image:
        rgb = image.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR)
        hsv = np.asarray(rgb.convert("HSV"), dtype=np.float32)
        gray = np.asarray(rgb.convert("L"), dtype=np.float32) / 255.0
        edges = np.asarray(rgb.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0
        color_hist = []
        for channel in range(3):
            values, _ = np.histogram(hsv[:, :, channel], bins=12, range=(0, 256), density=True)
            color_hist.extend(values.tolist())
        summary = [
            float(gray.mean()), float(gray.std()),
            float((hsv[:, :, 1] / 255.0).mean()),
            float((hsv[:, :, 2] / 255.0).mean()),
            float(edges.mean()), float((gray > 0.92).mean()),
        ]
        vector = np.asarray(color_hist + summary, dtype=np.float32)
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector


def main() -> None:
    dataset = Path(__file__).resolve().parents[2] / "architecture-mapping-zh-runtime"
    rows = pipeline.read_jsonl(dataset / "raw/deduped.jsonl")
    matrix = np.vstack([features(row["asset"]["thumbnail_path"]) for row in rows])
    model = MiniBatchKMeans(n_clusters=8, random_state=42, n_init=10, batch_size=256)
    labels = model.fit_predict(matrix)
    cluster_stats = []
    assignments = []
    for label in range(8):
        indices = np.where(labels == label)[0]
        center = model.cluster_centers_[label]
        ranked = sorted(indices, key=lambda index: float(np.linalg.norm(matrix[index] - center)))
        representatives = [rows[int(index)]["record_id"] for index in ranked[:8]]
        cluster_stats.append({
            "label": label,
            "count": int(len(indices)),
            "brightness": float(matrix[indices, -6].mean()),
            "saturation": float(matrix[indices, -4].mean()),
            "edge_density": float(matrix[indices, -2].mean()),
            "representatives": representatives,
        })
    order = sorted(cluster_stats, key=lambda item: (item["brightness"], item["saturation"], item["edge_density"]))
    label_to_profile = {item["label"]: PROFILE_IDS[index] for index, item in enumerate(order)}
    for row, label in zip(rows, labels):
        assignments.append({"record_id": row["record_id"], "style_cluster": label_to_profile[int(label)]})
    profiles = json.loads((ROOT / "assets/pinterest_style_profiles.json").read_text(encoding="utf-8"))
    output_clusters = {}
    for item in cluster_stats:
        profile_id = label_to_profile[item["label"]]
        output_clusters[profile_id] = {
            **profiles["clusters"][profile_id],
            "sample_count": item["count"],
            "representative_record_ids": item["representatives"],
            "feature_summary": {
                "brightness": round(item["brightness"], 5),
                "saturation": round(item["saturation"], 5),
                "edge_density": round(item["edge_density"], 5),
            },
            "confidence": 0.75,
        }
    pipeline.write_json(dataset / "clusters/pinterest_style_clusters.json", {
        "schema_version": "1.0.0",
        "method": "MiniBatchKMeans over color histogram, brightness, saturation, white-space and edge-density features",
        "random_state": 42,
        "sample_count": len(rows),
        "clusters": output_clusters,
    })
    pipeline.write_jsonl(dataset / "clusters/pinterest_style_assignments.jsonl", assignments)
    pipeline.write_json(dataset / "reports/representatives.json", {
        key: value["representative_record_ids"] for key, value in output_clusters.items()
    })
    print(json.dumps({"samples": len(rows), "clusters": {key: value["sample_count"] for key, value in output_clusters.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
