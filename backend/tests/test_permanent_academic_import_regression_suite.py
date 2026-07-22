import os
import sys
import json
import unittest
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"
PDF_PATH = os.path.abspath(os.path.dirname(__file__) + "/dataset/Edge_Case_Academic_Schedule_Test.pdf")

class TestPermanentAcademicImportRegressionSuite(unittest.TestCase):
    """
    PERMANENT ACADEMIC IMPORT REGRESSION TEST SUITE
    Guarantees zero regressions for all previously fixed bugs.
    """

    @classmethod
    def setUpClass(cls):
        # 1. Authenticate HTTP Session
        r_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "punithgodof@gmail.com", "password": "Punith@123"})
        assert r_login.status_code == 200, f"Login failed: {r_login.text}"
        cls.token = r_login.json().get("access_token")
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # 2. Upload actual binary PDF
        assert os.path.exists(PDF_PATH), f"Test PDF missing at {PDF_PATH}"
        with open(PDF_PATH, "rb") as f:
            pdf_bytes = f.read()

        files = {"file": ("Edge_Case_Academic_Schedule_Test.pdf", pdf_bytes, "application/pdf")}
        r_upload = requests.post(f"{BASE_URL}/api/import/upload", headers=cls.headers, files=files)
        assert r_upload.status_code == 200, f"Upload failed: {r_upload.status_code} - {r_upload.text}"
        
        cls.res_json = r_upload.json()
        cls.sections = cls.res_json.get("sections", [])

    def test_reg_001_corrected_deadline_override(self):
        """REG-001: Corrected deadline must override superseded date."""
        dbms_sec = next((s for s in self.sections if "dbms" in s.get("display_name", "").lower()), None)
        self.assertIsNotNone(dbms_sec, "REG-001 FAIL: DBMS section missing")
        fields = {f.get("field_name"): f.get("value") for f in dbms_sec.get("fields", [])}
        self.assertIn("27 Aug 2026", fields.get("due_date", ""), "REG-001 FAIL: DBMS corrected deadline not applied")
        self.assertIn("25 Aug 2026", fields.get("superseded_date", ""), "REG-001 FAIL: DBMS superseded lineage missing")

    def test_reg_002_relative_date_math_48h(self):
        """REG-002: Relative date math (+48h) must compute 30 Aug 2026."""
        heap_rep = next((s for s in self.sections if "heap sort report" in s.get("display_name", "").lower()), None)
        self.assertIsNotNone(heap_rep, "REG-002 FAIL: Heap Sort Report section missing")
        fields = {f.get("field_name"): f.get("value") for f in heap_rep.get("fields", [])}
        self.assertIn("30 Aug 2026", fields.get("due_date", ""), "REG-002 FAIL: +48h relative date math failed")

    def test_reg_003_zero_entity_stealing(self):
        """REG-003: Dr. A. Kumar bound exclusively to DBMS; OS Mid Exam faculty = null."""
        os_sec = next((s for s in self.sections if "os mid exam" in s.get("display_name", "").lower()), None)
        self.assertIsNotNone(os_sec, "REG-003 FAIL: OS Mid Exam section missing")
        fields = {f.get("field_name"): f.get("value") for f in os_sec.get("fields", [])}
        self.assertIsNone(fields.get("faculty"), "REG-003 FAIL: Entity Stealing Bug! Dr. A. Kumar attached to OS!")

    def test_reg_004_venue_extraction(self):
        """REG-004: OS Mid Exam venue must be Block B-204."""
        os_sec = next((s for s in self.sections if "os mid exam" in s.get("display_name", "").lower()), None)
        fields = {f.get("field_name"): f.get("value") for f in os_sec.get("fields", [])}
        self.assertEqual(fields.get("venue"), "Block B-204", "REG-004 FAIL: OS Exam venue missing or incorrect")

    def test_reg_005_relative_thursday_date_calculation(self):
        """REG-005: Next Thursday after 2 Sept notice must compute 10 Sept 2026."""
        net_sec = next((s for s in self.sections if "networks quiz" in s.get("display_name", "").lower()), None)
        self.assertIsNotNone(net_sec, "REG-005 FAIL: Networks Quiz section missing")
        fields = {f.get("field_name"): f.get("value") for f in net_sec.get("fields", [])}
        self.assertIn("10 Sept 2026", fields.get("due_date", ""), "REG-005 FAIL: Relative Thursday calculation failed")

    def test_reg_006_suppressed_instruction_routing(self):
        """REG-006: AI Workshop with DO NOT AUTO-CREATE must be routed to ignored_item."""
        ai_sec = next((s for s in self.sections if "ai workshop" in s.get("display_name", "").lower()), None)
        self.assertIsNotNone(ai_sec, "REG-006 FAIL: AI Workshop section missing")
        self.assertEqual(ai_sec.get("document_type"), "ignored_item", "REG-006 FAIL: AI Workshop not classified as ignored_item")

    def test_reg_007_ambiguous_week_3_detection(self):
        """REG-007: Mini Project with Week 3 must be routed to needs_confirmation."""
        mini_sec = next((s for s in self.sections if "mini project" in s.get("display_name", "").lower()), None)
        self.assertIsNotNone(mini_sec, "REG-007 FAIL: Mini Project section missing")
        self.assertEqual(mini_sec.get("document_type"), "needs_confirmation", "REG-007 FAIL: Mini Project not flagged as needs_confirmation")

    def test_reg_008_canonical_subject_normalization(self):
        """REG-008: DBMS -> Database Management Systems, OS -> Operating Systems."""
        dbms_sec = next((s for s in self.sections if "dbms" in s.get("display_name", "").lower()), None)
        fields = {f.get("field_name"): f.get("value") for f in dbms_sec.get("fields", [])}
        self.assertEqual(fields.get("subject"), "Database Management Systems", "REG-008 FAIL: DBMS subject normalization failed")

    def test_reg_009_dynamic_priority_scoring_and_inferred_hours(self):
        """REG-009: OS Exam -> Priority 92.0 (Critical) / 6.0 hrs; Quiz -> Priority 29.0 (Low) / 1.0 hr."""
        os_sec = next((s for s in self.sections if "os mid exam" in s.get("display_name", "").lower()), None)
        fields = {f.get("field_name"): f.get("value") for f in os_sec.get("fields", [])}
        self.assertIn("92.0", fields.get("priority_preview", ""), "REG-009 FAIL: OS Exam priority score incorrect")
        self.assertIn("6.0 hrs", fields.get("estimated_hours", ""), "REG-009 FAIL: OS Exam inferred study hours incorrect")

    def test_reg_010_approved_import_task_creation_exclusion(self):
        """REG-010: POST /api/import/approve must create tasks for active items and exclude ignored items."""
        reviewed_sections = [
            {"document_type": s.get("document_type"), "fields": {f.get("field_name"): f.get("value") for f in s.get("fields", [])}}
            for s in self.sections
        ]
        r_approve = requests.post(f"{BASE_URL}/api/import/approve", headers=self.headers, json={"import_id": self.res_json.get("import_id"), "reviewed_sections": reviewed_sections})
        self.assertEqual(r_approve.status_code, 200, f"REG-010 FAIL: Approve endpoint returned {r_approve.status_code}")
        data = r_approve.json()
        self.assertGreaterEqual(data.get("tasks_created", 0), 6, "REG-010 FAIL: Expected at least 6 active tasks created")

if __name__ == "__main__":
    unittest.main()
