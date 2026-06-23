#!/usr/bin/env python3
"""Validate Constraint DSL structure and cross-file semantic invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

import jsonschema


SCHEMA = json.loads((ROOT / "schemas/constraint_dsl.schema.json").read_text(encoding="utf-8"))
ONTOLOGY = json.loads((ROOT / "assets/drawing_ontology.json").read_text(encoding="utf-8"))
STYLES = json.loads((ROOT / "assets/style_tokens.json").read_text(encoding="utf-8"))
GRAMMAR = json.loads((ROOT / "assets/drawing_grammar.json").read_text(encoding="utf-8"))
RAG = json.loads((ROOT / "assets/rag_manifest.json").read_text(encoding="utf-8"))
PRODUCTION_TYPES = {"mapping", "image_generation", "image_edit", "board_layout", "final_prompt"}


def semantic_checks(value: dict) -> list[dict]:
    checks: list[dict] = []

    def add(check_id: str, passed: bool, evidence: str, repair_target: str) -> None:
        checks.append({"id": check_id, "passed": passed, "evidence": evidence, "repair_target": repair_target})

    task_type = value.get("task_type")
    interview = value.get("interview", {})
    rounds = interview.get("rounds_completed", 0)
    ready = interview.get("ready_for_production", False)
    gate_ok = task_type not in PRODUCTION_TYPES or (rounds >= 3 and ready)
    add("production_gate", gate_ok, f"task_type={task_type}, rounds={rounds}, ready={ready}", "brief-intake")

    class_ids = {item["id"] for item in ONTOLOGY["classes"]}
    primary = value.get("ontology", {}).get("primary_class")
    add("ontology_class", primary in class_ids, f"primary_class={primary}", "analysis-taxonomy")

    graphics = value.get("graphics", {})
    token = graphics.get("style_token")
    secondary = graphics.get("secondary_style_token")
    token_ids = set(STYLES["token_sets"])
    token_ok = token in token_ids and (secondary is None or secondary in token_ids)
    add("style_tokens", token_ok, f"primary={token}, secondary={secondary}", "style-layout")

    pattern = graphics.get("grammar_pattern")
    pattern_ok = pattern in GRAMMAR["composition_patterns"]
    add("drawing_grammar", pattern_ok, f"grammar_pattern={pattern}", "figure-ground-graphics")

    claim = value.get("analysis", {}).get("claim", "").strip()
    evidence = value.get("analysis", {}).get("evidence_refs", [])
    evidence_ok = not claim or bool(evidence)
    add("claim_evidence", evidence_ok, f"claim_present={bool(claim)}, evidence_count={len(evidence)}", "evidence-geometry")

    known_sources = {item["id"] for item in RAG["collections"]}
    rag_items = value.get("rag_evidence", [])
    rag_ok = all(item.get("source_id") in known_sources for item in rag_items)
    add("rag_sources", rag_ok, f"references={len(rag_items)}", "analysis-taxonomy")

    locked = set(value.get("geometry", {}).get("locked", []))
    editable = set(value.get("geometry", {}).get("editable", []))
    overlap = sorted(locked & editable)
    add("geometry_ownership", not overlap, f"locked_editable_overlap={overlap}", "evidence-geometry")

    text = value.get("text", {})
    text_ok = text.get("language") == "en" or text.get("render_strategy") in {"svg_overlay", "pptx_overlay", "none"}
    add("chinese_text_strategy", text_ok, f"language={text.get('language')}, strategy={text.get('render_strategy')}", "model-production")
    return checks


def validate(value: dict) -> dict:
    schema_errors = sorted(jsonschema.Draft202012Validator(SCHEMA).iter_errors(value), key=lambda item: list(item.path))
    formatted = [{"path": "/".join(str(p) for p in item.path), "message": item.message} for item in schema_errors]
    checks = semantic_checks(value) if not schema_errors else []
    failures = [item for item in checks if not item["passed"]]
    return {
        "valid": not formatted and not failures,
        "schema_errors": formatted,
        "semantic_checks": checks,
        "repair_targets": sorted({item["repair_target"] for item in failures}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    value = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = validate(value)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
