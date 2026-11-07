# Verified project status

This record describes current evidence, not retrospective claims of work on earlier planned dates.

## Immediate milestone

Current update on 8 November 2026 takes precedence over the historical updates below. Two completed reviewer forms, each containing the same 60 original pairs, have been preserved and strictly imported after one owner-confirmed input correction. The owner reports independent completion without shared answers or machine suggestions. A source-field audit also found 17 originally blank candidate-address cells replaced by a numeric value in each returned form; those are not source addresses and the retained snapshots remain authoritative.

Only the 21 calibration pairs have been exported: 16/21 raw agreement (76.2%), unweighted three-class Cohen's kappa 0.561, five disagreements and one additional agreed pair flagged for source-evidence review. These are calibration reviewer-agreement measures, not algorithm accuracy. Genuine third-person adjudication, rule lock and evaluation are still pending. A known label disclosure before locking is retained in the private correction record; the new retrospective evaluation mode avoids an inaccurate unseen-label attestation and retains all original evaluation cases.

The owner reports only the Yau Tsim Mong main review returned; its revised sheet contains 50 candidate-level judgements (17 Match, 33 Non-match). These do not establish source-wide absence for rejected candidates and do not complete the 40 pilot candidate-miss searches. Other district assistance is not signed human review. Member contributions are deferred at the owner's request and remain required for final submission.

All three final submission guidelines have now been read. See `final_submission_requirements.md`; the report is self-contained, code is not submitted for marking, all five members speak in the ten-minute presentation, and a GenAI declaration with exact incorporated prompts is required in the report. Full historical transcript submission is not required. Actual personal reflections and contribution histories are not fabricated.

The following paragraphs and table retain the 2 November and 23 October historical state. They must not be read as current claims that no forms or final guidelines have arrived.

Update on 2 November 2026: the owner requested AI-assisted review rather than checking every source row alone. Evidence preparation has run for the 40 non-pilot Sha Tin branch/source tasks, retaining broader retrieval separately from the baseline and leaving all human inputs blank. Ten pilot tasks remain deferred. No independent human labels, adjudication, genuine freeze or validated metrics have been supplied to this workspace. The private evidence and assistance outputs are separate from public source publication. See `docs/ai_assisted_review.md`; the assistance does not complete the original validation commitment.

The owner also supplied instructor/TA guidance permitting substantive GenAI assistance while requiring student correctness checks and Final Report tool/prompt disclosure. The Project Plan disclosure waiver does not extend to the Final Report. A checklist is in `docs/ai_use_disclosure.md`; the later final guideline clarifies the exact-prompt requirement without requiring a complete transcript. Genuine student verification remains necessary.

The separate full-sample import and summary workflow is now implemented in `scripts/finalise_main_review.py`, with 22 isolated tests. A blank 200-task handoff is prepared; it is not 200 completed reviews. The importer requires the real independent-review freeze, checks source fields against the retained package, rejects incomplete/duplicate declarations and preserves reviewed-link coverage and field-specific denominators in a new output version. No genuine final main-sample analysis has been run. See `docs/main_review_workflow.md`.

Produce the evidence required for the 20–24 October interim meeting: schema and licence review, reproducible sampling, 20-branch pilot, source extraction, matching tests, validation materials and a progress briefing.

## Full project requirements

- Preserve the submitted research question and four districts.
- Retain source snapshots, source/release dates, retrieval timestamps and checksums.
- Document actual schema coverage and comparability.
- Select 20 pilot branches and a reproducible 100-branch main sample.
- Implement explainable candidate generation, normalisation and scoring.
- Prepare at least 60 candidate pairs for two independent human reviewers, with calibration and held-out evaluation kept separate.
- Check candidate-generation misses for all 20 pilot branches.
- Report missingness separately from disagreement, with numerator and denominator.
- Produce supported analysis, figures and an interface with provenance and uncertainty.
- Complete the final report, presentation and permitted supporting materials against the course requirements.
- Keep individual reflections and contribution claims tied to actual group-member work.

## Current evidence

Actual catch-up date: 23 October 2026. No acquisition, meeting or human review is backdated to the original plan.

| Item | Evidence now available | Status |
| --- | --- | --- |
| Course and literature review | Supplied guidelines audited; nine substantive sources with verification notes | Prepared; later final-report rubric not supplied |
| FEHD frame | 17,271 licence records; 7,593 in the four district groups | Acquired |
| Sampling | Fixed hash selection, 20 pilot and 100 provisional main branches | Prepared |
| FEHD spatial support | 99 sample licence IDs joined exactly to official CSDI distribution; 99 normalised addresses agree | Acquired, not positional ground truth |
| External snapshots | 7,679 OSM food amenities; 153,821 all-category Overture places in the search box | Acquired; totals have different populations |
| Matching | Explainable normalisation, blocking, score and ambiguity handling; 2,206 saved pairs | Initial implementation |
| Pilot proposals | OSM 3 automatic / 9 review / 8 weak; Overture 7 automatic / 10 review / 3 weak | Unvalidated |
| Independent review | Two separate blank 60-pair files; 21 calibration / 39 label-held-out; K11 development case excluded from evaluation | Prepared; 0 human pairs complete |
| Post-review validation workflow | Input protection, calibration adjudication checks, actual freeze, guarded held-out opening, scoped pair-set metrics and isolated tests | Implemented; no real human freeze or evaluation yet |
| Pilot candidate-miss searches | 40-row template for 20 branches × two external sources | Prepared; not performed by group members |
| Tables and figures | 1,800 provisional field observations, explicit denominators and two status figures | Provisional |
| Meeting material | English script, current counts, cases, questions and Chinese handoff | Prepared |
| Website | Search, sample/district filters, side-by-side evidence and browser-local review/export | Deployed privately; core interactions checked |
| Final report | Working draft using real snapshots and nine numbered background sources | Not a final validated submission |
| STA feedback and final rubric | User confirms none received so far | Awaiting external information |
| Personal contributions/logs/reflections | Must be supplied by actual students | Not fabricated |

## Next human-dependent steps

Two different group members independently label the same 60 pairs; a third resolves disagreements and uncertain cases. Complete 40 pilot source searches. Use calibration labels first, document any rule changes and freeze the configuration before examining held-out labels. The held-out set reserves reference labels, but pilot features were inspected during development, so it is not a wholly untouched external test set. Complete the main sample adjudication before reporting validated coverage or agreement. Obtain STA feedback and the later official report instructions.

The evidence package provides the computational catch-up work and a usable meeting handoff. It does not make the original 11–19 October human-review commitment complete. Precision, recall and F1 remain unavailable.

The demonstration Site remains private; its address and deployment identifiers are retained separately rather than published here. The other-course GitHub repository previously seen was not modified. The user created https://github.com/QuYunhao07828/comp1110-restaurant-consistency and explicitly approved public code publication on 23 October after its Public visibility was explained. The initial contents write was refused with HTTP 403, `Resource not accessible by integration`. Following the user's authorisation, the connected application installation list now includes `QuYunhao07828`. Source publication and remote verification are tracked in the local `docs/github_publication_receipt.json`; account connection alone is not proof of an uploaded commit. Only code, method documentation and static interface files are in publication scope. Study data, human inputs, private Site configuration and personal local paths are excluded. Publishing code does not establish research completion.
