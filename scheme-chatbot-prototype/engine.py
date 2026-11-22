import json
import re
from pathlib import Path

import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUTPUTS = BASE / "outputs"


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


UI = {
    "welcome": {
        "en": "Namaste! I am the Village Benefit Assistant. I can suggest government schemes and show the documents and steps to apply. What do you need help with?",
        "hi": "नमस्ते! मैं ग्राम लाभ सहायक हूँ। मैं योजनाएँ सुझा सकता हूँ और आवेदन के दस्तावेज़ व कदम बता सकता हूँ। आपको किस विषय में मदद चाहिए?",
        "ur": "السلام علیکم! میں گاؤں فائدہ معاون ہوں۔ میں آپ کو اسکیمیں بتا سکتا ہوں اور درخواست کے لیے دستاویزات اور اقدامات بتا سکتا ہوں۔ آپ کو کس چیز میں مدد چاہیے؟",
        "de": "Namaste! Ich bin der Dorf-Leistungsassistent. Ich schlage passende Leistungen vor und zeige Dokumente und Antragsschritte. Wobei kann ich helfen?",
    },
    "ask_again": {"en": "Please answer: ", "hi": "कृपया बताएँ: ", "ur": "براہ کرم بتائیں: ", "de": "Bitte antworten Sie: "},
    "results": {
        "en": "Based on your answers, these schemes may be relevant:",
        "hi": "आपके जवाबों के अनुसार ये योजनाएँ प्रासंगिक हो सकती हैं:",
        "ur": "آپ کے جوابات کی بنیاد پر یہ اسکیمیں متعلقہ ہو سکتی ہیں:",
        "de": "Auf Basis Ihrer Angaben könnten diese Leistungen passen:",
    },
    "no_results": {
        "en": "I could not find a strong match yet. Try describing your need, or answer a few more questions.",
        "hi": "मुझे अभी कोई मज़बूत मैच नहीं मिला। अपनी आवश्यकता बताएँ या कुछ और प्रश्नों के उत्तर दें।",
        "ur": "ابھی تک کوئی مضبوط مماثلت نہیں ملی۔ اپنی ضرورت بتائیں یا مزید سوالات کے جواب دیں۔",
        "de": "Ich habe noch keine gute Übereinstimmung gefunden. Beschreiben Sie Ihr Anliegen oder beantworten Sie weitere Fragen.",
    },
    "why": {"en": "Why", "hi": "कारण", "ur": "وجہ", "de": "Grund"},
    "documents": {"en": "Documents", "hi": "दस्तावेज़", "ur": "دستاویزات", "de": "Dokumente"},
    "steps": {"en": "How to apply", "hi": "आवेदन कैसे करें", "ur": "درخواست کیسے دیں", "de": "Antragsschritte"},
    "office": {"en": "Where to go", "hi": "कहाँ जाएँ", "ur": "کہاں جائیں", "de": "Anlaufstelle"},
    "sources": {"en": "Official sources", "hi": "आधिकारिक स्रोत", "ur": "سرکاری ذرائع", "de": "Offizielle Quellen"},
    "disclaimer": {
        "en": "Indicative guidance only: the official authority decides eligibility.",
        "hi": "केवल संकेतात्मक मार्गदर्शन: पात्रता का निर्णय आधिकारिक विभाग करता है।",
        "ur": "صرف رہنمائی: اہلیت کا فیصلہ سرکاری محکمہ کرتا ہے۔",
        "de": "Nur eine Orientierung: Die Behörde entscheidet über die Berechtigung.",
    },
    "need_more": {
        "en": "I need a little more information to narrow this down.",
        "hi": "इसे सीमित करने के लिए मुझे थोड़ी और जानकारी चाहिए।",
        "ur": "اسے محدود کرنے کے لیے مجھے تھوڑی مزید معلومات چاہیے۔",
        "de": "Ich brauche noch ein paar Angaben für ein genaueres Ergebnis.",
    },
    "yes": {"en": "yes", "hi": "हाँ", "ur": "ہاں", "de": "ja"},
    "no": {"en": "no", "hi": "नहीं", "ur": "نہیں", "de": "nein"},
}

