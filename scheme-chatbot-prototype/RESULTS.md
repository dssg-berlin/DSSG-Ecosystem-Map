# Results

## Verification summary

```text
Ran 14 tests in 0.118s
OK
```

All tests passed: data schema, collection report, rule comparators, `any_of`, eligibility states, farmer scenario, German-family scenario, document query, language fallback, question cap, Flask health and chat endpoints, unknown scheme handling, and graph exports.

## Generated artifacts

- `outputs/demo_results.json`: structured results for five scenarios.
- `outputs/demo_transcript.md`: human-readable conversation transcript.
- `outputs/knowledge_graph.json`: graph with nodes and edges.
- `outputs/knowledge_graph.ttl`: Turtle export of the same graph.

## Scenario outcomes

| Scenario | Final matches |
|---|---|
| India farmer, age 42 | `pm_kisan`, `nsap_widow`, `nsap_disability`, `mgnrega` |
| Germany family with children under 25 | `kindergeld`, `kinderzuschlag`, `grundsicherungsgeld`, `wohngeld` |
| Hindi widow with BPL card | `nsap_widow`, `pmmvy`, `mgnrega`, `pmjay` |
| Health emergency in India | `pmjay`, `pm_kisan`, `pmay_g`, `mgnrega` |
| PM-KISAN document query | `pm_kisan` |

The farmer scenario correctly asks about landholding first and ranks PM-KISAN first after the answer. The German-family scenario ranks Kindergeld first. The document query returns scheme documents and application steps.

## Graph summary

The graph connects schemes to countries, needs, profile fields, sources, and other schemes. It supports explanations such as:

- PM-KISAN covers income support, requires India residence and landholding, and cites PM-KISAN official sources.
- Kindergeld and Kinderzuschlag both cover family support; Kinderzuschlag combines with Wohngeld.
- Grundsicherungsgeld and Wohngeld have mutual exclusion considerations.

## What worked well

- TF-IDF intent recognition kept short follow-up answers on the same scheme.
- Three-valued eligibility avoided false negatives when information was missing.
- Exclusion handling prevented obviously ineligible users from receiving a scheme as a top match.
- Browser voice input and output worked through Web Speech API without Python STT/TTS packages.
- Official source links were attached to every matched scheme.

## Limitations observed

- Some result lists include `needs_info` schemes; the `?` marker indicates that more answers are needed.
- Translation strings are partial and a few contain mixed-language or typo artifacts.
- Direct source verification was blocked, so source freshness remains unconfirmed.
- The system does not submit forms or parse uploaded documents.
- The UI and tests were not run in a field setting with real villagers.

## Recommended next steps

1. Revalidate all source URLs and replace snapshots with cached official extracts.
2. Add a volunteer-reviewed question set per state or municipality.
3. Add OCR and document-checking for Aadhaar, ration card, BPL, SECC, and German family documents.
4. Run a moderated usability study in at least three languages.
5. Add a formal DPIA, consent flow, and production security controls.
6. Integrate official application APIs where available.
