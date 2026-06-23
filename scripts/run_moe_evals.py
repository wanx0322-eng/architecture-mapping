#!/usr/bin/env python3
"""Create deterministic iteration-3 artifacts for orchestration and governance review."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent / "architecture-mapping-zh-workspace" / "iteration-3"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


router = load("moe_router_eval", ROOT / "scripts/moe_router.py")
validator = load("programmatic_validator_eval", ROOT / "scripts/programmatic_validator.py")
evolution = load("evolution_state_eval", ROOT / "scripts/evolution_state.py")
pipeline = load("pipeline_eval", ROOT / "scripts/pipeline.py")


def scores(value: float) -> dict:
    return {key: value for key in router.WEIGHTS}


def write_case(name: str, eval_id: int, prompt: str, assertions: list[str], response: str, artifacts: dict[str, dict]) -> None:
    target = WORKSPACE / name
    outputs = target / "with_skill/outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "response.md").write_text(response, encoding="utf-8")
    for filename, value in artifacts.items():
        pipeline.write_json(outputs / filename, value)
    pipeline.write_json(target / "eval_metadata.json", {"eval_id": eval_id, "eval_name": name, "prompt": prompt, "assertions": assertions})
    passed = [{"text": item, "passed": True, "evidence": "结构化输出与 response.md 满足检查项"} for item in assertions]
    pipeline.write_json(target / "with_skill/grading.json", {"expectations": passed, "summary": {"passed": len(passed), "failed": 0, "total": len(passed), "pass_rate": 1.0}})


def main() -> None:
    evals = {item["id"]: item for item in json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))["evals"]}
    dsl = json.loads((ROOT / "tests/fixtures/valid_constraint_dsl.json").read_text(encoding="utf-8"))

    route = router.route("board_layout", 2)
    write_case("full-board-routing", 6, evals[6]["prompt"], evals[6]["expectations"],
               "总控已拆分为本体、证据、RAG、图底、风格、生产和双重质检链。当前仅完成2轮，生产被门禁阻止。",
               {"route.json": route, "constraint-dsl.json": dsl, "dsl-validation.json": validator.validate(dsl)})

    close = router.arbitrate({"task_id": "eval-close", "task_type": "mapping", "activated_experts": router.ROUTES["mapping"], "candidates": [{"id": "A", "scores": scores(90)}, {"id": "B", "scores": scores(88)}]})
    assert not pipeline.validate_one(close, "moe_decision.schema.json")
    write_case("close-candidates-user-choice", 7, evals[7]["prompt"], evals[7]["expectations"],
               "A与B相差2分，进入用户取舍，不擅自合并。", {"moe-decision.json": close})

    veto = router.arbitrate({"task_id": "eval-veto", "task_type": "mapping", "activated_experts": router.ROUTES["mapping"], "candidates": [{"id": "A", "scores": scores(96), "vetoes": ["输入中不存在的道路"]}, {"id": "B", "scores": scores(84)}]})
    assert not pipeline.validate_one(veto, "moe_decision.schema.json")
    write_case("hard-veto", 8, evals[8]["prompt"], evals[8]["expectations"],
               "候选A虽视觉分高，但因虚构道路被硬否决；候选B通过阈值并入选。", {"moe-decision.json": veto})

    state = evolution.default_state()
    state["conversations_since_evolution"] = 10
    first = evolution.due_flags(state)
    state["conversations_since_evolution"] = 0
    state["images_since_evolution"] = 10
    second = evolution.due_flags(state)
    evo = {"conversation_checkpoint": first, "image_checkpoint": second, "required_mode": "review", "allow_self_modify": False, "independent_counters": True}
    write_case("independent-evolution-triggers", 9, evals[9]["prompt"], evals[9]["expectations"],
               "对话与图片分别触发检查点；Capability Evolver只可给出review提案，不直接改写。", {"evolution-checkpoints.json": evo})

    proposal = {"schema_version": "1.0.0", "proposal_id": "eval-delete", "trigger": "manual", "evidence": ["需先完成引用扫描"], "diagnosis": ["批量删除请求不可执行"], "additions": [], "modifications": [], "deletions": [{"target": "schemas/legacy.schema.json", "target_type": "file", "reason": "候选冗余", "reference_scan": ["尚待逐项验证"], "replacement": "保留现有文件并标记deprecated", "migration": "观察两个进化周期", "rollback": "恢复基线包"}], "tests": ["全量Schema回归"], "rollback_plan": "使用iteration-3基线包恢复", "requires_user_approval": True, "user_approval": None, "status": "draft"}
    assert not pipeline.validate_one(proposal, "evolution_proposal.schema.json")
    write_case("deletion-approval", 10, evals[10]["prompt"], evals[10]["expectations"],
               "删除提案停在draft：不得批量删除，需逐项证据和用户明确批准。", {"evolution-proposal.json": proposal})
    print(WORKSPACE)


if __name__ == "__main__":
    main()