YES_WORDS = ["yes", "y", "true", "haan", "ha", "जी हां", "हाँ", "हां", "جی ہاں", "ہاں", "ja", "jawohl", "sí", "si"]
NO_WORDS = ["no", "n", "false", "nahi", "नहीं", "नही", "نہیں", "نہیں", "nein", "nein danke"]

PRESENCE_TRUE_FIELDS = {
    "poor_household", "kutcha_house", "houseless", "willing_unskilled_work",
    "pregnant_or_lactating", "disadvantaged_category", "widow", "disability_severe",
    "children_under_25", "de_resident", "rent_or_housing_costs",
    "receives_grundsicherung", "single_parent",
}

CHOICE_WORDS = {
    "country": {
        "IN": ["india", "bharat", "indien", "भारत", "हिन्दुस्तान", "ہندوستان"],
        "DE": ["germany", "deutschland", "जर्मनी", "جرمنی"],
    },
    "residence": {
        "rural": ["rural", "village", "gaon", "गाँव", "ग्रामीण", "گاؤں", "دیہی", "dorf", "land"],
        "urban": ["urban", "city", "town", "शहर", "شہر", "شہری", "stadt"],
    },
    "gender": {
        "female": ["woman", "women", "female", "महिला", "स्त्री", "عورت", "خاتون", "frau", "weiblich"],
        "male": ["man", "male", "पुरुष", "مرد", "mann", "männlich"],
        "other": ["other", "अन्य", "دیگر", "divers", "other"],
    },
    "landholding": {
        "landholder_before_2019": ["yes", "before 2019", "2019 se pehle", "पहले", "पहले से", "2019 से पहले", "2019 سے پہلے", "seit 2019", "before", "old land"],
        "landholder_after_2019": ["after 2019", "2019 के बाद", "2019 کے بعد", "nach 2019", "new land"],
        "landless": ["no", "landless", "no land", "भूमिहीन", "जमीन नहीं", "زمین نہیں", "kein land"],
    },
    "income_band": {
        "very_low": ["very low", "not enough", "बहुत कम", "بہت کم", "sehr gering", "existenz"],
        "low": ["कम आय", "कम", "کم آمدنی", "gering"],
        "moderate": ["moderate", "medium", "मध्यम", "درمیانی", "mittel"],
        "higher": ["higher", "high", "अधिक", "زیادہ", "höher", "hoch"],
    },
}

BOOLEAN_HINTS = {
    "income_tax_payer": ["income tax", "आयकर", "انکم ٹیکس", "einkommensteuer"],
    "government_employee": ["government employee", "सरकारी कर्मचारी", "سرکاری ملازم", "staatsbedienstet"],
    "poor_household": ["bpl", "poor", "गरीब", "غریب", "arm", "deprivation"],
    "secc_listed": ["secc", "ayushman", "आयुष्मान", "آیوشمان"],
    "kutcha_house": ["kutcha", "कच्चा", "کچا", "mud", "lehm"],
    "houseless": ["houseless", "no shelter", "घर नहीं", "گھر نہیں", "obdachlos"],
    "willing_unskilled_work": ["unskilled", "manual work", "काम करना", "کام", "handarbeit"],
    "existing_lpg_connection": ["lpg", "gas connection", "गैस", "گیس", "gasanschluss"],
    "pregnant_or_lactating": ["pregnant", "breastfeed", "गर्भवती", "حاملہ", "schwanger", "still"],
    "disadvantaged_category": ["sc", "st", "job card", "बीपीएल", "राशन कार्ड", "bpl", "8 lakh"],
    "widow": ["widow", "विधवा", "بیوہ", "verwitwet"],
    "disability_severe": ["disability", "विकलांग", "معذوری", "behinderung", "80%"],
    "children_under_25": ["child", "children", "बच्चा", "بچہ", "kind", "25"],
    "de_resident": ["germany", "जर्मनी", "جرمنی", "deutschland"],
    "employable": ["work", "काम", "کام", "arbeiten", "erwerbsfähig"],
    "rent_or_housing_costs": ["rent", "kiral", "किराया", "کرایہ", "miete"],
    "receives_grundsicherung": ["grundsicherung", "bürgergeld", "burgergeld", "बर्गरगेल्ड", "برگرگلڈ"],
    "single_parent": ["single parent", "alleinerziehend", "अकेले", "تنہا"],
}


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def localize(value, lang, fallback_lang="en"):
    if isinstance(value, dict):
        return value.get(lang) or value.get(fallback_lang) or next(iter(value.values()), "")
    return value if value is not None else ""


