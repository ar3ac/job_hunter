import unittest

from sources.linkedin import parse_job_cards


HTML = """
<div class="scaffold-layout__list"><ul>
  <li>
    <a class="job-card-list__title--link" href="/jobs/view/123/?tracking=x">
      <strong>Production Planner</strong>
    </a>
    <div class="artdeco-entity-lockup__subtitle">ACME</div>
    <ul class="job-card-container__metadata-wrapper"><li>Lecco, Lombardia</li></ul>
  </li>
  <li><span>Scheda malformata</span></li>
</ul></div>
"""


class LinkedinParserTests(unittest.TestCase):
    def test_parses_and_canonicalizes_card(self):
        jobs = parse_job_cards(HTML, "Lecco", 10)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["id"], "123")
        self.assertEqual(jobs[0]["company"], "ACME")
        self.assertEqual(jobs[0]["location_actual"], "Lecco, Lombardia")
        self.assertEqual(jobs[0]["url"], "https://www.linkedin.com/jobs/view/123")

    def test_missing_container_returns_empty_list(self):
        self.assertEqual(parse_job_cards("<html></html>", "Lecco", 10), [])


if __name__ == "__main__":
    unittest.main()
