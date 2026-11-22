# Documentation

## Environment

All work was performed under `/kaggle/working`. The kernel provided Python 3.13.18, Flask 3.1.3, scikit-learn 1.6.1, NetworkX 3.7, requests 2.34.2, BeautifulSoup 4.13.5, Gradio 6.30.0, and pytest 8.4.2. `rdflib`, Streamlit, Whisper, `pyttsx3`, `gtts`, and `speech_recognition` were unavailable, and no Hugging Face cache was present.

Direct HTTP requests from the kernel timed out for India government sites and returned 403 for Prototype Fund pages. Data collection therefore used web-search snapshots with recorded URLs and excerpts. `collect_data.py` can still attempt live verification with `--live`.

## Step 1: Collect data

Source research covered official scheme portals, legal documents, government guidelines, German benefit authority pages, comparable projects, and direct application links.

```bash
cd /kaggle/working/scheme-chatbot-prototype
python collect_data.py
```

Output: `data/collection_report.json`.

The report recorded 25 sources: 20 tier A, 4 tier B, and 1 tier C. Tier A means official government or scheme authority. Tier B means secondary legal guide or project documentation. Tier C means comparable product documentation used for inspiration, not scheme facts.

## Step 2: Curate the knowledge base

`data/schemes.json` contains:

- 13 schemes across India and Germany;
- 24 profile fields with type, question, and options;
- rules with `eq`, `in`, `gte`, `lte`, and `any_of`;
- exclusion rules with safe-state semantics;
- documents, application steps, offices, helplines, deadlines, benefits, aliases, and keywords;
- multilingual `name`, `summary`, `benefit`, `document`, and `step` values for `en`, `hi`, `ur`, and `de`;
- relations such as `COMBINES_WITH`, `CONVERGES_WITH`, `ENABLES`, and `ENABLED_BY`.

## Step 3: Implement the engine

`engine.py` provides:

- `KnowledgeBase`: loads JSON, builds TF-IDF corpus, evaluates source integrity, and builds a NetworkX graph.
- `RuleEvaluator`: returns `eligible`, `ineligible`, or `needs_info` with matched, failed, missing, and exclusion fields.
- `ProfileExtractor`: parses numbers, choices, yes/no answers, and language-specific hints.
- `ChatEngine`: handles intent detection, detail queries, clarification, question cap, result ranking, citations, and graph neighbours.
- `export_artifacts`: writes `outputs/knowledge_graph.json` and `outputs/knowledge_graph.ttl`.

Important logic decisions:

- Exclusion rules are stored as safe states, for example `income_tax_payer == false`; a false safe state triggers ineligibility.
- Requirement questions are preferred over exclusion questions unless a scheme already has a positive requirement match.
- Intent scores are remembered across short answers such as "yes", so the conversation stays on the same scheme.
- Generic result prompts do not overwrite stored intent unless they contain a meaningful scheme signal.
- Eight clarification questions force a result to avoid exhausting the user.

## Step 4: Implement the API and UI

`app.py` exposes:

- `GET /` for the browser UI;
- `GET /api/health` for counts and status;
- `GET /api/schemes` for the scheme catalogue;
- `GET /api/schemes/<id>` for detail and graph neighbours;
- `POST /api/chat` for conversation turns;
- `POST /api/export` to regenerate graph exports.

`static/index.html` sends `{message, language, profile, expecting, asked}` to `/api/chat`. It renders chat messages, profile chips, matched scheme chips, source links, and optional spoken replies. Voice input uses `SpeechRecognition` or `webkitSpeechRecognition` with `en-IN`, `hi-IN`, `ur-IN`, and `de-DE` locales.

## Step 5: Run the demo

```bash
python run_demo.py
```

This writes:

- `outputs/demo_results.json`: structured scenario results;
- `outputs/demo_transcript.md`: readable transcript;
- `outputs/knowledge_graph.json`: graph nodes and edges;
- `outputs/knowledge_graph.ttl`: Turtle export.

## Step 6: Verify

```bash
python -m unittest -v
```

The suite covers data schema, collection report, rule comparators, `any_of`, eligibility states, farmer and German-family scenarios, document queries, language fallback, question cap, Flask endpoints, unknown scheme handling, and graph exports.

Result: 14 tests passed.

## Known limitations

- Rule extraction is heuristic and can misread ambiguous answers.
- Live government data and form URLs were not verifiable from the kernel during collection.
- Translations are partial; English fallback is used when a translation is missing.
- The graph uses hand-written Turtle rather than an RDF library.
- The prototype has no authentication, database, document upload, OCR, or form submission.
- It does not provide legal advice; the official body decides eligibility.

## Privacy and security notes

- Profile state is held in browser memory and passed per request; no server-side user store exists.
- No secrets, API keys, or credentials are used.
- Source links are rendered with `rel="noreferrer"`.
- HTML is escaped before chat rendering.
- Future deployment should add HTTPS, rate limiting, logging redaction, consent flows, and a formal DPIA.
