import unittest
from pathlib import Path

import yaml


TARGET_ROLES = {
    "production planner",
    "pianificatore di produzione",
    "addetto programmazione produzione",
    "production planning specialist",
    "production scheduler",
    "material planner",
    "material scheduler",
    "supply planner",
    "supply chain planner",
    "industrial planner",
    "production planning analyst",
    "supply chain analyst",
    "operations analyst",
    "planning analyst",
    "logistics analyst",
    "process analyst",
    "sap key user",
    "sap pp key user",
    "sap mm key user",
    "reporting automation analyst",
}


class ProfileTests(unittest.TestCase):
    def test_all_target_roles_are_configured(self):
        config = yaml.safe_load(Path("profile.yaml").read_text(encoding="utf-8"))
        configured = {
            str(role).casefold()
            for search in config["searches"]
            for role in search.get("required_any", [])
        }
        self.assertEqual(TARGET_ROLES - configured, set())

    def test_operational_searches_are_preserved(self):
        config = yaml.safe_load(Path("profile.yaml").read_text(encoding="utf-8"))
        names = {search["name"] for search in config["searches"]}
        self.assertTrue({"magazziniere", "logistica"} <= names)


if __name__ == "__main__":
    unittest.main()
