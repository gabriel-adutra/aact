import unittest
import logging

from src.load.neo4j_client import Neo4jClient


class BonusIntegrationTest(unittest.TestCase):
    """
    Integration test (bônus): carrega um pequeno conjunto sintético no Neo4j
    usando o próprio loader e valida contagens e consultas básicas.
    """

    sample_data = [
        {
            "nct_id": "TEST_BONUS_1",
            "title": "Bonus Trial A",
            "phase": "PHASE2",
            "status": "RECRUITING",
            "drugs": [
                {"name": "Drug A", "route": "Oral", "dosage_form": "Tablet"},
                {"name": "Drug B", "route": "Unknown", "dosage_form": "Unknown"},
            ],
            "conditions": [{"name": "Condition Alpha"}],
            "sponsors": [{"name": "Sponsor One", "class": "INDUSTRY"}],
        },
        {
            "nct_id": "TEST_BONUS_2",
            "title": "Bonus Trial B",
            "phase": "PHASE3",
            "status": "COMPLETED",
            "drugs": [
                {"name": "Drug B", "route": "Subcutaneous", "dosage_form": "Injection"},
            ],
            "conditions": [{"name": "Condition Beta"}],
            "sponsors": [{"name": "Sponsor Two", "class": "OTHER"}],
        },
    ]

    @classmethod
    def setUpClass(cls):
        try:
            logging.basicConfig(level=logging.INFO)
            cls.logger = logging.getLogger("tests.test_bonus_integration")
            cls.client = Neo4jClient()
            cls.client.ensure_graph_schema()
            cls._cleanup()
            cls.client.load_trials_batch(cls.sample_data)
            cls.logger.info("Loaded sample batch into Neo4j for bonus test: %s", cls.sample_data)
        except Exception as exc:
            raise unittest.SkipTest(f"Neo4j not available for integration test: {exc}")

    @classmethod
    def tearDownClass(cls):
        try:
            cls._cleanup()
            cls.client.close_connection()
        except Exception:
            pass

    @classmethod
    def _cleanup(cls):
        cypher = """
        MATCH (t:Trial)
        WHERE t.nct_id STARTS WITH 'TEST_BONUS_'
        DETACH DELETE t
        """
        with cls.client.driver.session() as session:
            session.run(cypher)

    def test_counts_and_coverage(self):
        cypher = """
        MATCH (t:Trial)-[r:STUDIED_IN]->(d:Drug)
        WHERE t.nct_id STARTS WITH 'TEST_BONUS_'
        RETURN count(DISTINCT t) AS trials,
               count(DISTINCT d) AS drugs,
               count(r) AS edges,
               SUM(CASE WHEN r.route IS NOT NULL AND r.route <> 'Unknown' THEN 1 ELSE 0 END) AS with_route,
               SUM(CASE WHEN r.dosage_form IS NOT NULL AND r.dosage_form <> 'Unknown' THEN 1 ELSE 0 END) AS with_form
        """
        with self.client.driver.session() as session:
            rec = session.run(cypher).single()

        self.logger.info(
            "Counts/coverage | trials=%s, drugs=%s, edges=%s, route_known=%s, form_known=%s",
            rec["trials"], rec["drugs"], rec["edges"], rec["with_route"], rec["with_form"]
        )
        self.assertEqual(rec["trials"], 2)
        self.assertEqual(rec["drugs"], 2)
        self.assertEqual(rec["edges"], 3)
        self.assertGreaterEqual(rec["with_route"], 2)
        self.assertGreaterEqual(rec["with_form"], 2)

    def test_top_drugs_for_bonus_subset(self):
        cypher = """
        MATCH (d:Drug)<-[:STUDIED_IN]-(t:Trial)
        WHERE t.nct_id STARTS WITH 'TEST_BONUS_'
        RETURN d.name AS drug, count(t) AS trials
        ORDER BY trials DESC
        """
        with self.client.driver.session() as session:
            rows = list(session.run(cypher))

        self.logger.info("Top drugs (bonus subset): %s", rows)
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["drug"], "Drug B")
        self.assertEqual(rows[0]["trials"], 2)
        self.assertEqual(rows[1]["drug"], "Drug A")
        self.assertEqual(rows[1]["trials"], 1)


if __name__ == "__main__":
    unittest.main()

