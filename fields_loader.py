import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

DATA_PATH = DATA_DIR / "study_fields.json"
QUESTIONS_DATA_PATH = DATA_DIR / "career_orientation_questions_v2_locked.json"

# Dimensions for the interest profile
INTEREST_KEYS = [
    "analytical",
    "investigative",
    "social",
    "creative",
    "enterprising",
    "hands_on",
]


def _check_unit_interval(value: Any, path: str) -> float:
    """Validate a numeric value in [0.0, 1.0] and return it as float."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number, got {type(value).__name__}")
    value_f = float(value)
    if not (0.0 <= value_f <= 1.0):
        raise ValueError(f"{path} must be in [0.0, 1.0], got {value_f}")
    return value_f


def load_fields() -> List[Dict[str, Any]]:
    """Load and validate study fields from data/study_fields.json including constraints and core values."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing file: {DATA_PATH}")

    with DATA_PATH.open("r", encoding="utf-8") as f:
        fields = json.load(f)

    if not isinstance(fields, list) or len(fields) == 0:
        raise ValueError("study_fields.json must be a non-empty JSON list")

    seen_ids = set()
    for i, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError(f"fields[{i}] must be an object")

        # 1) Identity Validation
        field_id = field.get("id")
        name = field.get("name")
        if not isinstance(field_id, str) or not field_id.strip() or field_id in seen_ids:
            raise ValueError(f"Invalid or duplicate ID at index {i}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"fields[{i}].name must be a non-empty string")
        seen_ids.add(field_id)

        # 2) Interests Validation (allow missing keys -> default 0.5)
        interests = field.get("interests", {})
        if not isinstance(interests, dict):
            raise ValueError(f"fields[{i}].interests must be an object")

        for k in INTEREST_KEYS:
            raw = interests.get(k, 0.5)
            interests[k] = _check_unit_interval(raw, f"fields[{i}].interests.{k}")
        field["interests"] = interests

        # 3) Constraints Validation (optional object; validate any provided)
        constraints = field.get("constraints", {})
        if constraints is None:
            constraints = {}
        if not isinstance(constraints, dict):
            raise ValueError(f"fields[{i}].constraints must be an object")

        for ck, cv in constraints.items():
            constraints[ck] = _check_unit_interval(cv, f"fields[{i}].constraints.{ck}")
        field["constraints"] = constraints

        # 4) Core Values Validation
        core_values = field.get("core_values")
        if not isinstance(core_values, list):
            raise ValueError(f"fields[{i}].core_values must be a list of strings")

        for j, val in enumerate(core_values):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"fields[{i}].core_values[{j}] must be a non-empty string")

        # 5) Optional: tags / family (keep if exists, else default)
        tags = field.get("tags", [])
        if tags is None:
            tags = []
        if not isinstance(tags, list) or any((not isinstance(t, str) or not t.strip()) for t in tags):
            raise ValueError(f"fields[{i}].tags must be a list of non-empty strings")
        field["tags"] = tags

        family = field.get("family", None)
        if family is not None and (not isinstance(family, str) or not family.strip()):
            raise ValueError(f"fields[{i}].family must be a non-empty string or null")
        field["family"] = family

    return fields


def load_questions() -> List[Dict[str, Any]]:
    """Load and return the list of career orientation questions."""
    if not QUESTIONS_DATA_PATH.exists():
        raise FileNotFoundError(f"Missing file: {QUESTIONS_DATA_PATH}")

    with QUESTIONS_DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # supports both {"questions":[...]} and direct list formats
    if isinstance(data, dict):
        return data.get("questions", [])
    if isinstance(data, list):
        return data
    raise ValueError("Questions JSON must be either an object with 'questions' or a list")


if __name__ == "__main__":
    try:
        fields = load_fields()
        print(f"✅ Successfully loaded {len(fields)} fields with core values.")
        print(f"Example core values for {fields[0]['name']}: {fields[0]['core_values']}")

        questions = load_questions()
        print(f"✅ Successfully loaded {len(questions)} questions.")

        if questions:
            q0 = questions[0]
            qid = q0.get("id", "<missing id>")
            qtext = q0.get("text_he") or q0.get("text") or "<missing question text>"
            print(f"Example question: id={qid}, text={qtext[:120]}")

    except Exception as e:
        print(f"❌ Error: {e}")