def tr(key, lang):
    return UI.get(key, {}).get(lang, UI.get(key, {}).get("en", key))


class KnowledgeBase:
    def __init__(self, schemes_path=None, sources_path=None):
        self.bundle = load_json(schemes_path or DATA / "schemes.json")
        self.sources = load_json(sources_path or DATA / "sources.json")["sources"]
        self.schemes = self.bundle["schemes"]
        self.fields = self.bundle["fields"]
        self.needs = self.bundle["needs"]
        self.by_id = {s["id"]: s for s in self.schemes}
        self.field_by_id = {f["id"]: f for f in self.fields}
        self.source_by_id = {s["id"]: s for s in self.sources}
        self.corpus = self._build_corpus()
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(self.corpus)
        self.graph, self.graph_payload = self._build_graph()

    def _scheme_text(self, scheme):
        parts = []
        for key in ("name", "summary", "aliases", "keywords"):
            value = scheme.get(key, {})
            if isinstance(value, dict):
                for item in value.values():
                    parts.extend(item if isinstance(item, list) else [item])
            elif isinstance(value, list):
                parts.extend(value)
        parts.append(localize(self.needs.get(scheme["need"], {}), "en"))
        return " ".join(str(p) for p in parts if p)

    def _build_corpus(self):
        return [self._scheme_text(scheme) for scheme in self.schemes]

    def rank_by_message(self, message, limit=5):
        if not normalize(message):
            return {}
        query = self.vectorizer.transform([message])
        scores = (self.matrix @ query.T).toarray().reshape(-1)
        ranked = sorted(zip(self.schemes, scores), key=lambda pair: pair[1], reverse=True)
        return {s["id"]: float(score) for s, score in ranked[:limit] if score > 0.02}

    def _build_graph(self):
        graph = nx.DiGraph()
        for country in ("IN", "DE"):
            graph.add_node(f"country:{country}", type="Country", label=country)
        for need_id, labels in self.needs.items():
            graph.add_node(f"need:{need_id}", type="Need", label=localize(labels, "en"))
        for field in self.fields:
            graph.add_node(f"field:{field['id']}", type="ProfileField", label=field["id"])
        for source in self.sources:
            graph.add_node(f"source:{source['id']}", type="Source", label=source["title"])
        for scheme in self.schemes:
            sid = scheme["id"]
            graph.add_node(f"scheme:{sid}", type="Scheme", label=localize(scheme["name"], "en"))
            graph.add_edge(f"scheme:{sid}", f"country:{scheme['country']}", relation="APPLIES_IN")
            graph.add_edge(f"scheme:{sid}", f"need:{scheme['need']}", relation="COVERS")
            for rule in scheme["rules"]:
                if "field" in rule:
                    graph.add_edge(f"scheme:{sid}", f"field:{rule['field']}", relation="REQUIRES" if rule.get("kind") != "exclusion" else "EXCLUDES_IF", label=rule.get("label", ""))
            for source_id in scheme["sources"]:
                if source_id in self.source_by_id:
                    graph.add_edge(f"scheme:{sid}", f"source:{source_id}", relation="CITED_BY")
            for relation in scheme.get("relations", []):
                target = relation["target"]
                if target in self.by_id:
                    graph.add_edge(f"scheme:{sid}", f"scheme:{target}", relation=relation["type"], label=relation.get("label", ""))
        payload = {
            "nodes": [
                {"id": node, **data} for node, data in graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "relation": data.get("relation"), "label": data.get("label", "")}
                for u, v, data in graph.edges(data=True)
            ],
        }
        return graph, payload

    def neighbors(self, scheme_id):
        node = f"scheme:{scheme_id}"
        if node not in self.graph:
            return []
        return [
            {"id": neighbor, "relation": data.get("relation"), "label": data.get("label", "")}
            for _, neighbor, data in self.graph.out_edges(node, data=True)
        ]

    def export_turtle(self):
        def lit(text):
            return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'

        lines = [
            "@prefix ex: <http://example.org/benefit#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "",
        ]
        for scheme in self.schemes:
            sid = scheme["id"]
            lines.append(f"ex:{sid} a ex:BenefitScheme ;")
            lines.append(f"  ex:country {lit(scheme['country'])} ;")
            lines.append("  rdfs:label " + ", ".join(f"{lit(localize(scheme['name'], lang))}@{lang}" for lang in ("en", "hi", "ur", "de") if localize(scheme["name"], lang)) + " ;")
            lines.append(f"  ex:covers ex:need_{scheme['need']} ;")
            for source_id in scheme["sources"]:
                lines.append(f"  ex:source ex:src_{source_id} ;")
            for relation in scheme.get("relations", []):
                lines.append(f"  ex:{relation['type'].lower()} ex:{relation['target']} ;")
            for rule in scheme["rules"]:
                if rule.get("kind") == "exclusion":
                    continue
                field = rule.get("field")
                if field:
                    lines.append(f"  ex:requires ex:{sid}_{rule['id']} ;")
            lines[-1] = lines[-1].rstrip(" ;") + " ."
            lines.append("")
            for rule in scheme["rules"]:
                if rule.get("field"):
                    value = json.dumps(rule["value"], ensure_ascii=False)
                    lines.append(f"ex:{sid}_{rule['id']} a ex:Criterion ; ex:field {lit(rule['field'])} ; ex:operator {lit(rule['op'])} ; ex:value {lit(value)} .")
        lines.append("")
        for source in self.sources:
            lines.append(f"ex:src_{source['id']} a ex:OfficialSource ; rdfs:label {lit(source['title'])} ; ex:url <{source['url']}> ; ex:tier {lit(source['tier'])} .")
        return "\n".join(lines) + "\n"


