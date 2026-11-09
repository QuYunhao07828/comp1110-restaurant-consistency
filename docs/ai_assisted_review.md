# AI assisted evidence review

## Purpose and limits

On 2 November 2026 the owner requested direct assistance with the Sha Tin review tasks. The assistant can search snapshots, compare source fields, suggest counterparts, identify conflicting evidence and prepare questions. These are AI-assisted assessments, not judgements authored by two independent students. Neither AI suggestions nor a user's receipt of them establishes completed human validation.

The initial task was 40 branch/source combinations for 20 non-pilot Sha Tin branches. The latest project-wide request was carried forward on 9 November into three further district workbooks, 40 tasks each. The 120 new notes suggest IDs in 52 tasks, including unresolved cases, not confirmed matches. Four workbooks now cover 160 non-pilot tasks. The other five branches per district belong to the independent pilot set; their 40 source-search tasks remain deferred, not labelled or counted as completed searches. Obtain a documented rule freeze before exposing reference labels or using pilot findings to change rules. Do not open assistance workbooks during independent A/B labelling.

The supplied instructor/TA response permits substantive GenAI assistance, with student checking and mandatory Final Report disclosure. See `docs/ai_use_disclosure.md`. Independent reference review is a methodological commitment of this study, not a claim that the course bans AI analysis.

## Retrieval and assessment

Run from the project root with the dated evidence package and dependencies restored:

```powershell
python -X utf8 scripts/assist_review.py --output-dir outputs/NEW_ASSISTANCE_DIRECTORY
```

The helper retains the saved top 12 candidates and expands retrieval to records within 1,500 metres without the baseline name/category floor, plus source-wide name variants with fuzzy ratio at least 65 and up to 30 variants per alias. All retrieved evidence is preserved in the new directory. A display-priority sort is only for presentation, not the original match score, a calibrated rule or a probability. Retrieval is bounded; failure to confirm a counterpart does not prove absence from the source.

An assistant-authored `assessments.json` is a separate, preserved input containing case suggestions, selected record IDs, reasons, unresolved questions and dated supplementary source observations. It is not generated reference truth. Validate it using `validate_curation` in the helper before running:

```powershell
node scripts/build_assisted_workbook.mjs outputs/NEW_ASSISTANCE_DIRECTORY
```

This creates one workbook and `triage.json`, refusing an existing workbook or triage output. The workbook separates AI suggestions and source evidence from blank human decision, evidence, name and date fields. Its completion formula reports only that the human fields were filled and await administrator review, not that the research is validated. The case assessments and dated data are private project evidence and are not included in the public source export.

The builder accepts a third positional argument for a separate evidence directory. Set `RUNTIME_NODE_MODULES` or `CODEX_PRIMARY_RUNTIME_NODE_MODULES` to the configured bundled package directory when required. Curation dates are distinct from original retrieval dates and stored as typed Excel dates. Reading views preserve saved candidates plus selected broader evidence, with the full retrieval file date and hash; they are not exhaustive searches.

On 9 November the three saved XLSX files passed ZIP integrity, 40-task uniqueness, selected-ID membership, date, cached-counter and blank-human-input checks. Input, evidence and pilot views and the longest main rows were visually inspected. Native processes returned nonzero after writing completion output and files; actual saved-file checks were used rather than relying on a completion message. No human confirmations were created.

## Supplementary observations

Official brand or property directories may corroborate branch identity and telephone numbers. Record the actual observation date and link. A page observed on 2 November is not an immutable record of the 23 October snapshot. Keep it separate from the original source fields, do not backfill absent fields as though the source supplied them, and do not turn current operation into historical ground truth. Do not collect or copy customer reviews.

## Integrity and handoff

- Preserve original snapshots, matching configuration, saved decisions, A/B files and the fixed calibration/evaluation split. The helper hashes its input files before and after retrieval.
- Keep AI-assisted decisions outside `reviewer_A.csv`, `reviewer_B.csv`, the independent workbooks and adjudicated reference files. Do not use AI suggestions as a second independent reviewer.
- Use the existing 21-pair calibration, rule-freeze and 39-pair evaluation workflow with genuine independent input. If the group wants to replace that submitted commitment, seek STA approval and disclose the changed design instead of silently relabelling the same evaluation.
- A zero count of human labels remains zero after preparation. Source coverage, precision and recall are not validated by creating an assistance workbook.
- New source candidates and apparent duplicate records require separate traceable review. Do not change a frozen evaluation input or tune on held-out answers.

Tests in `scripts/test_assist_review.py` check selected-ID membership, protected pilot boundaries, duplicate task handling, preservation of supplied human fields and refusal of human-completion claims. They do not test real-world matching accuracy. `assessments.json` must remain with the private evidence package to reproduce assistant-specific suggestions; source code alone cannot reconstruct those authored decisions.
