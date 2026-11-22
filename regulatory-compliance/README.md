# LexAudit — open-source AI-native dual-jurisdiction compliance auditor

Prototype of an AI-native infrastructure that audits codebases **and** live agent
traces against European and Indian data/AI law **at the same time**. It answers a
single operational question before deployment:

> Would this system accidentally log unmasked PII, drift from its declared
> purpose, or violate transparency/automated-decision duties under GDPR, the
> EU AI Act **and** the India DPDP Act?

## Rationale

German and Indian ventures increasingly ship the same AI product into both
markets. The two regimes overlap but are not identical:

- GDPR emphasises lawful basis, purpose limitation, minimisation, security and
  rights, with extra safeguards for solely automated decisions.
- The EU AI Act adds transparency for AI interaction and synthetic content,
  human oversight, logging and impact assessment for high-risk systems.
- The DPDP Act makes notice + consent central, requires verifiable guardian
  consent for children, prohibits child tracking, and sets explicit retention
  expiry and breach intimation duties.

A checklist per regime misses the intersections. The prototype encodes the
three texts into one citation-verified graph and evaluates one shared control
set with citations to every applicable regime.

## Proposed prototype

| Capability | Prototype implementation |
| --- | --- |
| Legal ingestion | Official EUR-Lex HTML for GDPR and AI Act, official MeitY Gazette PDF for DPDP |
| Unified knowledge graph | 18 themes, 3 instrument nodes, 255 provision nodes, 25 controls, 482 edges (NetworkX, exported JSON + GraphML) |
| Citation verification | Every stored excerpt is re-checked against the normalized official source text at graph build time |
| Codebase audit | Regex detectors plus repository-level safeguard presence checks over source and config files |
| Live agent audit | JSONL trace ingestion with semantic checks for PII in logs, decisions, disclosures and purpose-bound tool calls |
| Deployment gate | `BLOCK_DEPLOYMENT` if any critical/high finding, `MANUAL_REVIEW` if only medium, `PASS` otherwise |
| Outputs | Machine-readable JSON and human-readable Markdown reports with exact citations and excerpts |

## Architecture

```
official sources (EUR-Lex HTML, MeitY PDF)
        |
        v
src/collect_sources.py  -->  data/raw/            (immutable snapshots + SHA-256)
        |                    data/processed/      (255 parsed provisions, normalized corpora)
        v
config/ontology.yaml    -->  src/build_knowledge_graph.py
(themes, mappings,           |
 citations, controls)        v
                         data/knowledge_graph/    graph.json, graph.graphml,
                                                  control_index.json, summary
                                     |
                    +----------------+-----------------+
                    v                                  v
        src/audit_engine.py                  src/audit_engine.py
        (codebase scan)                      (agent trace scan)
                    |                                  |
                    +----------------+-----------------+
                                     v
                          results/audits/*.json + *.md
                          results/pipeline_summary.json
```

## Repository layout

```
src/
  collect_sources.py        download, parse and verify legal sources
  build_knowledge_graph.py  validate ontology and build the graph
  audit_engine.py           detectors, trace semantics, reports, gate logic
  run_pipeline.py           end-to-end orchestration
  verify_outputs.py         checks all generated artifacts
config/ontology.yaml        themes, cross-law mappings and 25 controls
data/raw/                   downloaded official documents
data/processed/             parsed provisions and normalized source text
data/knowledge_graph/       graph exports and control index
examples/                   vulnerable/compliant apps, risky/clean agent traces
results/audits/             generated audit reports
docs/                       data, architecture, methodology, results, crosswalk
```

## Quick start

```bash
pip install -r requirements.txt
python -W ignore src/run_pipeline.py          # fetch, parse, build, audit
python -W ignore src/run_pipeline.py --skip-fetch   # reuse cached sources
python src/verify_outputs.py                        # validate all artifacts
```

Run a single target:

```bash
python src/audit_engine.py code  examples/vulnerable_app
python src/audit_engine.py trace examples/agent_traces/risky_agent.jsonl
```

## Prototype results

| Target | Mode | Findings | Gate |
| --- | --- | ---: | --- |
| `vulnerable_app` | codebase | 21 (5 critical, 11 high, 5 medium) | `BLOCK_DEPLOYMENT` |
| `compliant_app` | codebase | 0 | `PASS` |
| `risky_agent` | live trace | 7 (3 critical, 4 high) | `BLOCK_DEPLOYMENT` |
| `clean_agent` | live trace | 0 | `PASS` |

The vulnerable codebase produced findings under all three regimes
(GDPR 19, DPDP Act 21, EU AI Act 10 finding-level citations), including raw PII
logging, consent absence, no retention limit, missing explanation and human
review for automated decisions, missing synthetic-content disclosure, child
targeting and absent breach notification.

## Documentation index

- [docs/01_data_collection.md](docs/01_data_collection.md) — sources, parsing and citation verification
- [docs/02_architecture.md](docs/02_architecture.md) — components and graph schema
- [docs/03_methodology.md](docs/03_methodology.md) — detectors, severity and gate logic
- [docs/04_results.md](docs/04_results.md) — step-by-step execution record and outcomes
- [docs/05_controls_reference.md](docs/05_controls_reference.md) — all 25 controls and their citations
- [docs/crosswalk.md](docs/crosswalk.md) — generated legal crosswalk

## Design principles

1. **Citation first.** A finding is only actionable if it can point to verified
   statutory text. Every control carries citations to one or more instruments.
2. **One control, many regimes.** A single detection maps to overlapping duties,
   so a German+Indian venture sees the combined exposure rather than two reports.
3. **Fail closed.** Missing safeguards in a system that handles personal data are
   findings, not silent passes.
4. **Deterministic core.** The prototype uses transparent rules rather than an
   LLM for detection, so results are reproducible and auditable. The graph is the
   place where semantic/LLM enrichment would plug in next.

## Limitations

This is a research prototype, **not legal advice** and not a certification.

- Regex detectors are heuristics: they produce false positives and can miss
  semantically equivalent violations. They need data-flow and taint analysis for
  production use.
- Absence checks infer from token presence across a repository; they cannot prove
  that a control is actually enforced at runtime.
- Only the English versions of the three instruments are ingested; authoritative
  language and later amendments must be added.
- DPDP rules and AI Act implementation timelines are not modelled.
- Trace ingestion uses JSONL files; a production build would consume
  OpenTelemetry spans from a running agent runtime.
- The ontology is curated, not learned; its mappings are a starting point for
  review by counsel in both jurisdictions.

## Licensing

The prototype code and ontology are intended as open source. Legal texts are
reproduced as short, attribution-bearing excerpts for verification and remain
subject to their respective public sources and applicable terms.
