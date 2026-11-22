# Prototype Proposal

## Problem

Village residents often know that a benefit may exist but cannot tell whether they qualify, which documents are needed, where to apply, or which source can be trusted. Information is scattered across schemes, departments, languages, and portals. Intermediaries can add cost, delay, or misinformation.

## Proposed solution

A conversational assistant that asks a short, structured set of questions, matches answers against a curated scheme knowledge base, and returns:

- likely relevant schemes with plain-language reasons;
- documents usually required;
- application steps and office or helpline;
- official source links for verification;
- optional voice input and output for low-literacy users.

## Users and scenarios

- Indian small farmer with land before 1 February 2019: PM-KISAN, MGNREGA, PM-JAY.
- Indian widow or BPL household: NSAP widow pension, PMMVY, PM-JAY.
- Family with hospitalisation need: PM-JAY.
- Family in Germany with children: Kindergeld, Kinderzuschlag, Wohngeld, Grundsicherungsgeld.
- User asking for documents for a named scheme.

## Architecture

1. Data layer: `sources.json` and `schemes.json` with provenance and multilingual text.
2. Retrieval layer: TF-IDF character n-gram ranking over scheme names, aliases, summaries, needs, and keywords.
3. Reasoning layer: rule evaluator with three-valued logic and explicit exclusion semantics.
4. Dialogue layer: profile extraction, one-question-at-a-time clarification, intent memory, question cap, and result formatting.
5. Knowledge graph: NetworkX graph of schemes, needs, profile fields, sources, and cross-scheme relations.
6. Interface layer: Flask API plus browser UI with Web Speech API voice support.
7. Outputs: JSON/Turtle graph exports, demo transcript, demo results, and Markdown documentation.

## Why this approach

- Works in a Kaggle kernel with no external API key or heavyweight model download.
- Keeps a human-readable rule trail for every match.
- Cites official sources rather than generating unsupported claims.
- Supports Hindi, Urdu, English, and German with English fallback.
- Can later swap the rule engine or add an LLM without changing the UI contract.

## Human-centred and safety requirements

- Do not present the chatbot as the deciding authority.
- Always show official source links and an indicative-guidance disclaimer.
- Ask only for fields needed to narrow eligibility.
- Allow users to skip questions by asking for results.
- Keep profile data in the browser; do not persist personally identifiable information.
- Provide text alternatives for voice interaction.

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Source collection and curated scheme KB | Complete in prototype |
| 2 | Rule engine, retrieval, graph, Flask UI | Complete in prototype |
| 3 | Tests, demo scenarios, documentation | Complete in prototype |
| 4 | Official API integrations and live source verification | Proposed |
| 5 | OCR/document upload and assisted form filling | Proposed |
| 6 | Field usability study with villagers and local volunteers | Proposed |
| 7 | Security review, DPIA, and production deployment | Proposed |

## Success criteria for a field pilot

- At least 80% of tested users can reach a relevant scheme in five minutes.
- At least 90% of returned source links are live and point to an official page.
- No personally identifiable information is stored by the prototype.
- Users can complete the flow in their preferred language with or without voice.
- Local volunteers can audit why a scheme was suggested or not suggested.