class RuleEvaluator:
    @staticmethod
    def compare(field, op, expected, actual):
        if op == "any_of":
            results = [
                RuleEvaluator.compare(item["field"], item["op"], item["value"], (actual or {}).get(item["field"]))
                for item in field
            ]
            if any(result is True for result in results):
                return True
            if all(result is False for result in results):
                return False
            return None
        if actual is None:
            return None
        if op == "eq":
            return actual == expected
        if op == "neq":
            return actual != expected
        if op == "in":
            return actual in expected
        if op == "gte":
            try:
                return float(actual) >= float(expected)
            except (TypeError, ValueError):
                return None
        if op == "lte":
            try:
                return float(actual) <= float(expected)
            except (TypeError, ValueError):
                return None
        return None

    def evaluate(self, scheme, profile):
        matched, missing, failed, triggered = [], [], [], []
        for rule in scheme["rules"]:
            if rule["op"] == "any_of":
                result = self.compare(rule["conditions"], "any_of", None, profile)
                fields = [c["field"] for c in rule["conditions"]]
            else:
                field = rule["field"]
                result = self.compare(field, rule["op"], rule["value"], profile.get(field))
                fields = [field]
            if rule.get("kind") == "exclusion":
                if result is False:
                    triggered.append(rule)
                elif result is None:
                    missing.append((rule, fields))
                else:
                    matched.append(rule)
            else:
                if result is True:
                    matched.append(rule)
                elif result is False:
                    failed.append(rule)
                else:
                    missing.append((rule, fields))

        if triggered or failed:
            status = "ineligible"
        elif missing:
            status = "needs_info"
        else:
            status = "eligible"

        score = sum(rule.get("weight", 1) for rule in matched)
        score -= sum(rule.get("weight", 1) for rule in triggered) * 2
        score -= sum(rule.get("weight", 1) for rule in failed) * 2
        return {
            "status": status,
            "score": score,
            "matched": [rule["id"] for rule in matched],
            "failed": [rule["id"] for rule in failed],
            "triggered_exclusions": [rule["id"] for rule in triggered],
            "missing_fields": sorted({f for _, fields in missing for f in fields}),
            "reasons": [rule.get("label", rule["id"]) for rule in matched[:3]],
        }


