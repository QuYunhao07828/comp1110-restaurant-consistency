# Main sample review and final statistics

## Separate the two review tasks

The 60 candidate-pair A/B review evaluates the fixed matching workflow. It does not establish the final counterpart for all 100 branches. This workflow imports the separate 200 branch/source declarations and creates versioned coverage and field-agreement tables. It neither supplies independent reference labels nor computes precision, recall or F1.

Keep the baseline, frozen evaluation inputs and filled originals unchanged. Do not use an AI suggestion column as a completed review declaration. AI assistance is permitted by the supplied course guidance but must be disclosed and actually checked by students.

## Prepare a blank handoff

```powershell
python -X utf8 scripts/finalise_main_review.py prepare --output-dir outputs/main_review_new_batch
```

This writes `main_review_template.csv` with exactly 200 rows, one for each fixed branch and OSM/Overture. The identifying fields are prefilled; decision, chosen record, evidence, reviewer, date and AI-use flag are blank. It creates no completed judgements or metrics. Team members may filter by district and return separate CSVs; their union must contain all 200 tasks exactly once.

The columns are `branch_id`, `source`, `district`, `pilot`, `name`, `address`, `decision`, `record_id`, `evidence_and_reason`, `reviewer_name`, `reviewed_at`, `ai_assisted`. Preserve IDs as text and dates in ISO format. `ai_assisted` must explicitly be `true` or `false`.

Use one of these decisions:

- `Confirmed`: supply the exact selected record ID from that source snapshot and a concrete reason.
- `Uncertain`: explain the unresolved identity, suite, alias or duplicate issue. A tentative ID may be retained but will not be counted as a confirmed counterpart.
- `No counterpart confirmed`: leave the selected ID blank and document what was checked. This is not proof that the source contains no restaurant record.

The four district AI workbooks remain separate assistance views, each with 40 non-pilot tasks and ten deferred pilot tasks. If suggestions are accepted or corrected, retain the filled original and transcribe the final explicit record ID and evidence into the standard declaration format. The human reason must identify the exact accepted ID; multiple tentative suggestions do not select one automatically. Declare AI assistance as true for decisions reviewed with these materials. Never guess a corrected ID from prose or replace an actual student's original answer. Do not inspect or use protected pilot reference decisions to tune rules before the real freeze.

## Import completed declarations

```powershell
python -X utf8 scripts/finalise_main_review.py analyse --reviews returned_district_1.csv returned_district_2.csv returned_district_3.csv returned_district_4.csv --freeze data/review/freeze01/freeze.json --reviewer-a returned_A.xlsx --reviewer-b returned_B.xlsx --output-dir outputs/main_review_analysis01
```

Paths above are examples, not files that already contain completed work. The command requires a genuine freeze verified by the independent-review workflow and both unchanged original A/B files. It checks source-field files against the retained evidence-package manifest. It rejects unknown or duplicate branch/source tasks, incomplete rows, missing AI-use declarations, unknown source IDs and the same source record being confirmed for multiple sample branches. A compound venue may legitimately remain uncertain rather than being forced through the duplicate gate.

## Outputs and interpretation

- `reviewed_links.json` and `.csv` preserve the supplied review declarations.
- `coverage.csv` gives confirmed, uncertain and no-counterpart-confirmed counts, the full sample denominator and reviewed-link coverage, pooled and by district.
- `field_observations.json` contains all 1,800 branch/pair/field states. Only confirmed counterpart pairs are compared.
- `field_summary.csv` shows all five comparison states and the Agree + Disagree denominator. Zero comparable observations give unavailable agreement, not zero or perfect agreement.
- `main_summary.json` records input hashes, declared AI assistance, scope and limitations. Independent validation metrics remain absent; the genuine 39-pair evaluation output is separate.

Schema non-comparability takes precedence over missingness. Missing comparable values are Unavailable; unconfirmed links are Ambiguous match; normalised address inequality is Disagree but not proof of a location error. FEHD does not acquire phones, cuisine, hours or live status merely because another source supplies them.

Review declarations and names are supplied evidence, not software proof of actual human work. Report AI assistance, uncertainty, selection bias and the four-district sampling boundary. Do not label these outputs universal platform accuracy or Hong Kong-wide coverage.

## Verification

`scripts/test_main_review.py` checks the declaration and denominator logic, pilot gate, source-package tampering, blank templates, overwrite refusal and a full isolated synthetic workflow. The synthetic freeze gate is mocked only in the test harness; those fixtures are temporary, excluded from project outputs and never treated as study findings. No real main-sample final analysis has run until genuine completed inputs exist.
