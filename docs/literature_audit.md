# Literature and background audit

Checked on 23 October 2026, Asia/Shanghai. This audit verifies the five papers and three data sources cited in the submitted optimised plan, adds one closely related existing system, and limits the novelty claim using the work actually located. The nine substantive sources below fall within the course's suggested range of about 5-10. Licence and access pages are supporting documentation grouped with the relevant data source, not additional research studies.

## Source 1 - Sun et al. 2023

**Verified reference:** Sun, K., Hu, Y., Ma, Y., Zhou, R. Z., & Zhu, Y. (2023). Conflating point of interest (POI) data: A systematic review of matching methods. *Computers, Environment and Urban Systems, 103*, 101977. [DOI and publisher](https://doi.org/10.1016/j.compenvurbsys.2023.101977). An [author-hosted manuscript](https://www.acsu.buffalo.edu/~yhu42/papers/2023_CEUS_POIConflation.pdf) is also available.

The review organises POI matching similarity measures and classification approaches. It supports explaining why candidate generation, attribute comparisons, and a decision rule are distinct parts of matching. It does not establish optimal weights or a threshold for Hong Kong restaurants; those must be justified and checked locally. General POI conflation is established research, so using it is a method choice rather than the novelty claim.

## Source 2 - Zhao et al. 2022

**Verified reference:** Zhao, J., Niu, X., Cui, Y., Zhao, Y., Guo, M., & Zhang, R. (2022). POI point entity matching and fusion based on multi similarity calculation. *ISPRS Annals of the Photogrammetry, Remote Sensing and Spatial Information Sciences, X-3/W2-2022*, 87-92. [Publisher article and DOI](https://doi.org/10.5194/isprs-annals-X-3-W2-2022-87-2022).

The method combines spatial, name and address similarities and uses an analytic hierarchy process to weight features. This is a precedent for an inspectable multi-feature score. The student project may use a simpler documented heuristic, but should not claim to reproduce the published method unless its actual feature definitions and weighting procedure are implemented. The paper's performance figures do not predict this project's results.

## Source 3 - Yeow et al. 2021

**Verified reference:** Yeow, L. W., Low, R., Tan, Y. X., & Cheah, L. (2021). Point-of-interest (POI) data validation methods: An urban case study. *ISPRS International Journal of Geo-Information, 10*(11), 735. [Publisher and DOI](https://doi.org/10.3390/ijgi10110735).

The study reviews validation methods and applies a subset to four POI sources in a Singapore neighbourhood, considering completeness and positional and thematic quality. It supports reporting missingness separately from disagreement and explaining how matching affects evaluation. This is one close methodological comparison: our bounded study uses Hong Kong licensed restaurant branches and FEHD/OSM/Overture, rather than the paper's Singapore setting and source combination.

## Source 4 - Klinkhardt et al. 2023

**Verified reference:** Klinkhardt, C., Kühnel, F., Heilig, M., Lautenbach, S., Wörle, T., Vortisch, P., & Kuhnimhof, T. (2023). Quality assessment of OpenStreetMap's points of interest with large-scale real data. *Transportation Research Record, 2677*(12), 661-674. [Publisher and DOI](https://doi.org/10.1177/03611981231169280); [KIT repository](https://publikationen.bibliothek.kit.edu/1000158824).

The authors compare OSM with surveyed POIs in 49 German areas and examine completeness by category and context. This supports reporting coverage and avoiding a universal claim about OSM quality. Our sample is far smaller and lacks their field survey, so it cannot support comparable external accuracy claims or broad geographic generalisation.

## Source 5 - Liu et al. 2023

**Verified reference:** Liu, Y., Shi, W., Yu, Y., Peng, L., & Zhang, A. (2023). Evaluation of the resilience of the catering industry in Hong Kong before and after the COVID-19 outbreak based on point-of-interest data. *ISPRS International Journal of Geo-Information, 12*(11), 443. [DOI](https://doi.org/10.3390/ijgi12110443); [PolyU institutional record](https://research.polyu.edu.hk/en/publications/evaluation-of-the-resilience-of-the-catering-industry-in-hong-kon/).

This work studies Hong Kong catering resilience using restaurant POIs and spatial/statistical analysis. It is a close setting comparison, showing that restaurant location records can support a local investigation. Its outcome is industry resilience, not the reliability of linking individual branches across the three sources or agreement between their attributes. It does not establish that the selected datasets are complete or error-free.

## Source 6 - FEHD restaurant licences

**Verified source:** Food and Environmental Hygiene Department. (n.d.). *Restaurant licences*. [DATA.GOV.HK dataset](https://data.gov.hk/en-data/dataset/hk-fehd-fehdlmis-restaurant-licences), with an [official data dictionary](https://www.fehd.gov.hk/datagovhk/data_dictionary/english/restaurant_licences.pdf). The catalogue states daily updates at 9:00am.

FEHD provides an administrative sampling frame, not restaurant ratings or evidence that a venue is serving customers now. Licence types are not cuisine. The XML district coding separates Yau Tsim and Mong Kok; combining them as Yau Tsim Mong requires a documented crosswalk. Inspect the actual chosen representation before declaring its fields: XML and CSDI distributions need not have identical schemas. Retain the extract date and licence identifiers.

Supporting access terms: [DATA.GOV.HK terms and conditions](https://data.gov.hk/en/terms-and-conditions). Record proper attribution to FEHD, the Government and DATA.GOV.HK, and avoid suggesting official endorsement.

## Source 7 - OpenStreetMap and Overpass

**Verified source:** OpenStreetMap contributors. (n.d.). *OpenStreetMap data and Overpass API*. [Overpass documentation](https://wiki.openstreetmap.org/wiki/Overpass_API); [opening_hours tag documentation](https://wiki.openstreetmap.org/wiki/Key:opening_hours).

Overpass supports querying contributed records and tags. Missing address, phone or opening-hours tags indicate unavailable observations; they are not conflicting values. A query must cover relevant object types and document which restaurant categories it includes. The time of extraction is not the time a business last changed. The optional opening_hours convention makes a field possible in OSM but does not make it available in every record or comparable across all sources.

Supporting licence: [OSM copyright and licence](https://www.openstreetmap.org/copyright). Attribute OpenStreetMap contributors and identify ODbL. If sharing an adapted OSM database, retain the applicable licence obligations; do not simply apply a repository's code licence to all data.

## Source 8 - Overture Places

**Verified source:** Overture Maps Foundation. (n.d.). *Places guide and place schema*. [Places guide](https://docs.overturemaps.org/guides/places/); [schema reference](https://docs.overturemaps.org/schema/reference/places/place/), currently displaying v2.0.0; [licensing](https://docs.overturemaps.org/attribution/). These are living documents, so cite the access date rather than inventing a publication year.

The schema defines names, addresses, phones, categories, provenance and operating status. Confidence concerns whether a place exists. Operating status is distinct from daily hours, and the displayed place schema has no general opening_hours field. The official guide says the Places theme contains no OSM data; distinguish it from other Overture themes. Record the actual release/schema and per-source provenance and licences for the snapshot used.

The [official GERS tutorial](https://docs.overturemaps.org/gers/gers-tutorial/) already matches Alameda County restaurant inspections to Overture and discusses maintenance matching. Therefore, matching a government restaurant dataset to Overture is an existing approach.

## Source 9 - Overmatch existing system

**Verified source:** whubsch. (n.d.). *Overmatch* [Computer software]. [Maintainer's GitHub repository](https://github.com/whubsch/overmatch), README and MIT licence checked on the audit date.

Overmatch matches OSM amenities, including restaurants, to Overture and offers a visual interface for reviewing tag differences and enriching OSM. This is direct prior art for a comparison display and two-source matching workflow. Our potential contribution is an audited FEHD-anchored Hong Kong sample with missingness, matching checks and field-specific agreement measures; it is not the first matching tool or first coloured discrepancy interface. README feature claims were inspected; this audit did not independently test that software's accuracy or deployment.

## Synthesis and defensible contribution

POI matching and quality assessment are established topics (Sources 1-4). Restaurant POIs have been analysed in Hong Kong (Source 5), and restaurant matching and discrepancy interfaces already exist (Sources 8-9). Sources 6-8 support obtaining data while also showing that the sources describe different concepts and do not provide every field.

Two particularly useful comparisons for the report are Yeow et al.'s validation study (similar methods, different geography and sources) and Liu et al.'s catering study (same city and restaurant setting, different outcome). The official GERS restaurant tutorial and Overmatch should additionally be acknowledged when describing system design and claimed originality.

**Suggested bounded research-gap wording:** In the sources reviewed and searches logged here, we did not locate an evaluation of FEHD, OpenStreetMap and Overture together that reports branch-matching uncertainty, source coverage and field-specific agreement for a reproducibly selected sample of Hong Kong licensed restaurant branches. This project applies established methods to that defined local comparison. It does not introduce a new matching algorithm, establish which source is correct, or claim that the combination has never previously been studied.

No conclusion about a rare or absent exact study can be proved by a short web search. The originality claim should remain conditional, and it may need revision if additional close work is found. A report should explain the local question and empirical contribution without relying on being first.

## Search record

Search date: 23 October 2026, Asia/Shanghai. Tool: general web search with publisher/institution/maintainer pages opened for evidence. This was a targeted scoping check, not a systematic database review. No Google Scholar, Scopus, Web of Science, Chinese bibliographic database, or comprehensive unpublished-work search was completed.

| Search query as executed | Screening observation |
| --- | --- |
| `"Conflating point of interest (POI) data" Sun 2023` | Located publisher and author-hosted manuscript; confirmed Source 1. |
| `"POI point entity matching and fusion" Zhao 2022` | Located the ISPRS/Copernicus article; confirmed Source 2 and feature/weighting method. |
| `"Point-of-interest (POI) data validation methods" Yeow` | Located MDPI article; confirmed Source 3. |
| `"Quality assessment of OpenStreetMap" "Klinkhardt"` | Located publisher and KIT record; confirmed Source 4. |
| `FEHD OpenStreetMap Overture Hong Kong restaurants consistency matching` | Located adjacent matching products/tutorials and local applications; no exact three-source evaluation identified in the returned results screened. |
| `"FEHD" "Overture" restaurant` | No exact study identified in returned results screened. |
| `"Hong Kong" restaurant "cross-source" "OpenStreetMap"` | Adjacent restaurant/POI work; no exact triple-source study identified. |
| `"香港" "餐廳" "Overture"` | Broad/noisy results; no exact study identified. |
| `"FEHD" "OpenStreetMap" "Overture"` | No exact three-source evaluation identified in returned results screened. |
| `"Hong Kong" "Overture" "consistency" restaurant` | Broad/noisy results; no exact study identified. |
| `"FEHD" "OpenStreetMap" restaurant comparison` | Found local data products using FEHD/OSM; dataset reuse is not itself a field-agreement study. |
| `"Hong Kong" restaurant "data quality" "Overture"` | No exact study identified in returned results screened. |

Publication metadata for Source 5 was additionally checked on the PolyU institutional record linked above. Some MDPI page fetches returned HTTP 429; previously returned publisher content and institutional records were used rather than treating failed fetches as evidence against a paper's existence.

## Checks for the eventual report

- Keep a short note for each numbered source and include a connected overview; the table of URLs is only an audit aid.
- Separate finding a paper, understanding its method, and reproducing its method. Do not report a paper's result as this project's result.
- Match every empirical claim to a saved extract, a review decision, or an analysis table. Literature cannot validate the new dataset's matches.
- Preserve the distinction between missing data, schema-incompatible fields, uncertain entity links, and disagreements between comparable observed values.
- Do not describe machine-suggested matches as independent human validation. Leave student names and contribution histories for the actual people to complete.
