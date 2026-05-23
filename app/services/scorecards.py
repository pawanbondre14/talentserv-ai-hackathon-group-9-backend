import json
from pathlib import Path
from typing import Any

SCORECARDS_DIR = Path(__file__).resolve().parents[1] / "templates" / "scorecards"


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
    lines = [f"Use this role scorecard ({scorecard['title']}):"]
    for c in scorecard.get("criteria", []):
        lines.append(f"- {c['label']} (id: {c['id']})")
    lines.append(
        "Include scorecard_scores: array of "
        '{"criterion": "label", "criterion_id": "id", "score": 1-5, "notes": "evidence"} '
        "for each criterion above."
    )
    return "\n".join(lines)
