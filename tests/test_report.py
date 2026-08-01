import unittest

from report import render_html


class ReportTests(unittest.TestCase):
    def test_score_and_reasons_are_rendered_and_escaped(self):
        html = render_html([{
            "title": "Planner <script>",
            "company": "ACME",
            "score": 88,
            "score_reasons": ["ruolo compatibile"],
            "url": "https://example.test/job",
        }], summary={"found": 3, "recommended": 1, "review": 1, "rejected": 1})
        self.assertIn("88/100", html)
        self.assertIn("ruolo compatibile", html)
        self.assertNotIn("Planner <script>", html)
        self.assertIn("Raccolti: 3", html)

    def test_failure_report_without_jobs(self):
        html = render_html([], summary={
            "found": 0, "review": 0, "rejected": 0,
            "source_failures": ["planner/linkedin: timeout"],
        })
        self.assertIn("Ricerche non completate", html)
        self.assertIn("planner/linkedin: timeout", html)


if __name__ == "__main__":
    unittest.main()
