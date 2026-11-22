# Data Sources

## Collection method

Data was collected through web-search snapshots because direct HTTP access from the Kaggle kernel was blocked or returned errors for several official domains. Each record in `data/sources.json` includes a URL, publisher, source type, trust tier, factual notes, and a recorded excerpt.

`collect_data.py` validates the bundle and writes `data/collection_report.json`. It does not alter the source snapshots.

## Trust tiers

| Tier | Meaning | Count | Use |
|---|---|---:|---|
| A | Official government, department, scheme portal, law, or guideline | 20 | Scheme facts, eligibility, benefits, application steps |
| B | Secondary legal guide or project documentation | 4 | Context, implementation inspiration, non-authoritative guidance |
| C | Comparable product documentation | 1 | Interaction design inspiration only |

## Indian sources

- `myscheme_portal`: umbrella discovery portal for central and state schemes.
- `india_gov_schemes`: Government of India scheme listing.
- `pmkisan_home` and `pmkisan_guidelines`: PM-KISAN official portal and guidelines; ₹6,000/year, landholding condition, DBT.
- `pmjay_home` and `pmjay_hospital`: Ayushman Bharat PM-JAY portal and hospital list; ₹5 lakh/family/year, SECC/Ayushman identification.
- `pmayg_guidelines` and `pmayg_pib`: PMAY-G guidelines and press information; ₹1.20 lakh plain areas, ₹1.30 lakh hilly areas.
- `mgnrega_home` and `mgnrega_act`: MGNREGA official portal and Act; 100 days of wage employment.
- `pmuy_faq` and `pmuy_apply`: PMUY FAQ and application route; LPG connection support.
- `pmmvy_wcd` and `pmmvy_faq`: PMMVY Ministry of Women and Child Development materials; ₹5,000 first child, ₹6,000 second girl child.
- `nsap_official` and `nsap_faq`: NSAP official and FAQ; old-age, widow, and disability pensions.

## German sources

- `ba_kindergeld`: Bundesagentur für Arbeit Kindergeld page; €259/month from 2026.
- `ba_kiz`: Kinderzuschlag page; up to €297/month.
- `ba_grundsicherung`: Grundsicherungsgeld page; replaces Bürgergeld from 01.07.2026.
- `ba_family`: family benefits overview.
- `wohngeld_guide`: secondary legal guide for Wohngeld; marked tier B.

## Comparable projects

- `foerderfunke_prototypefund`, `foerderfunke_civicdata`, `foerderfunke_github`: FörderFunke civic-tech project documentation and repository; used for design inspiration.
- `grantgpt`: comparable grant discovery product; tier C, not used for scheme facts.

## Known collection blockers

- `https://www.india.gov.in/my-government/schemes-0` timed out after 12 seconds.
- `https://pmkisan.gov.in/` returned a connect timeout.
- `https://www.prototypefund.de/en/projects/foerderfunke` returned HTTP 403.

Because of these blockers, the prototype cites source URLs and recorded excerpts but does not claim that every link was live at generation time. A production version should revalidate all URLs before release.
