#!/usr/bin/env python3
"""Maintain privacy-minimized counters and audited evolution checkpoints."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.0.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "skill_version": "1.0.0",
        "total_conversations": 0,
        "total_images": 0,
        "conversations_since_evolution": 0,
        "images_since_evolution": 0,
        "last_failure_type": None,
        "consecutive_same_failure": 0,
        "last_evolution_at": None,
        "updated_at": now_iso(),
    }


def read_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def paths(root: Path) -> tuple[Path, Path, Path]:
    return root / "evolution_state.json", root / "runtime_events.jsonl", root / "checkpoints"


def due_flags(state: dict) -> dict:
    return {
        "ten_conversations": state["conversations_since_evolution"] >= 10,
        "ten_images": state["images_since_evolution"] >= 10,
        "repeated_failure": state["consecutive_same_failure"] >= 3,
    }


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.state_root)
    state_path, _, checkpoint_dir = paths(root)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    state = read_json(state_path, default_state())
    write_json(state_path, state)
    print(json.dumps({"state_root": str(root.resolve()), "state": state, "due": due_flags(state)}, ensure_ascii=False))


def cmd_record(args: argparse.Namespace) -> None:
    root = Path(args.state_root)
    state_path, events_path, _ = paths(root)
    state = read_json(state_path, default_state())
    conversations = max(0, args.conversations)
    images = max(0, args.images)
    state["total_conversations"] += conversations
    state["conversations_since_evolution"] += conversations
    state["total_images"] += images
    state["images_since_evolution"] += images
    if args.success:
        state["last_failure_type"] = None
        state["consecutive_same_failure"] = 0
    elif args.failure_type:
        if state.get("last_failure_type") == args.failure_type:
            state["consecutive_same_failure"] += 1
        else:
            state["last_failure_type"] = args.failure_type
            state["consecutive_same_failure"] = 1
    state["updated_at"] = now_iso()
    event = {
        "event_id": str(uuid.uuid4()), "timestamp": state["updated_at"],
        "event_type": "runtime_task", "task_type": args.task_type,
        "experts": sorted(set(args.expert)), "conversation_count": conversations,
        "image_count": images, "success": args.success,
        "failure_type": args.failure_type, "quality_score": args.quality_score,
        "feedback_signal": args.feedback_signal,
        "privacy_note": "No prompt text, source path, project name, or image content is stored.",
    }
    write_json(state_path, state)
    append_jsonl(events_path, event)
    print(json.dumps({"state": state, "due": due_flags(state), "event_id": event["event_id"]}, ensure_ascii=False))


def cmd_status(args: argparse.Namespace) -> None:
    state_path, _, _ = paths(Path(args.state_root))
    state = read_json(state_path, default_state())
    print(json.dumps({"state": state, "due": due_flags(state)}, ensure_ascii=False, indent=2))


def cmd_checkpoint(args: argparse.Namespace) -> None:
    root = Path(args.state_root)
    state_path, events_path, checkpoint_dir = paths(root)
    state = read_json(state_path, default_state())
    due = due_flags(state)
    requested = [name for name, value in due.items() if value]
    if args.trigger != "auto":
        requested = [args.trigger]
    events = []
    if events_path.exists():
        lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        events = [json.loads(line) for line in lines[-20:]]
    checkpoint = {
        "schema_version": SCHEMA_VERSION,
        "checkpoint_id": f"evo-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "created_at": now_iso(), "triggers": requested,
        "state_snapshot": state, "recent_events": events,
        "required_mode": "review",
        "allow_self_modify": False,
        "deletion_policy": "Any file, field, document, or schema deletion requires exact evidence and explicit user approval.",
        "next_steps": ["diagnose patterns", "draft evolution proposal", "run tests", "request deletion approval if needed"],
    }
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output = checkpoint_dir / f"{checkpoint['checkpoint_id']}.json"
    write_json(output, checkpoint)
    append_jsonl(events_path, {"event_id": str(uuid.uuid4()), "timestamp": now_iso(), "event_type": "evolution_checkpoint", "checkpoint_path": str(output), "triggers": requested})
    print(json.dumps({"checkpoint": str(output), "triggers": requested}, ensure_ascii=False))


def cmd_review_proposal(args: argparse.Namespace) -> None:
    proposal_path = Path(args.proposal)
    proposal = read_json(proposal_path)
    deletions = proposal.get("deletions", [])
    proposal["requires_user_approval"] = bool(deletions)
    proposal["status"] = "draft" if deletions else "reviewed"
    proposal["reviewed_at"] = now_iso()
    proposal["review_result"] = {
        "deletion_count": len(deletions),
        "can_apply_without_user": not deletions,
        "reason": "Deletion candidates require explicit user approval." if deletions else "No deletion requested; tests are still required before application.",
    }
    write_json(proposal_path, proposal)
    print(json.dumps(proposal["review_result"], ensure_ascii=False))


def cmd_complete(args: argparse.Namespace) -> None:
    root = Path(args.state_root)
    state_path, events_path, _ = paths(root)
    state = read_json(state_path, default_state())
    if args.trigger in {"ten_conversations", "manual"}:
        state["conversations_since_evolution"] = 0
    if args.trigger in {"ten_images", "manual"}:
        state["images_since_evolution"] = 0
    if args.trigger in {"repeated_failure", "manual"}:
        state["last_failure_type"] = None
        state["consecutive_same_failure"] = 0
    state["skill_version"] = args.version
    state["last_evolution_at"] = now_iso()
    state["updated_at"] = state["last_evolution_at"]
    write_json(state_path, state)
    append_jsonl(events_path, {"event_id": str(uuid.uuid4()), "timestamp": now_iso(), "event_type": "evolution_complete", "trigger": args.trigger, "version": args.version, "summary": args.summary})
    print(json.dumps({"state": state, "due": due_flags(state)}, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--state-root", default=str(Path.cwd() / "architecture-mapping-zh-runtime"))
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("init").set_defaults(handler=cmd_init)
    sub.add_parser("status").set_defaults(handler=cmd_status)
    record = sub.add_parser("record")
    record.add_argument("--conversations", type=int, default=1)
    record.add_argument("--images", type=int, default=0)
    record.add_argument("--task-type", default="unknown")
    record.add_argument("--expert", action="append", default=[])
    record.add_argument("--success", action=argparse.BooleanOptionalAction, default=True)
    record.add_argument("--failure-type")
    record.add_argument("--quality-score", type=float)
    record.add_argument("--feedback-signal")
    record.set_defaults(handler=cmd_record)
    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--trigger", choices=["auto", "ten_conversations", "ten_images", "repeated_failure", "manual"], default="auto")
    checkpoint.set_defaults(handler=cmd_checkpoint)
    review = sub.add_parser("review-proposal")
    review.add_argument("--proposal", required=True)
    review.set_defaults(handler=cmd_review_proposal)
    complete = sub.add_parser("complete")
    complete.add_argument("--trigger", choices=["ten_conversations", "ten_images", "repeated_failure", "manual"], required=True)
    complete.add_argument("--version", required=True)
    complete.add_argument("--summary", required=True)
    complete.set_defaults(handler=cmd_complete)
    return value


def main() -> None:
    args = parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
