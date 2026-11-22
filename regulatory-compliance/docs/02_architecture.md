# Step 2 — Proposed prototype architecture

## 2.1 Components

| Component | File | Responsibility |
| --- | --- | --- |
| Collector | `src/collect_sources.py` | Fetch official sources, parse provisions, record provenance, verify excerpts |
| Ontology | `config/ontology.yaml` | Curated themes, cross-law mappings and executable controls |
| Graph builder | `src/build_knowledge_graph.py` | Validate citations, construct graph, export artifacts and crosswalk |
| Audit engine | `src/audit_engine.py` | Code and trace detectors, finding enrichment, report rendering, gate decision |
| Orchestrator | `src/run_pipeline.py` | Run all stages and emit `results/pipeline_summary.json` |

## 2.2 Data flow

```
Source bytes --> provisions --> validated graph --> control index
                                      |                  |
                                      |                  v
                          crosswalk.md      code scanner / trace scanner
                                                         |
                                            findings + citations
                                                         |
                                             JSON report + MD report
```

## 2.3 Graph schema

Directed graph with four node types:

| Node type | Id format | Example attributes |
| --- | --- | --- |
| `instrument` | `instrument:<name>` | provision count |
| `provision` | `provision:<PROVISION_ID>` | citation, title, instrument, `citation_verified`, source SHA-256 |
| `theme` | `theme:<Txx>` | label, slug, description |
| `control` | `control:<Cxx>` | title, severity, rationale |

Edge relations:

| Relation | From → To | Meaning |
| --- | --- | --- |
| `CONTAINS` | instrument → provision | The instrument contains the provision |
| `MAPS_TO` | theme → provision | The theme is grounded in statutory text |
| `EQUIVALENT` / `OVERLAPPING` / `COMPLEMENTARY` / `STRICTER` | provision → provision | Cross-law relation asserted by the ontology |
| `ENFORCED_BY` | theme → control | A machine-checkable control operationalises the theme |
| `CITES` | control → provision | The control's finding must cite this text |

Current graph: **301 nodes, 482 edges**, exported as `graph.json` and
`graph.graphml` for programmatic or visual inspection.

## 2.4 Theme layer

The 18 themes are the unit of cross-jurisdiction comparison. Ten of them are
grounded in all three regimes. The highest density of overlap is between GDPR
and the DPDP Act (18 shared themes), reflecting their shared data-protection
core; the AI Act overlaps on transparency, children, oversight, risk and
prohibited practices.

Representative mappings:

| Theme | GDPR | EU AI Act | DPDP Act |
| --- | --- | --- | --- |
| Consent | Art. 4, 6, 7, 8, 21 | — | s. 4, 5, 6, 7 |
| PII masking | Art. 4, 5, 25, 32 | Art. 10 | s. 8 |
| Automated decisions | Art. 15, 22 | Art. 6, 26, 86 | s. 8 |
| Synthetic content | Art. 5, 13 | Art. 13, 50 | s. 5 |
| Children | Art. 8 | Art. 5 | s. 9 |
| Retention | Art. 5, 17 | — | s. 8, 12 |
| Impact assessment | Art. 35 | Art. 9, 12, 26, 27 | s. 10 |

The full generated matrix is in `docs/crosswalk.md`.

## 2.5 Control layer

Each control has an id, theme, severity, rationale, citations, remediation and
one or more detectors of three kinds:

1. **`code_patterns`** — a regex plus file globs; a match is a positive detection
   of an explicitly risky construct (e.g. raw identifier in a log call).
2. **`absence_check`** — fires when a repository contains trigger tokens for a
   regulated activity (e.g. child data) but none of the required safeguard
   tokens (e.g. `verifiable_consent`) anywhere in the scanned files.
3. **`trace_patterns`** — regex over selected fields of each JSONL agent event,
   supplemented by semantic checks in `_trace_semantics` for decisions,
   disclosures and purpose-bound tool calls.

Controls deliberately separate "unambiguously bad construct" from "required
safeguard missing". The latter avoids flagging compliant code merely for
mentioning a regulated concept.

## 2.6 Finding enrichment

Every raw detector hit is enriched with:

- severity and theme from the control,
- the set of implicated regimes derived from its citations,
- verified statutory excerpts with source URL and SHA-256,
- exact file/line or trace event location,
- a remediation instruction.

Deduplication uses `(control, file, evidence prefix)` so repeated matches in one
line do not inflate counts.

## 2.7 Deployment gate

```
critical or high finding  ->  BLOCK_DEPLOYMENT
only medium findings      ->  MANUAL_REVIEW
no findings               ->  PASS
```

This is intentionally conservative to match the prevention goal: a deployment
that might log unmasked PII should not pass silently.
