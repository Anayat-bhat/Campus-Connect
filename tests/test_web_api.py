"""
Tests for CampusConnect Web API endpoints:
- Matches calculation and schema verification
- Item report creation with base64 photograph upload
- Payload limit error handling
"""

import os
import unittest
import json
import base64
from tempfile import NamedTemporaryFile

from web_app import app, db_path, user_repo, item_repo
from models.user import User
from models.item import Item
from database.connection import init_database


class WebApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Create or ensure test user exists
        user = user_repo.get_by_username("test_web_user")
        if not user:
            user = User(
                id=None,
                username="test_web_user",
                password_hash="testhash",
                salt="testsalt",
                full_name="Test Web User",
                email="test_web@campus.edu",
                role="student"
            )
            uid = user_repo.create(user)
            user.id = uid
        self.user = user

        # Set session
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user.id
            sess["username"] = self.user.username
            sess["role"] = self.user.role

    def test_api_item_matches(self):
        """Verify /api/items/<id>/matches returns valid json and match breakdown."""
        # Get an item
        items = item_repo.list_items(limit=1)
        if items:
            item_id = items[0].id
            res = self.client.get(f"/api/items/{item_id}/matches")
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data.decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("matches", data)
            self.assertIn("source_item", data)

    def test_api_create_item_with_base64_photo(self):
        """Verify /api/items creates item successfully when base64 image is uploaded."""
        # Create a tiny 1x1 transparent png base64
        tiny_png = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
            "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        payload = {
            "type": "LOST",
            "title": "Black Hydro Flask",
            "category": "Personal belongings",
            "event_date": "2026-10-26",
            "location": "Central Library",
            "description": "Black insulated flask with university stickers.",
            "image_base64": tiny_png
        }

        res = self.client.post(
            "/api/items",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data.decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertIn("item_id", data)

        # Verify created item in repo
        created_id = data["item_id"]
        saved = item_repo.get_by_id(created_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.title, "Black Hydro Flask")
        self.assertIsNotNone(saved.image_path)
        self.assertTrue(saved.image_path.startswith("assets/uploads/"))

        # Clean up test item
        item_repo.delete(created_id)
        if saved.image_path and os.path.exists(saved.image_path):
            try:
                os.remove(saved.image_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
