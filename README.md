# Hong Kong restaurant information consistency

COMP1110 research project following the submitted optimised project plan.

## Public source repository

https://github.com/QuYunhao07828/comp1110-restaurant-consistency

The owner explicitly approved public code publication on 23 October 2026. This repository contains source code, method documentation and static interface files only. It does not contain raw snapshots, processed study tables, reviewer files, generated reports, credentials or local dependencies. References below to data and deliverables describe the separate dated evidence package, not files included in a source-only clone. Restore that package locally or complete a new versioned acquisition before running data-dependent analysis and tests. Publishing this code does not change the existing demonstration Site's private access or establish completed human validation.

## Scope

Compare branch identification, record coverage and comparable business fields across FEHD, OpenStreetMap and Overture Places. The target is 100 FEHD branches: 25 each in Central and Western, Wan Chai, Yau Tsim Mong and Sha Tin. A reproducible 20-branch pilot is the first milestone.

All observations must retain actual retrieval times. No ratings, review text or personal reviewer data are in scope. Differences are evidence of inconsistency, not proof of which source is correct.

## Evidence and human review

Scripts and machine suggestions do not establish human validation. Two actual group members must independently label the validation pairs and document adjudication. Their names, decisions and contributions remain blank until completed by those people. Precision, recall and F1 remain unavailable until suitable reference labels and evaluation denominators exist.

Actual catch-up work was performed on 23 October 2026. See `docs/STATUS.md` for verified completion and remaining work, and `docs/START_HERE_CN.md` for the group handoff.

## Deliverables

- `outputs/study_2026-10-23/STA_Meeting_Briefing_2026-10-23.docx`: current evidence and meeting script.
- `outputs/study_2026-10-23/Research_Report_Working_Draft.docx`: substantive research working draft, not a validated final submission.
- `outputs/study_2026-10-23/Research_Workbook.xlsx`: sample, link suggestions and formula-based agreement denominators.
- `outputs/study_2026-10-23/Independent_Reviewer_A.xlsx` and `Independent_Reviewer_B.xlsx`: blank blinded human-review inputs.
- Private demonstration: the owner retains the access link separately. The private address and deployment identifiers are not published in this source repository.

## Evidence structure

`data/raw` contains cached snapshots, `data/provenance` contains retrieval times and checksums, `data/processed` contains derived tables, and `data/review` contains original review templates and the administrator-only split. Raw data and outputs are excluded from Git, but included in the evidence archive. `docs/references.json` and `docs/literature_audit.md` document nine substantive sources and the bounded originality claim.

## Reproduction

Use Python 3.12. The matching code adds `.vendor` to its import path, but a normal virtual environment with the same requirements also works. Install dependencies with `python -m pip install -r requirements.txt`. For the bundled runtime used here, DuckDB 2.0.0 and RapidFuzz 3.14.6 are in the local `.vendor` folder. It is not distributed as source.

Using the included snapshots, run these commands from the project root:

```powershell
python -X utf8 scripts/audit.py
```

The audit checks lineage, accounting and rule regressions. It does not establish real-world matching accuracy. To recompute the baseline analysis, use a separate copy of the project before filling the human forms:

```powershell
python -X utf8 scripts/sample.py
python -X utf8 scripts/analyse.py
python -X utf8 scripts/audit.py
python -X utf8 scripts/build_reports.py
```

The analysis generator writes empty review templates. Never rerun it over completed human-review files. After real labels exist, retain them as immutable inputs and use a versioned analysis directory. `scripts/ingest_reviews.py A.xlsx B.xlsx --output-dir data/review/returned_batch_01` validates all 60 original pairs in each completed file and exports only the 21 calibration rows for initial adjudication. It refuses blank/incomplete files, changed candidate IDs, duplicate pair IDs and the same named reviewer. It does not certify independence or fabricate adjudications. Freeze calibrated rules before examining the remaining reference labels.

New acquisition (network required) starts with `scripts/acquire.py all`, then `scripts/extract_overture.py`, `scripts/sample.py`, and `scripts/acquire_csdi.py`. Cached snapshots are reused. Use a new dated project/snapshot directory for a later study date, and do not silently replace this evidence. FEHD CSDI acquisition uses Windows system certificate trust through PowerShell; TLS verification is not disabled. Overture extraction uses DuckDB's httpfs extension. The original OSM response's unnecessary editor metadata was minimised with a documented transformation; future acquisition omits it.

The JS artifact builders use the Codex bundled `@oai/artifact-tool` and `sharp` packages. `scripts/build_site.mjs` assembles the static site payload and figures, and `scripts/build_workbooks.mjs` builds and verifies the spreadsheets. `scripts/build_reports.py` uses python-docx. The managed Site's identity is in `site/.openai/hosting.json`; do not create a second Site for the same project. Deployment credentials are not included in this evidence archive.

## Important limits

The 100 branches are an equal-quota four-district sample, not representative of all Hong Kong. FEHD is a licensing frame, not a live operating-status authority. OSM and Overture raw extracts use different category populations, so their raw totals cannot be compared as restaurant coverage. Exact address disagreement is a text-representation difference, not proof of a wrong location. Fields used to select links bias conditional agreement.

The K11 mall-suffix development example is reserved for calibration. Pilot features were inspected during development, so the remaining reference-label holdout is not an untouched external test. See `data/review/review_protocol.json`.

The post-review workflow is implemented in `scripts/evaluate_reviews.py`: it validates calibration adjudication, records an actual rule/data freeze, opens held-out labels only after checking that freeze, and evaluates automatic-link acceptance with explicit denominators. It refuses changed frozen inputs and preserves the original judgements. See `docs/review_workflow.md` for exact commands and scope. No genuine study freeze or evaluation has occurred yet. `scripts/test_evaluation.py` exercises this workflow using isolated non-study fixtures and checks the current saved decisions against the executable rule. `scripts/review_safety.py` protects filled review inputs from baseline regeneration.

No STA feedback or detailed final-report rubric has been received. Individual logs, reflections, review judgements and contributions require genuine student input. The connected repository for another course was not modified.

## Data attribution

FEHD / HKSAR Government / DATA.GOV.HK; © OpenStreetMap contributors under ODbL; Overture Maps Foundation and the upstream sources retained in each record, with their applicable licence notices. See `docs/methodology.md` and the official attribution links there. This project does not replace upstream database licences with a software licence or imply source endorsement.
