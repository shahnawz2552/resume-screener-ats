"""CLI smoke test: rank the bundled sample resumes against the sample JD."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/run_demo.py` from project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from screener.exporter import build_excel_report  # noqa: E402
from screener.matcher import score_candidates  # noqa: E402
from screener.parser import extract_text  # noqa: E402
from screener.skills import all_skills, extract_skills  # noqa: E402

SAMPLES = PROJECT_ROOT / "samples"
OUTPUT = PROJECT_ROOT / "output" / "demo_report.xlsx"


def main() -> int:
    jd_path = SAMPLES / "job_description.txt"
    if not jd_path.exists():
        print(f"❌ Missing JD at {jd_path}")
        return 1

    jd_text = extract_text(jd_path)
    resumes: dict[str, str] = {}
    for path in sorted(SAMPLES.glob("resume_*.txt")):
        label = path.stem.replace("resume_", "").replace("_", " ").title()
        resumes[label] = extract_text(path)

    if not resumes:
        print("❌ No sample resumes found.")
        return 1

    skills = all_skills()
    jd_skills = extract_skills(jd_text, skills)
    print(f"JD skills detected ({len(jd_skills)}): {', '.join(jd_skills)}")
    print(f"Scoring {len(resumes)} candidates...\n")

    results = score_candidates(jd_text, resumes)

    header = f"{'Rank':<6}{'Candidate':<25}{'Overall':>10}{'Skills':>10}{'Semantic':>12}"
    print(header)
    print("-" * len(header))
    for idx, r in enumerate(results, start=1):
        print(
            f"{idx:<6}{r.candidate:<25}"
            f"{r.overall_score * 100:>9.1f}"
            f"{r.skill_score * 100:>10.1f}"
            f"{r.semantic_score * 100:>12.1f}"
        )

    print("\nTop candidate matched skills:")
    print(", ".join(results[0].matched_skills) or "(none)")
    print("\nTop candidate missing skills:")
    print(", ".join(results[0].missing_skills) or "(none)")

    build_excel_report(results, job_title="Data Analyst — HR Analytics", output_path=OUTPUT)
    print(f"\n✅ Excel report written to {OUTPUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
