# Village Benefit Assistant

A prototype AI chatbot that helps villagers in India, and residents in Germany, discover government benefit schemes, understand eligibility, collect documents, and see official application steps.

## Quickstart

```bash
cd /kaggle/working/scheme-chatbot-prototype
python collect_data.py
python run_demo.py
python -m unittest -v
python app.py
```

Open the Flask app at `http://localhost:7860` or forward port `7860` in Kaggle. Set `PORT` to use another port.

## What is included

- `data/sources.json`: 25 collected source snapshots with URLs, publishers, tiers, facts, and excerpts.
- `data/schemes.json`: 13 scheme records, 24 profile fields, eligibility rules, documents, steps, offices, helplines, deadlines, multilingual text, and graph relations.
- `collect_data.py`: validates source records and optionally verifies URLs with `--live`.
- `engine.py`: retrieval, 3-valued eligibility, conversation state, knowledge graph, and multilingual responses.
- `app.py`: Flask API and static file server.
- `static/index.html`: chat UI with text input, browser speech recognition, and speech synthesis.
- `run_demo.py`: runs five scenarios and writes results and transcripts.
- `test_prototype.py`: 14 unit and integration tests.
- `outputs/`: generated knowledge graph, Turtle export, demo results, and demo transcript.
- `DOCUMENTATION.md`, `PROPOSAL.md`, `DATA_SOURCES.md`, `RESULTS.md`: build notes and outcomes.

## Example interactions

- "I am a small farmer in India, aged 42" then "yes" then "show me eligible schemes".
- "We live in Germany and have two children under 25" then "show me schemes".
- "What documents are needed for PM-KISAN?".
- "मैं 45 साल की विधवा हूँ और मेरे पास बीपीएल कार्ड है".

## Design choices

- Offline-first: no external model downloads or API keys required.
- Retrieval: scikit-learn TF-IDF over character n-grams in English, Hindi, Urdu, and German text.
- Eligibility: `eligible`, `ineligible`, `needs_info`; the bot asks one missing question at a time.
- Voice: browser Web Speech API because Python STT/TTS packages are unavailable in the kernel.
- Graph: NetworkX for scheme-need-field-document-source relations; Turtle is exported manually because `rdflib` is not installed.
- Privacy: profile state stays in the browser and is sent per request; no user data is stored.

## Verification

```text
Ran 14 tests in 0.118s
OK
```

See `RESULTS.md` for scenario outputs and limitations.
