import json
from pathlib import Path
from typing import Any

SCORECARDS_DIR = Path(__file__).resolve().parents[1] / "templates" / "scorecards"

SCORE_ANCHORS = """Score each criterion 1-5:
1 = no evidence or clearly below bar
2 = superficial or incorrect examples
3 = adequate with notable gaps
4 = strong with concrete, relevant examples
5 = exceptional depth, tradeoffs, and ownership"""


def list_scorecards() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(SCORECARDS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items.append(
            {
                "id": data["id"],
                "title": data["title"],
                "criteria": data.get("criteria", []),
            }
        )
    return items


def get_scorecard(scorecard_id: str) -> dict[str, Any] | None:
    path = SCORECARDS_DIR / f"{scorecard_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def scorecard_prompt_block(scorecard: dict[str, Any]) -> str:
    lines = [
        f"Use this role scorecard ({scorecard['title']}):",
        SCORE_ANCHORS,
    ]
    for c in scorecard.get("criteria", []):
        weight = c.get("weight")
        weight_note = f" (weight {weight})" if weight is not None else ""
        lines.append(f"- {c['label']} (id: {c['id']}){weight_note}")
    lines.append(
        "Include scorecard_scores: array of "
        '{"criterion": "label", "criterion_id": "id", "score": 1-5, "notes": "evidence with quote"} '
        "for each criterion above. Use notes to cite transcript evidence."
    )
    return "\n".join(lines)
