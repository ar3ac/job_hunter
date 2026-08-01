import unittest

from ranking import apply_evaluation, detect_experience, evaluate_job


SEARCH = {
    "name": "planner",
    "keywords": ["production planner"],
    "required_any": ["production planner", "pianificazione produzione"],
    "positive_keywords": ["mrp", "lean"],
    "exclude_keywords": ["software developer"],
    "location": "Lecco",
}

RULES = {
    "experience_max_years": 4,
    "seniority_exclude": ["senior", "lead", "manager"],
    "hard_exclude": ["corso di formazione", "formazione gratuita"],
}


class RankingTests(unittest.TestCase):
    def test_relevant_junior_permanent_job_is_recommended(self):
        result = evaluate_job({
            "title": "Junior Production Planner",
            "description": "MRP, contratto a tempo indeterminato, 2 anni di esperienza",
            "location_actual": "Lecco, Lombardia",
        }, SEARCH, RULES)
        self.assertEqual(result.status, "recommended")
        self.assertGreaterEqual(result.score, 80)
        self.assertEqual(result.contract_type, "tempo_indeterminato")

    def test_senior_job_is_rejected(self):
        result = evaluate_job({
            "title": "Senior Production Planner",
            "description": "Esperienza di almeno 8 anni",
        }, SEARCH, RULES)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.seniority, "senior")

    def test_course_is_rejected(self):
        result = evaluate_job({
            "title": "Production Planner - corso di formazione gratuito",
            "description": "",
        }, SEARCH, RULES)
        self.assertEqual(result.status, "rejected")

    def test_unrelated_advertisement_is_rejected(self):
        result = evaluate_job({
            "title": "Cappellino con luce LED ricaricabile",
            "description": "Promozione prodotto",
        }, SEARCH, RULES)
        self.assertEqual(result.status, "rejected")
        self.assertLess(result.score, 50)

    def test_experience_range(self):
        self.assertEqual(detect_experience("richiesti 3-5 anni di esperienza"), (3, 5))

    def test_evaluation_is_serializable_on_job(self):
        job = apply_evaluation({"title": "Production Planner", "company": "ACME"}, SEARCH, RULES)
        self.assertEqual(job["search"], "planner")
        self.assertIsInstance(job["score_reasons"], list)


if __name__ == "__main__":
    unittest.main()
