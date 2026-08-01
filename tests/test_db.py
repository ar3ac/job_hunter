import sqlite3
import tempfile
import unittest
from pathlib import Path

from db import connect, make_strong_key, save_jobs


def job(job_id, source="linkedin", status="recommended", score=80):
    return {
        "id": job_id,
        "source": source,
        "title": "Production Planner",
        "company": "ACME",
        "location": "Lecco",
        "location_actual": "Lecco, Lombardia",
        "url": f"https://example.test/jobs/{job_id}?tracking=1",
        "status": status,
        "score": score,
        "score_reasons": ["compatibile"],
        "matched_keywords": ["production planner"],
    }


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = connect(str(Path(self.tmp.name) / "jobs.db"))

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_schema_migrates_existing_database(self):
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(jobs)")}
        self.assertTrue({"score", "status", "content_key", "last_seen_at"} <= columns)

    def test_legacy_schema_is_migrated_without_data_loss(self):
        legacy_path = Path(self.tmp.name) / "legacy.db"
        legacy = sqlite3.connect(legacy_path)
        legacy.execute("""
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY, strong_key TEXT UNIQUE, soft_key TEXT,
                title TEXT, company TEXT, location TEXT,
                url TEXT, source TEXT, posted_at TEXT, fetched_at TEXT,
                description TEXT
            )
        """)
        legacy.execute(
            "INSERT INTO jobs(strong_key, soft_key, title, fetched_at) VALUES(?,?,?,?)",
            ("strong", "soft", "Legacy", "2025-01-01T00:00:00"),
        )
        legacy.commit()
        legacy.close()
        migrated = connect(str(legacy_path))
        row = migrated.execute(
            "SELECT title, content_key, first_seen_at, last_seen_at FROM jobs"
        ).fetchone()
        migrated.close()
        self.assertEqual(row, ("Legacy", "soft", "2025-01-01T00:00:00", "2025-01-01T00:00:00"))

    def test_same_content_is_not_inserted_twice(self):
        self.assertEqual(len(save_jobs(self.conn, [job("1")])), 1)
        duplicate = job("2", source="indeed")
        self.assertEqual(save_jobs(self.conn, [duplicate]), [])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)

    def test_recommended_upgrade_is_returned(self):
        save_jobs(self.conn, [job("1", status="rejected", score=10)])
        upgraded = save_jobs(self.conn, [job("2", status="recommended", score=80)])
        self.assertEqual(len(upgraded), 1)

    def test_location_actual_is_persisted(self):
        save_jobs(self.conn, [job("1")])
        value = self.conn.execute("SELECT loc_company FROM jobs").fetchone()[0]
        self.assertEqual(value, "Lecco, Lombardia")

    def test_linkedin_key_remains_url_based_for_legacy_compatibility(self):
        with_id = job("123")
        without_id = dict(with_id, id=None)
        self.assertEqual(make_strong_key(with_id), make_strong_key(without_id))

    def test_legacy_location_content_key_suppresses_repost(self):
        old = job("1")
        old.pop("location_actual")
        save_jobs(self.conn, [old])
        repost = job("2")
        repost["search_location"] = "Lecco"
        self.assertEqual(save_jobs(self.conn, [repost]), [])


if __name__ == "__main__":
    unittest.main()
