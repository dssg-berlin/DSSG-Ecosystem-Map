# Step 1 — Collecting the legal data

## Objective

Obtain authoritative, versioned source text for the three instruments and turn
it into addressable provisions that can be cited by a machine.

## Sources selected

| Instrument | Official source | Format | Why this source |
| --- | --- | --- | --- |
| GDPR — Regulation (EU) 2016/679 | EUR-Lex CELEX `32016R0679` | HTML | Consolidated official English text with stable article anchors |
| EU AI Act — Regulation (EU) 2024/1689 | EUR-Lex CELEX `32024R1689` | HTML | Official English text with 113 article anchors |
| India DPDP Act, 2023 | MeitY Gazette PDF (No. 22 of 2023, 11 Aug 2023) | PDF | Official Gazette copy hosted by the nodal ministry |

An early candidate URL on `meity.gov.in/writereaddata/...` returned HTTP 403 and
`indiacode.nic.in` timed out, so the collection script uses the working official
MeitY static-hosted Gazette PDF. The exact URL, hash and retrieval time are
recorded in `data/processed/manifest.json`.

## Collection method

1. `src/collect_sources.py` downloads each source with an identified user agent
   and writes the untouched bytes to `data/raw/`.
2. A SHA-256 digest, byte count, content type and UTC retrieval timestamp are
   recorded for provenance.
3. EUR-Lex HTML is parsed with BeautifulSoup. Nodes matching
   `div.eli-subdivision[id^="art_"]` with an exact numeric article id become
   provisions. Titles come from `p.oj-sti-art`.
4. The DPDP PDF is extracted with `pypdf`. Gazette watermark lines (Hindi/English
   masthead fragments) are filtered, then numbered sections 1–43 are sliced by
   the `^N.` markers and paired with their official section titles.
5. Text is normalised with Unicode NFKC, non-breaking spaces collapsed and
   whitespace flattened. The normalised full corpus is persisted next to the
   provisions.
6. Each provision stores a 280-character `excerpt` taken verbatim from the
   normalised text.

## Citation verification

At graph build time, `src/build_knowledge_graph.py` re-opens the normalised
corpus for each instrument and asserts that the stored excerpt is a literal
substring. This is the prototype's "citation-verified" guarantee: a citation
cannot be introduced into the graph unless its text is traceable to the exact
downloaded snapshot identified by SHA-256.

Result: **255 / 255 provisions verified**, zero validation errors.

## Collected data inventory

| Instrument | Provisions | Raw size | SHA-256 (short) |
| --- | ---: | ---: | --- |
| GDPR | 99 Articles | 809,040 B | `d78d4c48...` |
| EU AI Act | 113 Articles | 1,264,462 B | `9dd2aa99...` |
| DPDP Act | 43 Sections | 182,082 B | `4deb2398...` |

## Outputs

- `data/raw/` — immutable source snapshots
- `data/processed/manifest.json` — provenance manifest
- `data/processed/{gdpr,ai_act,dpdp}_provisions.json` — parsed provisions per instrument
- `data/processed/all_provisions.json` — combined 255 provisions
- `data/processed/*_source_normalized.txt` — normalized verification corpora
