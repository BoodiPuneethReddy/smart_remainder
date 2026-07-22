import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

# Import functions to test
from app.agents.learning_agent import (
    calculate_retention,
    schedule_revision,
    update_learning_profile,
)
from app.models.learning_profile import LearningProfile


class TestLearningAgent(unittest.TestCase):
    
    def test_calculate_retention_immediate(self):
        """Test that retention is 100% immediately after revision."""
        last_revision = datetime.now(timezone.utc)
        retention = calculate_retention(last_revision, interval_days=1)
        self.assertEqual(retention, 100.0)

    def test_calculate_retention_decay(self):
        """Test that retention decays deterministically over time."""
        # 4 days ago with interval of 1 (strength = 2.0 days)
        # R = e^(-4 / 2) = e^(-2) = ~13.5%
        last_revision = datetime.now(timezone.utc) - timedelta(days=4)
        retention = calculate_retention(last_revision, interval_days=1)
        self.assertAlmostEqual(retention, 13.5, delta=0.5)

    def test_calculate_retention_clamp(self):
        """Test that retention clamps at minimum 10.0%."""
        last_revision = datetime.now(timezone.utc) - timedelta(days=50)
        retention = calculate_retention(last_revision, interval_days=1)
        self.assertEqual(retention, 10.0)

    def test_spaced_repetition_increase(self):
        """Test that index increases on high performance (>= 80%)."""
        self.assertEqual(schedule_revision(1, 90.0), 3)
        self.assertEqual(schedule_revision(3, 85.0), 7)
        self.assertEqual(schedule_revision(14, 100.0), 30)
        self.assertEqual(schedule_revision(30, 95.0), 30) # clamp to max

    def test_spaced_repetition_decrease(self):
        """Test that index decreases on poor performance (< 60%)."""
        self.assertEqual(schedule_revision(30, 40.0), 14)
        self.assertEqual(schedule_revision(7, 20.0), 3)
        self.assertEqual(schedule_revision(1, 50.0), 1) # clamp to min

    def test_spaced_repetition_neutral(self):
        """Test that index remains unchanged on neutral performance (60% - 80%)."""
        self.assertEqual(schedule_revision(7, 70.0), 7)
        self.assertEqual(schedule_revision(14, 75.0), 14)

    def test_update_learning_profile_logic(self):
        """Test the mathematical update logic for mastery and confidence scores."""
        db_mock = MagicMock()
        
        # Mock profile search to return None (simulate new profile setup)
        db_mock.query().filter().first.return_value = None

        user_id = 1
        subject = "Physics"
        topic = "Quantum Mechanics"

        # Update profile with 100% score
        profile = update_learning_profile(
            db=db_mock,
            user_id=user_id,
            subject=subject,
            topic=topic,
            quiz_score=100.0,
            correct_count=3,
            total_questions=3,
        )

        # Expected mastery: 0.7 * 50.0 (default initial) + 0.3 * 100 = 65.0
        self.assertEqual(profile.mastery, 65.0)
        # Expected confidence: 50.0 (default initial) + 10 = 60.0
        self.assertEqual(profile.confidence, 60.0)
        # Expected interval: schedule_revision(1, 100.0) = 3
        self.assertEqual(profile.interval_days, 3)
        self.assertEqual(profile.revision_count, 1)
        self.assertEqual(profile.avg_quiz_score, 100.0)

    def test_build_mermaid_diagram(self):
        """Test that deterministic Mermaid compiler outputs syntactically correct graphs."""
        from app.services.tutor_service import build_mermaid_diagram
        diagram_data = {
            "type": "flowchart LR",
            "nodes": [
                {"id": "A", "label": "Concept X"},
                {"id": "B", "label": "Application Y"}
            ],
            "edges": [
                {"from": "A", "to": "B", "label": "transforms into"}
            ]
        }
        res = build_mermaid_diagram(diagram_data)
        self.assertIn("flowchart LR", res)
        self.assertIn('A["Concept X"]', res)
        self.assertIn('B["Application Y"]', res)
        self.assertIn('A -->|"transforms into"| B', res)

    def test_get_or_create_objectives(self):
        """Test that objectives are generated, merged, and prioritized (1-5 stars) correctly."""
        from app.services.tutor_service import get_or_create_objectives
        db_mock = MagicMock()
        db_mock.query().filter().all.return_value = [] # simulates new topic
        
        objectives = get_or_create_objectives(db_mock, "Database", "Keys")
        self.assertEqual(len(objectives), 5)
        self.assertEqual(objectives[0].subject, "Database")
        self.assertEqual(objectives[0].topic, "Keys")
        self.assertEqual(objectives[0].priority_stars, 5) # primary term objective
        self.assertEqual(objectives[4].priority_stars, 1) # history context objective


if __name__ == '__main__':
    unittest.main()
