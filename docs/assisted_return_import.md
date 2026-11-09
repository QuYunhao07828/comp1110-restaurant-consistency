# Import filled district assistance workbooks

This administrator step converts the supplied human I-L fields into standard main-review declarations. It preserves the received workbook and the original AI notes. It does not supply a human reviewer, independent labels, a rule lock, pilot search results or final coverage.

The group can return the same district XLSX already distributed. No new workbook or extra candidate-copying task is required. Keep the unfilled original and its `triage.json` alongside the returned copy. A source-only GitHub clone does not contain these private study inputs; restore the complete project package first.

## What the student enters

- Choose the actual decision in I, give concrete evidence in J, enter the actual reviewer in K and actual review date in L. A completed-field counter is not factual verification.
- If `Confirmed` accepts the single ID already displayed in F, a normal evidence note in J is sufficient.
- If F is empty, offers several IDs, or the student chooses another record, start J with `ID=<exact record ID>; <actual evidence>`. A Chinese semicolon or a newline also separates the ID and reason. Example syntax only: `ID=node/123456; building and unit evidence checked`. This example is not a study judgement.
- `Uncertain` stays unconfirmed. Without an explicit `ID=` statement, the import leaves its selected-ID field empty; it does not copy an AI ID into a student selection. An explicit tentative ID can be retained with the unresolved reason.
- `No counterpart confirmed` clears the selected ID. Explain the bounded search and unresolved evidence; this does not prove source absence. Do not also enter an `ID=` selection.
- Keep A-H intact. Put a correction in J rather than rewriting the retained source or AI evidence. Dates for a new assisted review cannot precede the assistance date. Earlier unassisted returns remain separate evidence.

## Administrator command

Example for a genuinely filled Wan Chai return, using a new output directory:

```powershell
python -X utf8 scripts/import_assisted_returns.py --original outputs/assisted_main_2026-11-09/WanChai/WanChai_AI_Assisted_Review.xlsx --triage outputs/assisted_main_2026-11-09/WanChai/triage.json --returned received/WanChai_completed.xlsx --output-dir outputs/returned_wan_chai_new_batch
```

The returned path is an example, not an assertion that this file has arrived. For Sha Tin, use the retained 2 November workbook and companion notes. Use the matching district paths for the other forms. The old 50-row Yau Tsim Mong return is a different layout and is not accepted by this adapter; preserve its original and audit trail.

The reader supports valid XLSX files without an optional worksheet dimension element, calculating the extent from actual cells without editing the file. It rejects changed headers, changed A-H fields, missing or duplicate tasks, formulas in human fields, incomplete declarations and dates before assistance or in the future. It binds the reference form to the fixed non-pilot sample and AI notes, and checks selected IDs against the correct retained source snapshot. An explicit newly found ID may be outside the AI shortlist, provided it exists in that source snapshot. Several IDs cannot silently select the first.

## Outputs and remaining gates

Successful import writes `nonpilot_review_declarations.csv` and `import_receipt.json` in a new directory. The CSV declares AI assistance as true. The receipt binds the original form, return, notes and source files by hash; input files remain unchanged. Software checks these declarations and their structure, not the identity or actual work of the named reviewer.

Each real district form contains 40 non-pilot tasks. Four such returns account for 160 tasks, leaving the 40 pilot tasks separate. The final 200-task workflow still requires the genuine independent-review lock and complete explicit declarations. See `docs/main_review_workflow.md`. No coverage, precision, recall or F1 is produced by this adapter.

Sixteen isolated tests cover conversion, source binding, changed evidence, explicit ID selection, uncertainty, dates, formulas, missing worksheet dimensions, overwrite refusal and a temporary end-to-end fixture. The four actual unfilled district files were separately read and bound to their retained notes; all were rejected as completed returns and remained unchanged. No real completed district declaration was created in those checks.
