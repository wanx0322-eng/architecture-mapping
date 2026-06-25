from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLUSTERS = {
    "minimal_grey_competition",
    "ecological_layered_wash",
    "desaturated_paper_collage",
    "precision_vector_analysis",
    "layered_landscape_axonometric",
    "diagnostic_heat_overlay",
    "hand_drawn_mixed_media",
    "dark_high_contrast_narrative",
}


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def read_json(relative: str) -> dict:
    return json.loads(read_text(relative))


def test_skill_routes_opt_in_pinterest_style_through_all_responsible_experts():
    skill = read_text("SKILL.md")
    assert "style_source=pinterest_dataset" in skill
    assert "05-style-layout" in skill
    assert "06-model-production" in skill
    assert "07-quality-critic" in skill
    assert "09-knowledge-retrieval" in skill
    assert "10-programmatic-validator" in skill
    assert "自动选择风格簇" in skill

    for relative in [
        "subskills/05-style-layout/INSTRUCTIONS.md",
        "subskills/06-model-production/INSTRUCTIONS.md",
        "subskills/07-quality-critic/INSTRUCTIONS.md",
        "subskills/09-knowledge-retrieval/INSTRUCTIONS.md",
        "subskills/10-programmatic-validator/INSTRUCTIONS.md",
    ]:
        text = read_text(relative)
        assert "pinterest_dataset" in text


def test_all_pinterest_clusters_are_registered_as_opt_in_style_tokens():
    profiles = read_json("assets/pinterest_style_profiles.json")
    tokens = read_json("assets/style_tokens.json")
    assert set(profiles["clusters"]) == CLUSTERS
    assert set(tokens["pinterest_token_sets"]) == CLUSTERS
    assert tokens["pinterest_activation_rule"] == "style_source=pinterest_dataset"


def test_primary_rag_manifest_can_discover_runtime_pinterest_indexes():
    manifest = read_json("assets/rag_manifest.json")
    collections = {item["id"]: item for item in manifest["collections"]}
    assert collections["pinterest-style-clusters"]["optional"] is True
    assert collections["pinterest-style-assignments"]["optional"] is True
    assert manifest["retrieval_policy"]["pinterest_style_opt_in_only"] is True


def test_prompt_and_quality_specs_define_strength_and_geometry_precedence():
    prompt_spec = read_text("references/prompt-spec.md")
    rubric = read_text("references/eval-rubric-loop.md")
    assert "low / medium / high" in prompt_spec
    assert "Gemini" in prompt_spec and "GPT Image" in prompt_spec and "Midjourney" in prompt_spec
    assert "F2/F3" in prompt_spec
    assert "Pinterest 风格一致性" in rubric
    assert "不得覆盖几何忠实度" in rubric
