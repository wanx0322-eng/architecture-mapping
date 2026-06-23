#!/usr/bin/env python3
"""Deterministic expert routing and MoE quality arbitration."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "assets/expert_registry.json").read_text(encoding="utf-8"))
EXPERT_IDS = {item["id"] for item in REGISTRY["experts"]}
WEIGHTS = REGISTRY["quality_weights"]


ROUTES = {
    "classification": ["analysis-taxonomy", "knowledge-retrieval", "figure-ground-graphics", "programmatic-validator", "quality-critic"],
    "reverse_engineering": ["evidence-geometry", "analysis-taxonomy", "knowledge-retrieval", "figure-ground-graphics", "style-layout", "programmatic-validator", "quality-critic"],
    "mapping": ["brief-intake", "evidence-geometry", "analysis-taxonomy", "knowledge-retrieval", "figure-ground-graphics", "style-layout", "programmatic-validator", "model-production", "quality-critic"],
    "image_generation": ["brief-intake", "evidence-geometry", "analysis-taxonomy", "knowledge-retrieval", "figure-ground-graphics", "style-layout", "programmatic-validator", "model-production", "quality-critic"],
    "image_edit": ["brief-intake", "evidence-geometry", "knowledge-retrieval", "figure-ground-graphics", "style-layout", "programmatic-validator", "model-production", "quality-critic"],
    "board_layout": ["brief-intake", "analysis-taxonomy", "knowledge-retrieval", "figure-ground-graphics", "style-layout", "programmatic-validator", "model-production", "quality-critic"],
    "final_prompt": ["brief-intake", "evidence-geometry", "analysis-taxonomy", "knowledge-retrieval", "figure-ground-graphics", "style-layout", "programmatic-validator", "model-production", "quality-critic"],
    "dataset": ["evidence-geometry", "analysis-taxonomy", "programmatic-validator", "quality-critic"],
    "evolution": ["evolution-governance", "programmatic-validator", "quality-critic"],
}
PRODUCTION_TYPES = {"mapping", "image_generation", "image_edit", "board_layout", "final_prompt"}


def route(task_type: str, rounds_completed: int) -> dict:
    experts = ROUTES.get(task_type, ["analysis-taxonomy", "quality-critic"])
    blocked = task_type in PRODUCTION_TYPES and rounds_completed < 3
    return {
        "task_type": task_type,
        "activated_experts": experts,
        "rounds_completed": rounds_completed,
        "blocked": blocked,
        "block_reason": "Production requires at least 3 completed user interview rounds." if blocked else None,
        "next_expert": "brief-intake" if blocked else experts[0],
    }


def weighted_total(scores: dict) -> float:
    return round(sum(float(scores.get(key, 0)) * weight / 100 for key, weight in WEIGHTS.items()), 2)


def arbitrate(payload: dict) -> dict:
    candidates = []
    for item in payload.get("candidates", []):
        scores = item.get("scores", {})
        total = weighted_total(scores)
        candidates.append({
            "id": item["id"], "scores": scores, "total": total,
            "strengths": item.get("strengths", []), "risks": item.get("risks", []),
            "vetoes": item.get("vetoes", []),
        })
    eligible = [item for item in candidates if not item["vetoes"]]
    eligible.sort(key=lambda item: item["total"], reverse=True)
    minimum = REGISTRY["minimum_delivery_score"]
    delta_limit = REGISTRY["user_choice_score_delta"]
    if not eligible:
        decision, selected, ready, ask = "block", None, False, False
        rationale = "All candidates violate at least one hard constraint."
        quality = 0
    elif eligible[0]["total"] < minimum:
        decision, selected, ready, ask = "revise", eligible[0]["id"], False, False
        rationale = f"Best candidate scores below delivery threshold {minimum}."
        quality = eligible[0]["total"]
    elif len(eligible) > 1 and eligible[0]["total"] - eligible[1]["total"] < delta_limit:
        decision, selected, ready, ask = "ask_user", None, False, True
        rationale = f"Top candidates differ by less than {delta_limit} points; user tradeoff is required."
        quality = eligible[0]["total"]
    else:
        decision, selected, ready, ask = "select", eligible[0]["id"], True, False
        rationale = "Highest-scoring candidate passes all hard constraints and the delivery threshold."
        quality = eligible[0]["total"]
    all_vetoes = [f"{item['id']}: {veto}" for item in candidates for veto in item["vetoes"]]
    clean_candidates = [{key: value for key, value in item.items() if key != "vetoes"} for item in candidates]
    return {
        "schema_version": "1.0.0", "task_id": payload.get("task_id") or str(uuid.uuid4()),
        "task_type": payload.get("task_type", "unknown"),
        "activated_experts": payload.get("activated_experts", ["quality-critic", "analysis-taxonomy"]),
        "hard_constraints": payload.get("hard_constraints", []), "vetoes": all_vetoes,
        "candidates": clean_candidates, "decision": decision, "selected_candidate": selected,
        "rationale": rationale, "quality_score": quality,
        "confidence": float(payload.get("confidence", 0.8)),
        "user_choice_required": ask, "ready_for_delivery": ready,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    route_parser = sub.add_parser("route")
    route_parser.add_argument("--task-type", required=True)
    route_parser.add_argument("--rounds-completed", type=int, default=0)
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--input", required=True)
    args = parser.parse_args()
    if args.command == "route":
        print(json.dumps(route(args.task_type, args.rounds_completed), ensure_ascii=False, indent=2))
    else:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        print(json.dumps(arbitrate(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
