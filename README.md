# Resume Screener ATS

Rank a stack of resumes against a job description in seconds.
Built for HR teams, recruiters, and hiring managers who need to triage
hundreds of applications without writing macros or paying for an enterprise ATS.

> **The business case:** A typical recruiter spends 6–8 seconds on each
> resume — and still misses qualified candidates. This tool produces a
> defensible, explainable shortlist with matched skills, gaps, and a
> downloadable Excel report that you can share with hiring managers.

---

## What it does

- Parses PDF, DOCX, and TXT resumes
- Extracts skills from a curated 200+ term taxonomy (tech, HR, business, soft skills, certifications)
- Scores each resume against the JD using a hybrid model:
  - **60% Skill Coverage** — share of JD skills found in the resume
  - **40% Semantic Match** — TF-IDF cosine similarity over 1–2 grams
- Produces:
  - An interactive ranked table in the browser
  - A per-candidate breakdown (matched / missing / extra skills)
  - A styled, color-banded Excel report with a Methodology sheet
  - A CSV export

Weights are tunable from the sidebar — slide them to favor keyword coverage
or semantic fit.

---

## Screenshots

> Place screenshots here once deployed:
> - `docs/img/01-upload.png` — upload + JD entry screen
> - `docs/img/02-ranking.png` — ranked results table
> - `docs/img/03-breakdown.png` — per-candidate breakdown
> - `docs/img/04-excel.png` — exported Excel report

---

## Tech stack

| Layer        | Tools                                           |
| ------------ | ----------------------------------------------- |
| UI           | Streamlit                                       |
| NLP / scoring| scikit-learn (TF-IDF + cosine similarity)       |
| Parsing      | pdfplumber, python-docx                         |
| Reporting    | pandas, openpyxl                                |
| Language     | Python 3.10+                                    |

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/<your-username>/resume-screener-ats.git
cd resume-screener-ats

# 2. Install
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

Then open `http://localhost:8501`. Sample mode is on by default — click
**Screen resumes** to see the demo ranking immediately.

### Run without the UI (CLI smoke test)

```bash
python -m scripts.run_demo
```

This loads the bundled JD + 3 sample resumes, prints the ranked scores,
and writes `output/demo_report.xlsx`.

---

## Project structure

```
resume-screener-ats/
├── app.py                       # Streamlit UI
├── requirements.txt
├── data/
│   └── skills_taxonomy.json     # Curated skill list (editable)
├── samples/
│   ├── job_description.txt
│   ├── resume_alice_kapoor.txt
│   ├── resume_ben_costa.txt
│   └── resume_chitra_menon.txt
├── screener/
│   ├── parser.py                # PDF/DOCX/TXT text extraction
│   ├── skills.py                # Skill extraction + coverage
│   ├── matcher.py               # Hybrid scoring engine
│   └── exporter.py              # Styled Excel report
└── scripts/
    └── run_demo.py              # CLI smoke test
```

---

## How scoring works

For each resume:

1. Extract clean text from the file.
2. Find every taxonomy skill present in the JD and the resume.
3. **Skill Coverage** = `|JD skills ∩ Resume skills| / |JD skills|`
4. **Semantic Match** = TF-IDF cosine similarity (`ngram_range=(1, 2)`,
   English stopwords removed, sublinear TF).
5. **Overall** = `0.6 × Skill Coverage + 0.4 × Semantic Match` (weights configurable).

Color bands in the Excel report:

| Band   | Score      |
| ------ | ---------- |
| 🟢 Green  | ≥ 70       |
| 🟡 Yellow | 40 – 69    |
| 🔴 Red    | < 40       |

---

## Customizing the skill taxonomy

The taxonomy lives in `data/skills_taxonomy.json` as a flat dict of
category → list of skills. Add, remove, or rename categories freely; the
matcher rebuilds its index on the next run.

```json
{
  "your_industry_skills": [
    "claims processing",
    "underwriting",
    "actuarial analysis"
  ]
}
```

This makes the tool re-targetable for any vertical (insurance, healthcare,
logistics, etc.) without code changes.

---

## Limitations and honest caveats

- Keyword-based scoring will miss synonym-only matches the TF-IDF layer
  can't recover. Always review the top candidates manually before
  scheduling interviews.
- PDF parsing quality depends on the source. Image-only PDFs (scanned
  resumes) will not extract text — use OCR upstream if needed.
- The taxonomy ships with ~200 skills. Tune it for your role family for
  best results.

---

## Roadmap

- [ ] Sentence-Transformers semantic layer (optional, GPU-friendly)
- [ ] Bias audit: show keyword presence by candidate name removed
- [ ] Multi-JD batch mode (rank a single resume against many roles)
- [ ] Docker image + Streamlit Cloud deployment guide
- [ ] OCR pipeline for scanned PDFs (pytesseract)

---

## License

MIT — fork it, use it, ship it.
