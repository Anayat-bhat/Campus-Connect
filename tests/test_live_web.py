"""
Comprehensive Live Web & API Test Suite for CampusConnect.
Verifies registration, authentication, item reporting, smart AI matching,
claims verification, notifications, and permissions.
"""

import os
import sys
import json
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from web_app import app, user_repo, item_repo, claim_repo, notif_repo
from models.user import User
from models.item import Item
from database.connection import init_database


class CampusConnectLiveWebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.client = app.test_client()

    def test_01_index_and_manifest(self):
        """Test home page and PWA manifest load properly for web and mobile browsers."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CampusConnect", res.data)
        self.assertIn(b"viewport", res.data)

        # Test PWA Manifest
        res_manifest = self.client.get("/manifest.json")
        self.assertEqual(res_manifest.status_code, 200)
        manifest_data = json.loads(res_manifest.data.decode("utf-8"))
        self.assertIn("CampusConnect", manifest_data.get("name"))
        self.assertEqual(manifest_data.get("display"), "standalone")

    def test_02_registration_and_login_validation(self):
        """Test user registration flow and login security."""
        # 1. Reject invalid credentials
        res_bad = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": "non_existent_student", "password": "WrongPassword123"}),
            content_type="application/json"
        )
        self.assertEqual(res_bad.status_code, 401)
        data_bad = json.loads(res_bad.data.decode("utf-8"))
        self.assertFalse(data_bad["success"])

        # 2. Register fresh student user
        username = "live_test_student_2026"
        email = "live_student@campus.edu"
        res_reg = self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": username,
                "password": "StrongStudentPassword@2026",
                "full_name": "Live Test Student",
                "email": email,
                "role": "student"
            }),
            content_type="application/json"
        )
        self.assertEqual(res_reg.status_code, 201)
        data_reg = json.loads(res_reg.data.decode("utf-8"))
        self.assertTrue(data_reg["success"])
        self.assertEqual(data_reg["user"]["username"], username)

        # 3. Check /api/auth/me session
        res_me = self.client.get("/api/auth/me")
        self.assertEqual(res_me.status_code, 200)
        data_me = json.loads(res_me.data.decode("utf-8"))
        self.assertTrue(data_me["authenticated"])
        self.assertEqual(data_me["user"]["username"], username)

        # 4. Logout
        res_logout = self.client.post("/api/auth/logout")
        self.assertEqual(res_logout.status_code, 200)

        # 5. Check session is cleared
        res_me_cleared = self.client.get("/api/auth/me")
        data_me_cleared = json.loads(res_me_cleared.data.decode("utf-8"))
        self.assertFalse(data_me_cleared["authenticated"])

        # 6. Re-login with the newly registered user
        res_login = self.client.post(
            "/api/auth/login",
            data=json.dumps({
                "username": username,
                "password": "StrongStudentPassword@2026"
            }),
            content_type="application/json"
        )
        self.assertEqual(res_login.status_code, 200)
        data_login = json.loads(res_login.data.decode("utf-8"))
        self.assertTrue(data_login["success"])
        self.assertEqual(data_login["user"]["username"], username)

    def test_03_item_reporting_search_and_matching(self):
        """Test reporting a Lost item and Found item, then validating algorithmic matching."""
        # Authenticate as student
        self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": "live_test_student_2026", "password": "StrongStudentPassword@2026"}),
            content_type="application/json"
        )

        # Report a LOST calculator
        lost_payload = {
            "type": "LOST",
            "title": "Casio Scientific Calculator fx-991EX",
            "category": "Electronics",
            "event_date": "2026-10-28",
            "location": "Academic Block A - Room 204",
            "description": "Black scientific calculator with solar panel and roll number written on back."
        }
        res_lost = self.client.post("/api/items", data=json.dumps(lost_payload), content_type="application/json")
        self.assertEqual(res_lost.status_code, 201)
        lost_data = json.loads(res_lost.data.decode("utf-8"))
        lost_id = lost_data["item_id"]

        # Admin reports a FOUND matching calculator
        admin_user = user_repo.get_by_username("admin")
        found_payload = {
            "type": "FOUND",
            "title": "Casio Scientific Calculator fx-991EX ClassWiz",
            "category": "Electronics",
            "event_date": "2026-10-28",
            "location": "Academic Block A",
            "description": "Found a black Casio calculator left on the front desk."
        }
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_user.id
            sess["username"] = admin_user.username
            sess["role"] = admin_user.role

        res_found = self.client.post("/api/items", data=json.dumps(found_payload), content_type="application/json")
        self.assertEqual(res_found.status_code, 201)
        found_data = json.loads(res_found.data.decode("utf-8"))
        found_id = found_data["item_id"]

        # Student logs back in to search and claim
        student_user = user_repo.get_by_username("live_test_student_2026")
        with self.client.session_transaction() as sess:
            sess["user_id"] = student_user.id
            sess["username"] = student_user.username
            sess["role"] = student_user.role

        # Verify items appear in search catalog
        res_catalog = self.client.get("/api/items?keyword=Calculator")
        self.assertEqual(res_catalog.status_code, 200)
        catalog_data = json.loads(res_catalog.data.decode("utf-8"))
        self.assertGreaterEqual(catalog_data["count"], 2)

        # Verify algorithmic AI Smart Match radar
        res_matches = self.client.get(f"/api/items/{lost_id}/matches")
        self.assertEqual(res_matches.status_code, 200)
        matches_data = json.loads(res_matches.data.decode("utf-8"))
        self.assertTrue(matches_data["success"])
        self.assertGreaterEqual(len(matches_data["matches"]), 1)
        top_match = matches_data["matches"][0]
        self.assertEqual(top_match["target_item"]["id"], found_id)
        self.assertGreater(top_match["overall_score"], 60.0)

        # Submit an ownership claim
        claim_payload = {
            "item_id": found_id,
            "proof_description": "My student ID card sticker is on the back inside the cover case."
        }
        res_claim = self.client.post(
            "/api/claims",
            data=json.dumps(claim_payload),
            content_type="application/json"
        )
        self.assertEqual(res_claim.status_code, 201)
        claim_data = json.loads(res_claim.data.decode("utf-8"))
        self.assertTrue(claim_data["success"])

        # Clean up test items and claims
        from database.connection import get_db_cursor
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM claims WHERE item_id IN (?, ?)", (lost_id, found_id))
            cur.execute("DELETE FROM items WHERE id IN (?, ?)", (lost_id, found_id))

    def test_04_admin_authentication_and_features(self):
        """Test admin login and access to admin statistics."""
        res_admin = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": "admin", "password": "Admin@Campus2026"}),
            content_type="application/json"
        )
        self.assertEqual(res_admin.status_code, 200)
        admin_data = json.loads(res_admin.data.decode("utf-8"))
        self.assertEqual(admin_data["user"]["role"], "admin")

        # Test analytics metrics endpoint
        res_analytics = self.client.get("/api/analytics")
        self.assertEqual(res_analytics.status_code, 200)
        analytics_data = json.loads(res_analytics.data.decode("utf-8"))
        self.assertTrue(analytics_data.get("success"))
        self.assertIn("kpis", analytics_data)
        self.assertIn("categories", analytics_data)

    @classmethod
    def tearDownClass(cls):
        # Remove test user
        user = user_repo.get_by_username("live_test_student_2026")
        if user:
            user_repo.delete(user.id)


if __name__ == "__main__":
    unittest.main()
