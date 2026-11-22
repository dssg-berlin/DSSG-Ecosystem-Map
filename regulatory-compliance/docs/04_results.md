# Step 4 — Execution steps and outcomes

This document records what was done, in order, and what each step produced.
All artifacts are under `/kaggle/working/`.

## Step 1 — Environment survey

| Check | Outcome |
| --- | --- |
| Python | 3.13.18 |
| Key libraries available | `requests`, `beautifulsoup4`, `lxml`, `pypdf`, `pyyaml`, `networkx`, `fastapi`, `pydantic` |
| EUR-Lex reachable | HTTP 200 |
| MeitY reachable | HTTP 200 |
| Session constraint | Kept to minutes; well below the 11-hour Kaggle limit |

**Outcome:** no dependency installation was necessary; all work stayed in the
kernel workspace.

## Step 2 — Data collection

Command: `python -W ignore src/collect_sources.py`

| Instrument | Provisions parsed | Citation-verified | Raw bytes |
| --- | ---: | ---: | ---: |
| GDPR | 99 | 99 | 809,040 |
| EU AI Act | 113 | 113 | 1,264,462 |
| DPDP Act | 43 | 43 | 182,082 |
| **Total** | **255** | **255** | **2,255,584** |

Problems encountered and resolved:

- The first MeitY `writereaddata` URL returned 403 and India Code timed out.
  The official MeitY static-hosted Gazette PDF was located and used instead.
- EUR-Lex emitted an XML parser warning; parsing still succeeded and warnings
  were suppressed in the pipeline invocation.
- The DPDP PDF contained bilingual Gazette watermark lines; a filter list
  removed them before section slicing.

Produced: `data/raw/`, `data/processed/manifest.json`, provision JSON files and
normalized source corpora. Details in [01_data_collection.md](01_data_collection.md).

## Step 3 — Ontology and knowledge graph

Command: `python src/build_knowledge_graph.py`

The ontology defines 18 themes and 25 controls. The builder validates every
citation against the 255 parsed provisions and every excerpt against its
normalized source text **before** constructing the graph.

| Metric | Value |
| --- | ---: |
| Provision nodes | 255 |
| Instrument nodes | 3 |
| Theme nodes | 18 |
| Control nodes | 25 |
| Total nodes | 301 |
| Total edges | 482 |
| Citation verification | 255 / 255 |
| Validation errors | 0 |
| Themes spanning all three regimes | 10 |

Pairwise theme overlap: GDPR × DPDP 18, GDPR × AI Act 10, AI Act × DPDP 10.

Produced: `data/knowledge_graph/graph.json`, `graph.graphml`,
`control_index.json`, `graph_summary.json`, and `docs/crosswalk.md`.

One YAML issue was fixed during this step: regex-like tokens such as
`auto_?decid` in flow sequences had to be quoted for PyYAML. A design issue was
also fixed: advisory "verify explanation / disclosure" patterns were removed
from C09, C11, C13, C16 and C17 so that compliant code mentioning those concepts
does not produce false positives; those controls now rely on safeguard-presence
checks and trace semantics.

## Step 4 — Audit targets

Four targets were authored to exercise both modes:

| Target | Purpose |
| --- | --- |
| `examples/vulnerable_app` | Deliberate violations across PII logging, prompts, consent, purpose, retention, automated decisions, synthetic content, children, transfers, processors, grievance and audit logging |
| `examples/compliant_app` | Same use cases with tokenisation, purpose-bound consent, retention, explanation, human review, AI disclosure, DPA/SCC/DPIA references |
| `examples/agent_traces/risky_agent.jsonl` | Live agent emitting raw PII, undeclared purpose, unexplained adverse decision and undisclosed generated content |
| `examples/agent_traces/clean_agent.jsonl` | Masked trace with declared purposes, explained decision and disclosed output |

## Step 5 — Audits

Command: `python -W ignore src/run_pipeline.py --skip-fetch`

| Target | Mode | Findings | Critical | High | Medium | Gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `vulnerable_app` | codebase | 21 | 5 | 11 | 5 | `BLOCK_DEPLOYMENT` |
| `compliant_app` | codebase | 0 | 0 | 0 | 0 | `PASS` |
| `risky_agent` | trace | 7 | 3 | 4 | 0 | `BLOCK_DEPLOYMENT` |
| `clean_agent` | trace | 0 | 0 | 0 | 0 | `PASS` |

### Regime coverage of the vulnerable codebase

| Regime | Finding-level citations |
| --- | ---: |
| India DPDP Act | 21 |
| EU GDPR | 19 |
| EU AI Act | 10 |

This is the key outcome of the dual-jurisdiction design: a single scan surfaced
obligations under all three instruments for the same code paths.

### Controls triggered — `vulnerable_app`

| Control | Severity | Issue |
| --- | --- | --- |
| C01 | critical | Raw PII written to application logs |
| C02 | critical | Personal data in LLM prompts or agent memory |
| C13 | critical | Child data without verifiable guardian consent |
| C14 | critical | Tracking or targeted advertising directed at children |
| C04 | high | No consent gate |
| C06 | high | Purpose drift / broad purpose |
| C07 | high | No retention limit |
| C08 | high | No erasure path |
| C09 | high | Automated decision without explanation |
| C10 | high | No human review |
| C11 | high | Synthetic content without disclosure |
| C15 | high | No breach notification hook |
| C16 | high | Cross-border transfer without evidence |
| C17 | high | Processor without contract reference |
| C18 | high | No impact assessment |
| C12 | medium | No AI interaction notice |
| C19 | medium | No decision input validation |
| C21 | medium | No grievance mechanism |
| C22 | medium | No access/correction endpoint |
| C24 | medium | No audit logging |

### Controls triggered — `risky_agent`

C01, C02 (raw identifiers in trace), C09, C10 (unexplained adverse decision),
C11 (undisclosed generated content) and C25 (tool call with `purpose=marketing`
outside the declared `customer_support` purpose).

## Step 6 — False-positive check

The first run of `clean_agent` produced one C11 finding because the semantic
check treated every `llm_output` event as synthetic content. AI Act Article 50's
synthetic-content disclosure applies to generated media/content, not ordinary
chatbot replies; the check was narrowed to `generated_content` and `synthetic`
event types. Re-running produced 0 findings. This is recorded as an explicit
outcome because it changed both code and reported results.

## Step 7 — Artifacts verified

| Artifact | Result |
| --- | --- |
| `results/audits/*.json` | 4 reports, schema `lexaudit.report/v0.1` |
| `results/audits/*.md` | 4 readable reports with evidence and verbatim citations |
| `results/pipeline_summary.json` | Aggregate of graph and audit outcomes |
| `data/knowledge_graph/graph.graphml` | Loadable by NetworkX |
| `src/verify_outputs.py` | 21/21 artifact and outcome checks passed after a full clean re-run |

## Overall outcome

The prototype successfully demonstrates the idea: official legal text can be
converted into a citation-verified, cross-jurisdiction graph, and that graph can
drive a deterministic pre-deployment gate that blocks a non-compliant codebase
and agent trace while passing their remediated counterparts.

## Next steps beyond the prototype

- Add static taint/data-flow analysis to replace regex heuristics.
- Ingest DPDP Rules, AI Act harmonised standards and national GDPR implementations.
- Add LLM-assisted semantic mapping with mandatory citation verification against
  the same snapshot hashes.
- Stream OpenTelemetry spans from live agents instead of JSONL files.
- Add jurisdiction/profile configuration per venture and per deployment region.
- Provide remediation patches and a GitHub Action for CI gating.
