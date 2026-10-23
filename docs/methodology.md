# Sampling matching and independent review protocol

Version: pilot v1. Actual acquisition date: 23 October 2026. Changes after calibration must be versioned; do not change the held-out reference labels to improve measured performance.

## Population and sampling

The FEHD English and Traditional Chinese XML files are joined by LICNO. The 23 October extract contains 17,271 licence records. The target frame contains 7,593 named, addressed records in Central and Western (18), Wan Chai (12), Yau Tsim plus Mong Kok (61 and 62), and Sha Tin (97). Exact normalised name/address duplicates would be grouped while preserving licence identifiers; no such duplicates were found in this frame. Different aliases or suites may still need review.

The seed is `COMP1110-2026-FOUR-DISTRICTS-v1`. Within each district, sort ascending by SHA256 of the seed, district, normalised name and normalised English address. The first five branches form the pilot; the first 25 form the provisional main sample. The pilot is a subset of the main sample. The sample was fixed before matching outcomes were inspected. Missing source matches are retained. Equal district quotas do not represent Hong Kong's population distribution.

The sampling unit is an observed licensed business/premises group, provisionally treated as a branch. Compound venue names, hotel facilities and overlapping suites may expose a mismatch between licence and branch granularity. Document these rather than quietly removing them.

## Acquisition and provenance

- FEHD XML: original English and Chinese files, schema and generation dates are retained. Licence expiry does not prove operation.
- FEHD CSDI is an additional official distribution of the same FEHD source, not a fourth independent source. `SEARCH02_EN` is joined exactly to XML `LICNO`; 99 of 100 sampled licences have a returned spatial feature, and all 99 have the same normalised English premises address. Retain LASTUPDATE. CSDI geometry in WGS84 is supporting location evidence, not positional ground truth. No commercial geocoding is used.
- OSM: nodes, ways and relations with amenity restaurant, cafe, fast_food, food_court, bar, pub or ice_cream, in the bounding box 113.80–114.45 E and 22.15–22.60 N. Way/relation centres are not necessarily entrance locations. The box extends outside Hong Kong; the raw count is not a Hong Kong restaurant count. Disused-only amenities can be missed by this query.
- Overture: release 2026-10-21.0. STAC partition bounding boxes select the overlapping Parquet partition, then DuckDB filters point bbox coordinates to the same search box. All place categories are retained to allow inspection of category errors. This is not the same raw population as the food-only OSM extract. The JSON subset is preserved with the SQL, source partition URLs, STAC metadata and checksum.
- Retrieval records contain actual UTC times, URLs, response headers and SHA256 hashes. UTC+8 is used for the meeting date. Retrieval, source release, object edit and business-change times are distinct.
- Unnecessary OSM public editor identifiers were removed from the initial snapshot. Its provenance records the transformation and both upstream-response and retained-file hashes. No review text or reviewer identities are collected. Human validation names are supplied only by the actual reviewers.

## Normalisation and features

Preserve original values. NFKC normalisation, case folding, punctuation-to-space and whitespace collapsing produce comparison strings. Names retain alternative language variants where supplied. The name feature is the largest ratio/token-sort similarity across variants. Token-set similarity is discounted and allowed only when the shorter name has at least four characters and at least 65% of the longer name's length; this prevents a short mall/location suffix from replacing the full business name.

Address comparison also standardises common English terms such as road/rd, street/st, avenue/ave, building/bldg and Hong Kong/hk. These replacements do not translate Chinese addresses, resolve unit equivalence or establish a canonical premises identifier. Missing address detail remains missing. Phone strings are normalised to valid eight-digit Hong Kong numbers with +852, when possible; unsupported formats are not guessed.

Candidate generation is the union of records within 750 m of an available FEHD CSDI point, exact normalised name hits anywhere in the search box, and up to eight fuzzy name variants scoring at least 86/100. The geographic block is not used as an exclusive filter. The saved candidate table retains the top 12 by score for each branch/source.

Initial score weights are name 0.55, address 0.25 and distance 0.20, renormalised across available features. Distance similarity is exp(-(distance_m/150)^2). FEHD supplies no phone, so phone is not a feature in its pair scoring. These are transparent heuristic starting values, not learned probabilities or a reproduction of a published weighting method.

An automatic proposal requires score at least 0.82, name similarity at least 0.84, distance at most 200 m, and a score margin of at least 0.08 over the next candidate. Missing location evidence cannot produce an automatic proposal. Duplicate source-record assignments are downgraded to review. Other cases are review-needed or no-strong-candidate; these states do not prove source absence.

