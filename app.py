"""Streamlit UI for the Resume Screener ATS tool."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from screener.exporter import build_excel_report
from screener.matcher import score_candidates
from screener.parser import extract_text
from screener.skills import all_skills, extract_skills

SAMPLES_DIR = Path(__file__).parent / "samples"

st.set_page_config(
    page_title="Resume Screener ATS",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- helpers ----------

def _load_sample_text(filename: str) -> str:
    path = SAMPLES_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _read_uploaded_resumes(uploaded_files) -> dict[str, str]:
    resumes: dict[str, str] = {}
    for upload in uploaded_files:
        text = extract_text(upload, filename=upload.name)
        if text.strip():
            label = Path(upload.name).stem.replace("_", " ").title()
            # Disambiguate duplicates
            base_label, idx = label, 2
            while label in resumes:
                label = f"{base_label} ({idx})"
                idx += 1
            resumes[label] = text
    return resumes


def _load_sample_resumes() -> dict[str, str]:
    resumes: dict[str, str] = {}
    if not SAMPLES_DIR.exists():
        return resumes
    for path in sorted(SAMPLES_DIR.glob("resume_*.txt")):
        label = path.stem.replace("resume_", "").replace("_", " ").title()
        resumes[label] = path.read_text(encoding="utf-8")
    return resumes


def _score_color(score: float) -> str:
    if score >= 70:
        return "🟢"
    if score >= 40:
        return "🟡"
    return "🔴"


# ---------- sidebar ----------

with st.sidebar:
    st.title("⚙️  Settings")
    use_samples = st.toggle(
        "Use sample data",
        value=True,
        help="Load a built-in JD and 3 demo resumes so you can try the tool instantly.",
    )

    st.markdown("**Scoring weights**")
    skill_weight = st.slider("Skill coverage weight", 0.0, 1.0, 0.6, 0.05)
    semantic_weight = st.slider("Semantic match weight", 0.0, 1.0, 0.4, 0.05)
    st.caption(
        f"Effective: skills={skill_weight / (skill_weight + semantic_weight):.0%}, "
        f"semantic={semantic_weight / (skill_weight + semantic_weight):.0%}"
    )

    st.markdown("---")
    st.markdown(
        "**About**  \n"
        "Hybrid ATS scorer combining a curated skill taxonomy with TF-IDF cosine "
        "similarity. Built for HR teams that need to rank dozens of resumes fast."
    )


# ---------- header ----------

st.title("📄 Resume Screener ATS")
st.markdown(
    "Upload a job description and a folder of resumes — get a ranked Excel report "
    "with match scores, matched skills, and gaps in seconds."
)


# ---------- inputs ----------

left, right = st.columns([1, 1])

with left:
    st.subheader("1. Job Description")
    default_jd = _load_sample_text("job_description.txt") if use_samples else ""
    jd_text = st.text_area(
        "Paste the JD here",
        value=default_jd,
        height=320,
        placeholder="Paste the job description...",
    )
    job_title = st.text_input(
        "Job title (used in report header)",
        value="Data Analyst" if use_samples else "",
    )

with right:
    st.subheader("2. Resumes")
    if use_samples:
        st.info("Sample mode is on — 3 demo resumes will be used.", icon="ℹ️")
        uploaded_files = []
    else:
        uploaded_files = st.file_uploader(
            "Upload resumes (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
        )
        st.caption("Tip: select multiple files at once.")


# ---------- run ----------

run = st.button("🔍 Screen resumes", type="primary", use_container_width=True)

if run:
    if not jd_text.strip():
        st.error("Please provide a job description.")
        st.stop()

    if use_samples:
        resumes = _load_sample_resumes()
    else:
        resumes = _read_uploaded_resumes(uploaded_files or [])

    if not resumes:
        st.error("No readable resumes found. Upload at least one PDF, DOCX, or TXT.")
        st.stop()

    with st.spinner(f"Scoring {len(resumes)} candidate(s)..."):
        results = score_candidates(
            jd_text,
            resumes,
            skill_weight=skill_weight,
            semantic_weight=semantic_weight,
        )

    # --- top metrics ---
    jd_skills = extract_skills(jd_text, all_skills())
    top = results[0]
    avg = sum(r.overall_score for r in results) / len(results)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidates", len(results))
    m2.metric("Top score", f"{top.overall_score * 100:.1f}")
    m3.metric("Average score", f"{avg * 100:.1f}")
    m4.metric("JD skills detected", len(jd_skills))

    st.markdown("---")

    # --- ranked table ---
    st.subheader("🏆 Ranked candidates")
    rows = []
    for idx, r in enumerate(results, start=1):
        rows.append({
            "Rank": idx,
            "": _score_color(r.overall_score * 100),
            "Candidate": r.candidate,
            "Overall": round(r.overall_score * 100, 1),
            "Skill Coverage": round(r.skill_score * 100, 1),
            "Semantic": round(r.semantic_score * 100, 1),
            "Matched": len(r.matched_skills),
            "Missing": len(r.missing_skills),
        })
    df_view = pd.DataFrame(rows)
    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Overall": st.column_config.ProgressColumn(
                "Overall",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Skill Coverage": st.column_config.ProgressColumn(
                "Skill Coverage",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Semantic": st.column_config.ProgressColumn(
                "Semantic",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
        },
    )

    # --- per-candidate breakdown ---
    st.subheader("🔎 Candidate breakdown")
    for r in results:
        with st.expander(
            f"{_score_color(r.overall_score * 100)}  "
            f"{r.candidate} — {r.overall_score * 100:.1f}/100"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall", f"{r.overall_score * 100:.1f}")
            c2.metric("Skill coverage", f"{r.skill_score * 100:.1f}")
            c3.metric("Semantic match", f"{r.semantic_score * 100:.1f}")

            cols = st.columns(2)
            with cols[0]:
                st.markdown("**✅ Matched skills**")
                if r.matched_skills:
                    st.write(", ".join(r.matched_skills))
                else:
                    st.caption("None.")
                st.markdown("**➕ Extra skills**")
                if r.extra_skills:
                    st.write(", ".join(r.extra_skills))
                else:
                    st.caption("None.")
            with cols[1]:
                st.markdown("**❌ Missing skills (from JD)**")
                if r.missing_skills:
                    st.write(", ".join(r.missing_skills))
                else:
                    st.caption("None — full coverage.")

    # --- downloads ---
    st.markdown("---")
    st.subheader("⬇️ Export")
    excel_bytes = build_excel_report(
        results,
        job_title=job_title or "Job Description",
    )
    csv_bytes = pd.DataFrame([r.as_row() for r in results]).to_csv(index=False).encode("utf-8")

    d1, d2 = st.columns(2)
    d1.download_button(
        "Download Excel report",
        data=excel_bytes,
        file_name="resume_screening_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    d2.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="resume_screening_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

else:
    st.info(
        "Provide a JD and resumes (or keep sample mode on), then click **Screen resumes**.",
        icon="👈",
    )
