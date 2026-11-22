# Step 3 — Audit methodology

## 3.1 Targets

The prototype supports two audit modes:

- **`code`** — recursive scan of a source tree. Skips `.git`, `node_modules`,
  `data`, `results`, caches and files over 2 MB. Files are matched by per-detector globs.
- **`trace`** — line-delimited JSON events from a live or recorded agent. Each
  line may contain `event`, `message`, `args`, `result`, `content`, `metadata`,
  `purpose` and arbitrary fields; `raw` is used for whole-event matching.

## 3.2 Detection logic

For each control, in order:

1. Compile every `code_patterns.regex` and scan matching files line by line,
   capped at three matches per file per detector.
2. For `absence_check`, collect all matching files, find files containing any
   trigger token, then check whether any file contains any required safeguard
   token. If triggers exist and no safeguard exists, emit one repository-scoped
   finding.
3. For `trace_patterns`, select the listed fields from each event (falling back
   to `raw`), serialize non-strings as JSON, and regex-match.
4. Run semantic trace checks:
   - PII-shaped values in `log` / `tool_call` / `tool_result` events → C01
   - adverse `decision` without `explanation` / `reason_codes` → C09
   - adverse decision without `human_review` → C10
   - `generated_content` / `synthetic` without disclosure flag → C11
   - tool event whose `purpose` is not in the session's `declared_purposes` → C25

## 3.3 Why these detectors

The detectors are chosen to directly encode the project rationale:

| Risk in rationale | Controls |
| --- | --- |
| Accidental logging of unmasked PII | C01, C02, C03 |
| Purpose limitation violations | C06, C25 |
| Consent invalid or absent | C04, C05 |
| Synthetic content transparency | C11, C12 |
| Automated decision safeguards | C09, C10, C18, C19 |
| Cross-regime overlap exposure | citations on every control |

## 3.4 Severity assignment

| Severity | Assignment rule |
| --- | --- |
| `critical` | Direct exposure of identifiers or prohibited processing of children |
| `high` | Missing legal basis, missing transparency, missing core safeguards or signals of cross-border/processor non-compliance |
| `medium` | Missing support processes such as grievance redressal, access endpoints, audit logging or data-quality checks |

## 3.5 Validation approach

The demo targets form a paired evaluation:

- `vulnerable_app` intentionally contains known violations for 20 controls.
- `compliant_app` implements the same use cases with masking, consent checks,
  retention, explanations, human review, disclosure and documented safeguards.
- `risky_agent` / `clean_agent` provide the same contrast for live traces.

A successful prototype should block the non-compliant targets, pass the
remediated ones, and cite all three regimes where relevant. Results are in
`docs/04_results.md`.

## 3.6 Reporting

Every audit writes two artifacts to `results/audits/`:

- `<name>.json` — full report conforming to `lexaudit.report/v0.1`, including
  gate decision, severity/jurisdiction counts, and enriched findings.
- `<name>.md` — human-readable report with evidence blocks, verbatim statutory
  excerpts and remediation steps.

`results/pipeline_summary.json` aggregates the four audits and the graph summary.