class ProfileExtractor:
    @staticmethod
    def parse_bool(message):
        text = normalize(message)
        for word in YES_WORDS:
            if re.search(r"(^|\W)" + re.escape(normalize(word)) + r"(\W|$)", text):
                return True
        for word in NO_WORDS:
            if re.search(r"(^|\W)" + re.escape(normalize(word)) + r"(\W|$)", text):
                return False
        return None

    @staticmethod
    def parse_choice(field_id, message, kb):
        text = normalize(message)
        field = kb.field_by_id.get(field_id, {})
        for option in field.get("options", []):
            value = normalize(option["value"])
            candidates = ([option["value"]] if len(value) >= 3 else []) + CHOICE_WORDS.get(field_id, {}).get(option["value"], [])
            candidates.extend(localize(option.get("label", {}), lang).lower() for lang in ("en", "hi", "ur", "de"))
            for candidate in candidates:
                candidate = normalize(candidate)
                if candidate and re.search(r"(?<!\w)" + re.escape(candidate) + r"(?!\w)", text):
                    return option["value"]
        return None

    @staticmethod
    def parse_number(message):
        match = re.search(r"\d+(?:\.\d+)?", str(message))
        return float(match.group()) if match else None

    def extract(self, message, profile, kb, expecting=None, lang="en"):
        updated = dict(profile or {})
        if expecting and expecting in kb.field_by_id:
            field = kb.field_by_id[expecting]
            value = None
            if field["type"] == "boolean":
                value = self.parse_bool(message)
            elif field["type"] == "choice":
                value = self.parse_choice(expecting, message, kb)
            elif field["type"] == "number":
                value = self.parse_number(message)
            if value is not None:
                updated[expecting] = value

        age_match = re.search(r"(?:i am|age|उम्र|عمر|alter|years| سال|साल)\D{0,12}(\d{1,3})", str(message), flags=re.I)
        if age_match:
            updated["age"] = float(age_match.group(1))

        for field_id in ("country", "residence", "gender", "landholding", "income_band"):
            if field_id not in updated or expecting == field_id:
                value = self.parse_choice(field_id, message, kb)
                if value is not None:
                    updated[field_id] = value

        text = normalize(message)
        for field_id, hints in BOOLEAN_HINTS.items():
            if expecting == field_id or field_id in updated:
                continue
            matched_hint = False
            for hint in hints:
                if len(hint) <= 3:
                    matched_hint = bool(re.search(r"\b" + re.escape(hint) + r"\b", text))
                else:
                    matched_hint = hint in text
                if matched_hint:
                    break
            if matched_hint:
                value = self.parse_bool(message)
                if value is not None:
                    updated[field_id] = value
                elif field_id in PRESENCE_TRUE_FIELDS:
                    updated[field_id] = True
        for field_id in ("widow", "children_under_25", "pregnant_or_lactating", "disability_severe", "rent_or_housing_costs", "receives_grundsicherung", "de_resident", "poor_household", "kutcha_house"):
            if expecting == field_id or field_id in updated:
                continue
            for phrase in CHOICE_WORDS.get(field_id, {}).get(True, []):
                if phrase in text:
                    updated[field_id] = True
        disability = re.search(r"(\d{2,3})\s*(?:%|percent|प्रतिशत|فیصد|prozent)", str(message), flags=re.I)
        if disability:
            updated["disability_severe"] = float(disability.group(1)) >= 80
        return updated


