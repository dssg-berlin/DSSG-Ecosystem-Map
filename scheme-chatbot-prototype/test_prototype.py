import json
import unittest
from pathlib import Path

from app import app
from engine import OUTPUTS, ChatEngine, RuleEvaluator, export_artifacts

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"


class DataTests(unittest.TestCase):
    def test_schema_files_load(self):
        sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
        schemes = json.loads((DATA / "schemes.json").read_text(encoding="utf-8"))
        self.assertIn("collection_method", sources)
        self.assertIn("collector", sources)
        self.assertGreaterEqual(len(sources["sources"]), 20)
        self.assertGreaterEqual(len(schemes["schemes"]), 10)
        self.assertEqual(len(schemes["fields"]), 24)
        for required in ("id", "url", "publisher", "tier", "facts", "snippet"):
            for source in sources["sources"]:
                self.assertIn(required, source)
        for required in ("id", "country", "need", "rules", "documents", "steps", "sources"):
            for scheme in schemes["schemes"]:
                self.assertIn(required, scheme)

    def test_collection_report_exists(self):
        report = json.loads((DATA / "collection_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema_validation"], "pass")
        self.assertEqual(report["invalid_sources"], [])


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEvaluator()

    def test_comparators(self):
        self.assertTrue(self.engine.compare("age", "gte", 18, 42))
        self.assertFalse(self.engine.compare("age", "lte", 18, 42))
        self.assertIsNone(self.engine.compare("age", "gte", 18, None))
        self.assertTrue(self.engine.compare("country", "in", ["IN", "DE"], "IN"))

    def test_any_of(self):
        conditions = [
            {"field": "widow", "op": "eq", "value": True},
            {"field": "disability_severe", "op": "eq", "value": True},
        ]
        self.assertIs(self.engine.compare(conditions, "any_of", None, {"widow": True}), True)
        self.assertIs(self.engine.compare(conditions, "any_of", None, {"widow": False, "disability_severe": True}), True)
        self.assertIs(self.engine.compare(conditions, "any_of", None, {"widow": False, "disability_severe": False}), False)
        self.assertIs(self.engine.compare(conditions, "any_of", None, {}), None)

    def test_eligibility_states(self):
        kb = ChatEngine().kb
        pm_kisan = kb.by_id["pm_kisan"]
        eligible = self.engine.evaluate(pm_kisan, {
            "country": "IN",
            "landholding": "landholder_before_2019",
            "income_tax_payer": False,
            "government_employee": False,
        })
        ineligible = self.engine.evaluate(pm_kisan, {
            "country": "IN",
            "landholding": "landholder_before_2019",
            "income_tax_payer": True,
            "government_employee": False,
        })
        unknown = self.engine.evaluate(pm_kisan, {"country": "IN"})
        self.assertEqual(eligible["status"], "eligible")
        self.assertEqual(ineligible["status"], "ineligible")
        self.assertEqual(unknown["status"], "needs_info")
        self.assertIn("landholding", unknown["missing_fields"])


class ConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ChatEngine()

    def test_farmer_intent_and_landholding_answer(self):
        first = self.engine.answer("I am a small farmer in India, aged 42", "en", {}, None, 0)
        self.assertEqual(first["expecting"], "landholding")
        self.assertIn("PM-KISAN", first["reply"])
        second = self.engine.answer("yes", "en", first["profile"], first["expecting"], first["profile"]["_asked"])
        self.assertEqual(second["profile"]["landholding"], "landholder_before_2019")
        third = self.engine.answer("show me eligible schemes", "en", second["profile"], None, second["profile"]["_asked"])
        self.assertEqual(third["matches"][0], "pm_kisan")
        self.assertIn("Rs 6,000", third["reply"])
        self.assertTrue(any("pmkisan" in url or "pm-kisan" in url for url in third["sources"]))

    def test_german_family_intent(self):
        first = self.engine.answer("We live in Germany and have two children under 25", "en", {}, None, 0)
        self.assertEqual(first["profile"]["country"], "DE")
        self.assertEqual(first["profile"]["children_under_25"], True)
        result = self.engine.answer("show me schemes", "en", first["profile"], None, first["profile"]["_asked"])
        self.assertIn("kindergeld", result["matches"])

    def test_detail_answer(self):
        result = self.engine.answer("What documents are needed for PM-KISAN?", "en", {}, None, 0)
        self.assertEqual(result["matches"], ["pm_kisan"])
        self.assertIn("Documents", result["reply"])
        self.assertIn("How to apply", result["reply"])
        self.assertTrue(result["graph"])

    def test_language_fallback(self):
        for lang in ("en", "hi", "ur", "de"):
            result = self.engine.answer("", lang, {}, None, 0)
            self.assertEqual(result["language"], lang)
            self.assertTrue(result["reply"])

    def test_question_cap_forces_results(self):
        profile = {"country": "IN", "_asked": 8}
        result = self.engine.answer("nothing more", "en", profile, None, 8)
        self.assertIsNone(result["expecting"])
        self.assertTrue(result["matches"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health_and_schemes(self):
        health = self.client.get("/api/health").get_json()
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["schemes"], 13)
        schemes = self.client.get("/api/schemes?language=hi").get_json()
        self.assertEqual(len(schemes), 13)
        self.assertTrue(schemes[0]["name"])

    def test_chat_endpoint(self):
        response = self.client.post("/api/chat", json={"message": "I am a farmer in India", "language": "en"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("reply", data)
        self.assertIn("profile", data)
        self.assertEqual(data["api_version"], "1.0")

    def test_unknown_scheme(self):
        response = self.client.get("/api/schemes/not_a_scheme")
        self.assertEqual(response.status_code, 404)


class ExportTests(unittest.TestCase):
    def test_graph_exports(self):
        engine = ChatEngine()
        graph_path, turtle_path = export_artifacts(engine)
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        turtle = turtle_path.read_text(encoding="utf-8")
        self.assertGreater(len(graph["nodes"]), 40)
        self.assertGreater(len(graph["edges"]), 70)
        self.assertIn("@prefix ex:", turtle)
        self.assertIn("ex:pm_kisan a ex:BenefitScheme", turtle)
        self.assertIn("https://", turtle)
        self.assertTrue((OUTPUTS / "knowledge_graph.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
