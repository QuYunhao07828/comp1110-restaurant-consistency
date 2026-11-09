# Read only snapshot diagnostics

The diagnostic audit adds evidence about the retained matching workflow without reading reference labels or changing the rule. It does not supply adjudications or establish source accuracy.

```powershell
python -X utf8 scripts/diagnose_snapshot.py --output-dir outputs/snapshot_diagnostics_new_version
```

Restore the private dated evidence package first; a source-only clone does not contain study inputs. Use a new output directory. The command verifies the normalised source fields against the retained package, binds its inputs by hash and checks that they remain unchanged. It reproduces the saved baseline automatic proposals before producing any diagnostic output.

## Outputs

- `diagnostic_summary.json` records the input fingerprints, candidate-list limits, missing features and disclosed limitations.
- `candidate_diagnostics.csv` contains one row per fixed branch/source task, including empty lists. Saved lists stop at 12; a capped list is not an exhaustive source search.
- `snapshot_field_presence.csv` counts populated normalised fields against each full extract's own denominator. OSM food amenities and Overture all-category places are different populations. A field not supplied by a schema must be described as non-comparable rather than ranked as a conflicting value.
- `proposal_sensitivity.csv` displays a declared grid: score minima 0.78, 0.82 and 0.86 crossed with margin minima 0.04, 0.08 and 0.12. Name similarity at least 0.84, distance at most 200 metres and duplicate-record checks stay fixed. No reference labels are loaded, no optimum is selected and the baseline is not rewritten.

## Interpretation

Proposal count measures how often the specified rule accepts a candidate automatically. It is not verified source coverage, the accuracy of a platform, or evidence that a rejected first candidate has no counterpart elsewhere. Inspect uncertainty, missingness, the fixed sample and retrieval boundaries before interpreting the count.

Renormalising available score weights can make a missing address less penalising than an observed poor address. The additional name, distance and margin gates remain necessary. The diagnostics identify tasks affected by missing address features rather than pretending that a score is a probability.

The retained sample includes explicit missing-name markers. One has a genuine Chinese alternative; another has marker values in both languages and lacks coordinates. Do not use a marker as a business name or claim that a name-only fuzzy search provides identity evidence for the unidentified target. This parser limitation is disclosed without changing the fixed sample or baseline. Corrections to parsing or semantic address comparison belong in a separately versioned analysis.

`scripts/test_snapshot_diagnostics.py` uses isolated fixtures to check the four acceptance gates, alternative-candidate margin, duplicate assignments and full attribute-presence denominators. These are implementation checks, not research labels.
