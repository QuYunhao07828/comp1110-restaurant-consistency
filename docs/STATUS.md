# Verified project status

This record describes current evidence, not retrospective claims of work on earlier planned dates.

## Immediate milestone

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
