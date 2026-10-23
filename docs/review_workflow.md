# Independent review and frozen evaluation

Implemented on 23 October 2026. No genuine reviewer files, adjudications, freeze or evaluation result have yet been supplied or created. The commands below describe future execution after actual human work. Tests use isolated fixtures, not research findings.

## What is measured

The 60 deliberately selected pairs contain 21 calibration pairs from seven branches and 39 label-held-out pairs from thirteen other branches. The inspected K11 rule-development branch belongs only to calibration. Pilot feature inspection has already occurred, so this is a holdout of reference labels, not a wholly untouched external test dataset.

The binary rule being evaluated is **automatic acceptance of this exact candidate link**: an automatic proposal for this branch/source/candidate is positive, and every other machine state is non-acceptance. Review-needed is not a human judgement that the pair is a non-match. Counting abstention/non-acceptance as a negative prediction measures the recall of the automatic-acceptance workflow, rather than recall of every candidate ever retrieved.

Reference labels are the two real reviewers' unchanged judgements, supplemented by documented third-person adjudication where they differ, either is Uncertain, or an agreed label is overridden. Adjudication may legitimately remain Uncertain. Such pairs are excluded from classification metrics and explicitly counted.

Outputs retain TP, FP, FN, TN, excluded uncertainty, precision/recall denominators, precision, recall and F1. A zero denominator produces unavailable (`null`), not an invented perfect score. F1 is calculated as 2TP/(2TP+FP+FN) when its denominator is nonzero. Original three-category reviewer agreement and unweighted Cohen's kappa are reported separately from the adjudicated reference. Kappa is unavailable when chance agreement makes the formula undefined.

These are **pair-set metrics**, pooled and by source. They are not whole-platform accuracy, unbiased Hong Kong-wide quality, end-to-end candidate retrieval recall or validated coverage of the 100 branches. The 40 pilot missed-candidate searches and the main-sample link review remain separate requirements.

## 1. Independent completion

Two different actual members independently complete the same 60-pair A/B files. They must not consult machine scores, the split administrator file or one another's decisions. Preserve original files. They may finish all rows before calibration, but the analyst must not inspect held-out answers before freezing. An actual manager must attest this at freeze time; the software cannot certify human independence or that nobody previously viewed a label.

Use ISO dates or actual Excel date cells. Do not backdate. Evidence is mandatory. Blank/partial inputs are rejected. Baseline matching, split regeneration and workbook generation now stop when supplied human review inputs or a returned batch would be overwritten. Keep additional backups nonetheless.

## 2. Import and adjudicate calibration only

Example PowerShell commands below assume Python with `requirements.txt` installed, and execution from the project root. `returned_A.xlsx` and `returned_B.xlsx` are the genuinely completed files. Paths are examples, not files that currently contain completed work.

```powershell
python -X utf8 scripts/ingest_reviews.py returned_A.xlsx returned_B.xlsx --output-dir data/review/batch01
```

This checks 60 original IDs and required inputs in both files, but exports only `batch01/calibration_adjudication.csv`, containing 21 pairs. Do not open or discuss held-out labels during calibration.

Keep every A_/B_ column and original pair metadata unchanged. If both reviewers agree on Match or Non-match, their consensus is usable without inventing a third person's approval. For disagreement, any Uncertain judgement, or an override of consensus, a third person must fill `adjudicator_name`, `final_decision`, `adjudication_evidence`, and `adjudicated_at`. The adjudicator must differ from both reviewers. The recorded date must not predate either review.

Evaluate calibration examples and document any method changes. If the rule changes, create a versioned analysis copy and recompute its outputs without regenerating or relabelling the fixed 60-pair review set. This is not permission to change difficult reference labels, remove failed sample branches or tune using held-out answers. The freeze checks that configuration, weights and saved link decisions are mutually consistent. Current outputs remain the original pre-human-calibration baseline.

## 3. Record an actual freeze

After calibration and any necessary recomputation, use the final code/data version, the unchanged original reviewer files and completed calibration CSV:

```powershell
python -X utf8 scripts/evaluate_reviews.py freeze --reviewer-a returned_A.xlsx --reviewer-b returned_B.xlsx --adjudication data/review/batch01/calibration_adjudication.csv --owner ACTUAL_MANAGER_NAME --note "Describe the actual calibration outcome and rule changes, or explain why no change was made" --attest-held-out-unseen --output-dir data/review/freeze01
```

Replace the owner and note with actual information. Do not run the attestation if the analyst already inspected held-out labels. In that case, disclose the leakage and reserve new independent reference cases before calling a later result a test.

The freeze records the actual current timestamp, input hashes and bindings for matching code, configuration, candidate/decision tables and review split. It neither exports held-out labels nor computes test scores. It requires a new output directory and never overwrites the original labels. A freeze is a workflow record, not cryptographic proof that a human declaration is true.

## 4. Open and adjudicate the held-out labels

```powershell
python -X utf8 scripts/evaluate_reviews.py prepare-held-out --reviewer-a returned_A.xlsx --reviewer-b returned_B.xlsx --freeze data/review/freeze01/freeze.json --output-dir data/review/heldout01
```

This verifies that the frozen rule, split, data and original reviewer files have not changed, then exports 39 rows to `heldout01/held_out_adjudication.csv`. Resolve required cases with the same evidence-preserving rules. Do not tune the matching procedure after viewing these labels and then reuse this set as a fresh evaluation.

## 5. Calculate bounded evaluation results

```powershell
python -X utf8 scripts/evaluate_reviews.py evaluate --reviewer-a returned_A.xlsx --reviewer-b returned_B.xlsx --freeze data/review/freeze01/freeze.json --adjudication data/review/heldout01/held_out_adjudication.csv --output-dir data/review/evaluation01
```

Only valid real inputs and unchanged frozen rules can reach this stage. It creates `evaluation.json` with denominators and scope limits, and `held_out_pair_results.csv` for traceability. No such result currently exists for the study. Rule or input changes after freezing are refused. If an error is found later, preserve the original run, disclose the reason, version the correction and assess whether a genuinely fresh evaluation is needed.

## Remaining study work

- Complete the 40 pilot source searches with actual names, searches and evidence. Do not call a negative search proof of absence.
- Resolve main-sample branch links before claiming validated 100-branch coverage or field agreement. The 60 candidate labels alone do not validate all 200 branch/source links.
- Rebuild the final tables and report from the appropriate validated analysis version. The existing report and spreadsheet remain explicitly provisional, and are not automatically promoted to final by running these tools.
- Obtain STA feedback and the later official report/presentation requirements. Logs, reflections and contribution claims require the actual students' input.

## Verification

Run `python -X utf8 scripts/test_evaluation.py`, `python -X utf8 scripts/test_reviews.py` and `python -X utf8 scripts/audit.py`. The evaluation suite covers metric boundaries, uncertainty, original-label preservation, independent adjudication, safe regeneration, the freeze/reveal/evaluate sequence, stale predictions and tamper detection. Isolated synthetic fixtures are kept under `tmp/review_tests`, removed by the test harness, and excluded from evidence packaging. They are never saved as completed study labels or results.
