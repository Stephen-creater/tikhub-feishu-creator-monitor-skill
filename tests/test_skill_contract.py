from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_skill_frontmatter_and_runtime_contract() -> None:
    skill = ROOT / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, raw_frontmatter, body = text.split("---", 2)
    frontmatter = yaml.safe_load(raw_frontmatter)
    assert frontmatter["name"] == "creator-monitor"
    assert "TikHub" in frontmatter["description"]
    assert "飞书" in frontmatter["description"]
    assert "scripts/creator-monitor" in body


def test_skill_references_only_existing_files() -> None:
    required = [
        ROOT / "references" / "data-contract.md",
        ROOT / "references" / "operations.md",
        ROOT / "scripts" / "creator-monitor",
        ROOT / "agents" / "openai.yaml",
    ]
    assert all(path.exists() for path in required)


def test_no_scaffold_placeholders() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for placeholder in ("TODO", "TBD", "[PLACEHOLDER]", "your-skill-name"):
        assert placeholder not in text
