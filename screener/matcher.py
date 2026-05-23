"""Hybrid scoring engine: TF-IDF semantic similarity + skill coverage."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skills import all_skills, extract_skills, skill_coverage

# Default weighting: 60% skill coverage (HR-specific), 40% semantic match.
# Skill coverage gets the higher weight because recruiters care about the keyword
# checklist; semantic match catches synonyms, paraphrasing, and overall fit.
DEFAULT_SKILL_WEIGHT = 0.6
DEFAULT_SEMANTIC_WEIGHT = 0.4


@dataclass
class CandidateResult:
    candidate: str
    overall_score: float
    semantic_score: float
    skill_score: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    extra_skills: list[str] = field(default_factory=list)
    raw_text_chars: int = 0

    def as_row(self) -> dict:
        return {
            "Candidate": self.candidate,
            "Overall Score": round(self.overall_score * 100, 2),
            "Semantic Match": round(self.semantic_score * 100, 2),
            "Skill Coverage": round(self.skill_score * 100, 2),
            "Matched Skills": ", ".join(self.matched_skills),
            "Missing Skills": ", ".join(self.missing_skills),
            "Extra Skills": ", ".join(self.extra_skills),
            "Resume Length (chars)": self.raw_text_chars,
        }


def _clean_for_tfidf(text: str) -> str:
    """Lowercase and collapse non-alphanumeric runs for TF-IDF."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./ ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _semantic_scores(jd_text: str, resume_texts: list[str]) -> list[float]:
    """Return cosine similarity of each resume against the JD."""
    cleaned_jd = _clean_for_tfidf(jd_text)
    cleaned_resumes = [_clean_for_tfidf(t) for t in resume_texts]
    corpus = [cleaned_jd] + cleaned_resumes

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        stop_words="english",
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(corpus)
    sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    return [float(s) for s in sims]


def score_candidates(
    jd_text: str,
    resumes: dict[str, str],
    *,
    skill_weight: float = DEFAULT_SKILL_WEIGHT,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
) -> list[CandidateResult]:
    """Score each resume against the job description.

    Args:
        jd_text: Raw job description text.
        resumes: Mapping of candidate name → resume text.
        skill_weight: Weight applied to JD skill coverage [0..1].
        semantic_weight: Weight applied to TF-IDF cosine similarity [0..1].

    Returns:
        List of `CandidateResult`, sorted by overall_score descending.
    """
    if not resumes:
        return []

    # Normalize weights so they always sum to 1 even if the caller passes raw values.
    total_weight = skill_weight + semantic_weight
    if total_weight <= 0:
        skill_weight, semantic_weight = DEFAULT_SKILL_WEIGHT, DEFAULT_SEMANTIC_WEIGHT
        total_weight = skill_weight + semantic_weight
    skill_w = skill_weight / total_weight
    semantic_w = semantic_weight / total_weight

    skills_universe = all_skills()
    jd_skills = extract_skills(jd_text, skills_universe)

    candidate_names = list(resumes.keys())
    resume_texts = [resumes[name] for name in candidate_names]
    semantic_scores = _semantic_scores(jd_text, resume_texts)

    results: list[CandidateResult] = []
    for name, text, sem in zip(candidate_names, resume_texts, semantic_scores):
        resume_skills = extract_skills(text, skills_universe)
        coverage, matched, missing = skill_coverage(jd_skills, resume_skills)
        extra = sorted(set(resume_skills) - set(jd_skills))
        overall = (skill_w * coverage) + (semantic_w * sem)
        results.append(
            CandidateResult(
                candidate=name,
                overall_score=overall,
                semantic_score=sem,
                skill_score=coverage,
                matched_skills=matched,
                missing_skills=missing,
                extra_skills=extra,
                raw_text_chars=len(text),
            )
        )

    results.sort(key=lambda r: r.overall_score, reverse=True)
    return results
