"""Skill extraction using a curated taxonomy."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TAXONOMY_PATH = DATA_DIR / "skills_taxonomy.json"


@lru_cache(maxsize=1)
def load_taxonomy(path: str | Path | None = None) -> dict[str, list[str]]:
    """Load and cache the skill taxonomy from JSON."""
    target = Path(path) if path else TAXONOMY_PATH
    with open(target, "r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def all_skills() -> list[str]:
    """Flat, deduplicated list of every skill in the taxonomy (lowercased)."""
    taxonomy = load_taxonomy()
    seen: set[str] = set()
    flat: list[str] = []
    for skills in taxonomy.values():
        for skill in skills:
            s = skill.strip().lower()
            if s and s not in seen:
                seen.add(s)
                flat.append(s)
    return flat


def _pattern_for(skill: str) -> re.Pattern[str]:
    """Compile a word-boundary regex that handles multi-word and symbol skills."""
    # Escape special chars (e.g. "c++", "c#", "ci/cd") then enforce word boundaries
    # where it makes sense. For tokens with non-word ends we use a lookaround.
    escaped = re.escape(skill)
    # If the skill starts/ends with a word char, use \b; otherwise use lookarounds.
    left = r"(?<![A-Za-z0-9])" if not re.match(r"\w", skill[0]) else r"\b"
    right = r"(?![A-Za-z0-9])" if not re.match(r"\w", skill[-1]) else r"\b"
    return re.compile(f"{left}{escaped}{right}", re.IGNORECASE)


@lru_cache(maxsize=512)
def _compiled_skill_patterns(skills_tuple: tuple[str, ...]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    return tuple((s, _pattern_for(s)) for s in skills_tuple)


def extract_skills(text: str, skills: list[str] | None = None) -> list[str]:
    """Return the list of taxonomy skills found in `text`, preserving taxonomy order."""
    if not text:
        return []
    candidates = skills or all_skills()
    patterns = _compiled_skill_patterns(tuple(candidates))
    found: list[str] = []
    for skill, pattern in patterns:
        if pattern.search(text):
            found.append(skill)
    return found


def skill_coverage(jd_skills: list[str], resume_skills: list[str]) -> tuple[float, list[str], list[str]]:
    """Compute fraction of JD skills present in resume.

    Returns:
        (coverage_ratio, matched_skills, missing_skills)
    """
    if not jd_skills:
        return 0.0, [], []
    jd_set = {s.lower() for s in jd_skills}
    resume_set = {s.lower() for s in resume_skills}
    matched = sorted(jd_set & resume_set)
    missing = sorted(jd_set - resume_set)
    return len(matched) / len(jd_set), matched, missing