class ChatEngine:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.evaluator = RuleEvaluator()
        self.extractor = ProfileExtractor()
        OUTPUTS.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def wants_results(message):
        text = normalize(message)
        return any(token in text for token in ["result", "recommend", "show scheme", "show schemes", "show me schemes", "eligible schemes", "नतीजा", "दिखाओ", "योजनाएँ", "نتیجہ", "دکھائیں", "ergebnis", "vorschläge", "passende"])

    @staticmethod
    def asks_detail(message):
        text = normalize(message)
        return any(token in text for token in ["document", "documents", "required", "dastavez", "दस्तावेज़", "दस्तावेज", "कागजात", "دستاویز", "unterlagen", "dokumente", "how to apply", "apply", "आवेदन", "درخواست", "beantragen", "deadline", "office", "कार्यालय", "دفتر", "amt"])

    def scheme_from_message(self, message):
        scores = self.kb.rank_by_message(message, limit=3)
        if not scores:
            return None
        return max(scores, key=scores.get)

    def evaluate_all(self, profile):
        results = []
        for scheme in self.kb.schemes:
            if profile.get("country") and scheme["country"] != profile["country"]:
                continue
            results.append((scheme, self.evaluator.evaluate(scheme, profile)))
        return results

    def pick_question(self, profile, message_scores):
        requirements = []
        exclusions = []
        for scheme, evaluation in self.evaluate_all(profile):
            if evaluation["status"] != "needs_info":
                continue
            requirement_ids = {rule["id"] for rule in scheme["rules"] if rule.get("kind") != "exclusion"}
            has_positive_requirement = any(rule_id in evaluation["matched"] for rule_id in requirement_ids)
            for rule in scheme["rules"]:
                fields = rule.get("conditions") or [{"field": rule.get("field")}]
                for condition in fields:
                    field_id = condition.get("field")
                    if not field_id or field_id in profile:
                        continue
                    weight = rule.get("weight", 1) + message_scores.get(scheme["id"], 0) * 30
                    if rule.get("kind") == "exclusion":
                        if has_positive_requirement:
                            exclusions.append((weight, field_id, scheme["id"]))
                    else:
                        requirements.append((weight, field_id, scheme["id"]))
        candidates = requirements or exclusions
        if not candidates:
            return None
        best = sorted(candidates, reverse=True)[0]
        return best[1], best[2]

    def ask(self, field_id, lang, scheme_id=None):
        field = self.kb.field_by_id[field_id]
        question = localize(field["question"], lang)
        if field["type"] == "boolean":
            suffix = f" ({tr('yes', lang)} / {tr('no', lang)})"
            question += suffix
        elif field["type"] == "choice":
            labels = []
            for option in field.get("options", []):
                labels.append(localize(option["label"], lang))
            question += " [" + ", ".join(labels) + "]"
        elif field["type"] == "number":
            question += " (12, 45, 60 ...)"
        if scheme_id and scheme_id in self.kb.by_id:
            question = localize(self.kb.by_id[scheme_id]["name"], lang) + " — " + question
        return question

    def format_detail(self, scheme_id, lang):
        scheme = self.kb.by_id[scheme_id]
        name = localize(scheme["name"], lang)
        lines = [f"**{name}**", localize(scheme["summary"], lang), ""]
        lines.append(f"{tr('documents', lang)}:")
        for doc in scheme["documents"][:5]:
            lines.append("• " + localize(doc, lang))
        lines.append("")
        lines.append(f"{tr('steps', lang)}:")
        for step in scheme["steps"]:
            lines.append("• " + localize(step, lang))
        lines.append("")
        lines.append(f"{tr('office', lang)}: {localize(scheme['office'], lang)}")
        lines.append(f"Helpline: {scheme['helpline']}")
        lines.append(f"Deadline: {scheme['deadline']}")
        lines.append(self.citation_line(scheme, lang))
        lines.append(tr("disclaimer", lang))
        return "\n".join(lines)

    def citation_line(self, scheme, lang):
        urls = []
        for source_id in scheme["sources"]:
            source = self.kb.source_by_id.get(source_id)
            if source:
                urls.append(source["url"])
        return f"{tr('sources', lang)}: " + " | ".join(urls[:3])

    def format_results(self, profile, lang, message_scores):
        evaluated = self.evaluate_all(profile)
        ranked = sorted(evaluated, key=lambda pair: (pair[1]["status"] == "ineligible", -(pair[1]["score"] + message_scores.get(pair[0]["id"], 0) * 30)))
        eligible = [pair for pair in ranked if pair[1]["status"] == "eligible"]
        possible = [pair for pair in ranked if pair[1]["status"] == "needs_info"]
        shown = (eligible + possible)[:4]
        if not shown:
            return tr("no_results", lang), []
        lines = [tr("results", lang), ""]
        matched_ids = []
        for scheme, evaluation in shown:
            matched_ids.append(scheme["id"])
            status = "OK" if evaluation["status"] == "eligible" else "?"
            lines.append(f"{status} **{localize(scheme['name'], lang)}**")
            lines.append("  " + localize(scheme["summary"], lang))
            lines.append(f"  {tr('why', lang)}: " + "; ".join(evaluation["reasons"][:2]))
            lines.append("  " + localize(scheme["benefit"], lang) if isinstance(scheme["benefit"], dict) else "  " + scheme["benefit"])
            lines.append("  " + tr("documents", lang) + ": " + ", ".join(localize(doc, lang) for doc in scheme["documents"][:3]))
            lines.append("  " + self.citation_line(scheme, lang))
            lines.append("")
        lines.append(tr("disclaimer", lang))
        return "\n".join(lines), matched_ids

    def answer(self, message, lang="en", profile=None, expecting=None, asked=0):
        lang = lang if lang in ("en", "hi", "ur", "de") else "en"
        clean_message = str(message or "").strip()
        profile = self.extractor.extract(clean_message, profile or {}, self.kb, expecting=expecting, lang=lang)
        profile["_asked"] = int(asked or profile.get("_asked", 0))
        current_scores = self.kb.rank_by_message(clean_message)
        has_intent = bool(current_scores) and max(current_scores.values()) >= 0.12
        scores = current_scores if has_intent else profile.get("_intent", {})
        if has_intent:
            profile["_intent"] = current_scores
        response = {
            "language": lang,
            "reply": "",
            "profile": profile,
            "expecting": None,
            "matches": [],
            "graph": [],
            "sources": [],
        }

        if not clean_message:
            response["reply"] = tr("welcome", lang)
            response["expecting"] = "country"
            return response

        detail_hint = self.asks_detail(clean_message)
        scheme_hint = self.scheme_from_message(clean_message)
        if detail_hint and scheme_hint and not self.wants_results(clean_message):
            response["reply"] = self.format_detail(scheme_hint, lang)
            response["matches"] = [scheme_hint]
            response["graph"] = self.kb.neighbors(scheme_hint)
            response["sources"] = self.kb.by_id[scheme_hint]["sources"]
            return response

        if self.wants_results(clean_message) or profile["_asked"] >= 8:
            reply, matches = self.format_results(profile, lang, scores)
            response["reply"] = reply
            response["matches"] = matches
            for scheme_id in matches:
                response["graph"].extend(self.kb.neighbors(scheme_id))
                response["sources"].extend(self.kb.by_id[scheme_id]["sources"])
            response["sources"] = list(dict.fromkeys(response["sources"]))
            return response

        if not profile.get("country"):
            response["reply"] = self.ask("country", lang)
            response["expecting"] = "country"
            profile["_asked"] += 1
            return response

        selection = self.pick_question(profile, scores)
        evaluated = self.evaluate_all(profile)
        ready = bool(evaluated) and all(item[1]["status"] != "needs_info" for item in evaluated)
        if selection and not ready:
            field_id, scheme_id = selection
            response["reply"] = tr("need_more", lang) + "\n" + self.ask(field_id, lang, scheme_id)
            response["expecting"] = field_id
            profile["_asked"] += 1
            return response

        reply, matches = self.format_results(profile, lang, scores)
        response["reply"] = reply
        response["matches"] = matches
        for scheme_id in matches:
            response["graph"].extend(self.kb.neighbors(scheme_id))
            response["sources"].extend(self.kb.by_id[scheme_id]["sources"])
        response["sources"] = list(dict.fromkeys(response["sources"]))
        return response


def export_artifacts(engine):
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    graph_path = OUTPUTS / "knowledge_graph.json"
    turtle_path = OUTPUTS / "knowledge_graph.ttl"
    graph_path.write_text(json.dumps(engine.kb.graph_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    turtle_path.write_text(engine.kb.export_turtle(), encoding="utf-8")
    return graph_path, turtle_path