## Two independent reviewers and adjudication

Sixty candidate pairs are prepared: each pilot branch's highest-ranked OSM and Overture candidates, plus its strongest alternative across the two sources. This purposeful set contains difficult and competing candidates; it is not a prevalence-weighted random sample of all pairs. Pairwise performance on it must not be represented as an unbiased whole-source accuracy estimate.

Seven pilot branches (21 pairs) are assigned to calibration and 13 (39 pairs) to label-held-out evaluation. The inspected K11 mall-suffix development case is reserved for calibration. Six remaining calibration branches follow the fixed `review-split-v1` branch hash; the remaining 13 branches supply held-out reference labels. This revision was recorded before any independent human labels were received. Splitting by branch avoids placing the same branch in both sets. Pilot features and machine outputs have already been inspected during development: this is a reference-label holdout, not a wholly untouched external test set. State this limitation when reporting performance. The split and revision are stored in `data/review/review_protocol.json` and the admin file, and omitted from reviewer forms. Algorithm scores and proposed decisions are omitted from the independent forms.

1. Each reviewer completes their own file or browser form before comparing decisions. Enter their actual name, observation date, decision and supporting reason.
2. Use Match only when evidence supports the same business branch/premises. A shared brand or nearby point alone is insufficient. Use Non-match for distinct branches/entities. Use Uncertain for inadequate or contradictory evidence.
3. Preserve both original decisions. A third member adjudicates disagreements and uncertain cases, recording evidence and a final decision; do not overwrite the original columns.
4. Calibrate on the 21 calibration pairs only, freeze rules, then evaluate on the 39 held-out pairs. Report how Uncertain pairs are excluded and show their count.
5. Use the 40-row pilot miss-search form to inspect both sources for all 20 branches beyond the generated candidates. Record searches, located IDs, negative searches and unresolved cases. A negative search is not proof the source contains no record.

Precision = TP/(TP+FP), recall = TP/(TP+FN), and F1 uses the same labelled evaluation universe. These metrics remain unavailable until denominators exist. Distinguish pair-classification recall within the reviewed set from end-to-end retrieval recall. Candidate-miss checks are separate evidence about retrieval; they do not make the labelled set exhaustive.

## Coverage and agreement

Until independent review is completed, results are explicitly provisional automatic-proposal counts. They are not validated source coverage or accuracy. Once reviewed, report confident linked branches / sampled branches, with uncertain links separately.

For each field and source pair, report Agree, Disagree, Unavailable, Non-comparable and Ambiguous match. Agreement denominator = Agree + Disagree for comparable observed values under accepted links. Show all counts. Different normalised text is labelled Disagree, but does not necessarily denote a semantic contradiction or error; exact address equality is a conservative representation measure. More semantic address classes need documented review rules.

FEHD licence category is not cuisine or OSM/Overture venue category. FEHD phone/hours/operating-status comparisons are non-comparable. Overture Places has no general opening-hours field. Optional OSM values do not establish cross-source comparability. Category crosswalks are coarse and provisional; preserve raw labels and report unmapped values.

Names, addresses and positions also help select links, so their observed agreement is conditional on linkage and subject to selection bias. Avoid claiming that a high conditional rate proves source quality, or that low exact-address agreement proves incorrect locations. Do not infer business-change causes or identify a universally correct source.

## Reproduction

Use Python 3.12 with DuckDB 2.0.0 and RapidFuzz 3.14.6 installed in the project-local `.vendor` directory, plus the bundled document libraries for reporting. Run acquisition, `sample.py`, official CSDI acquisition, `analyse.py`, validation checks and deliverable builders in order. Keep raw snapshots unchanged apart from the explicitly logged metadata minimisation. Reruns against cached snapshots reproduce selection; a new-date acquisition needs a separately versioned snapshot and manifest.

## Data use and attribution

Attribute FEHD, the HKSAR Government and DATA.GOV.HK and avoid implying endorsement. Attribute © OpenStreetMap contributors and identify ODbL; derived database sharing requires the applicable terms, separate from code licensing. Attribute Overture and its per-record upstream sources and preserve CDLA Permissive 2.0 / Apache 2.0 or other source-specific notices. Publishing only a limited study extract does not remove attribution obligations. Record-level provenance is retained in the local evidence package.
