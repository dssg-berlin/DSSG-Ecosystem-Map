# Control reference

Generated from `config/ontology.yaml` and the resolved control index.

| ID | Theme | Severity | Title | Citations | Detectors |
| --- | --- | --- | --- | --- | --- |
| C01 | T05 pii_masking_pseudonymisation | critical | Raw PII written to application logs | Article 5, Article 32, section 8 | 2 code regex, 1 trace regex, trace semantics |
| C02 | T05 pii_masking_pseudonymisation | critical | Personal data embedded in LLM prompts or agent memory | Article 5, Article 28, section 6, section 8 | 1 code regex, 1 trace regex |
| C03 | T05 pii_masking_pseudonymisation | high | Unmasked PII persisted to storage | Article 25, Article 32, section 8 | 1 code regex |
| C04 | T04 consent | high | Personal data processed without a consent gate | Article 6, Article 7, section 4, section 6 | absence check |
| C05 | T04 consent | high | Pre-ticked or non-granular consent | Article 4, Article 7, section 6 | 2 code regex |
| C06 | T02 purpose_limitation | high | Purpose drift or undisclosed secondary use | Article 5, Article 6, section 6, section 8 | 2 code regex, 1 trace regex |
| C07 | T10 retention_erasure | high | No retention limit or expiry for personal data | Article 5, section 8, section 12 | absence check |
| C08 | T10 retention_erasure | high | No erasure or withdrawal path | Article 17, Article 21, section 6, section 8, section 12 | absence check |
| C09 | T07 automated_decision_making | high | Significant automated decision without explanation | Article 22, Article 15, Article 86, section 8 | 1 trace regex, absence check, trace semantics |
| C10 | T15 human_oversight | high | No human review for high-impact decisions | Article 22, Article 14, Article 6, section 8 | absence check, trace semantics |
| C11 | T08 synthetic_content_transparency | high | Synthetic or AI-generated content without disclosure | Article 50, Article 5, section 5 | 1 trace regex, absence check, trace semantics |
| C12 | T08 synthetic_content_transparency | medium | AI interaction without user disclosure | Article 50, Article 13, section 5 | absence check |
| C13 | T09 children_data | critical | Child data without verifiable guardian consent | Article 8, section 9, Article 5 | absence check |
| C14 | T09 children_data | critical | Tracking or targeted advertising directed at children | section 9, Article 5 | 1 code regex |
| C15 | T17 breach_response | high | No breach detection and notification hook | Article 33, Article 34, section 8 | absence check |
| C16 | T13 cross_border_transfer | high | Cross-border transfer without transfer-control evidence | Article 44, Article 46, section 16 | absence check |
| C17 | T11 processor_governance | high | Processor used without a contract or DPA reference | Article 28, section 8 | absence check |
| C18 | T12 risk_impact_assessment | high | High-risk AI or processing without prior impact assessment | Article 35, Article 9, Article 27, section 10 | absence check |
| C19 | T16 accuracy_quality | medium | Decision inputs without completeness and accuracy checks | Article 5, Article 16, Article 10, section 8 | absence check |
| C20 | T06 security_safeguards | high | PII store without encryption at rest | Article 32, section 8 | absence check |
| C21 | T14 data_subject_rights | medium | No grievance redressal mechanism | section 13, Article 77 | absence check |
| C22 | T14 data_subject_rights | medium | No access or correction endpoint for individuals | Article 15, Article 16, section 11, section 12 | absence check |
| C23 | T18 prohibited_manipulative_practices | high | Manipulative interface or dark pattern | Article 5, Article 5, section 6 | 1 code regex |
| C24 | T12 risk_impact_assessment | medium | No audit logging of agent or model actions | Article 12, Article 26, section 10, Article 5 | absence check |
| C25 | T02 purpose_limitation | high | Purpose-bound access control in agent traces | Article 5, Article 6, section 6, Article 26 | 2 trace regex, trace semantics |

## Themes without a dedicated executable control

Themes T01 (lawfulness/transparency) and T03 (data minimisation) are enforced indirectly through controls attached to adjacent themes (for example C01, C02, C04 and C06). Adding first-class controls for these themes is tracked as a roadmap item.

