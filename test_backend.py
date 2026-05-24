import os
import json
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment to test database if needed (main.py uses SQLite ./kulkas_pintar.db by default)
# For the unit tests, we'll import and run directly against the app
from backend.main import app, SECRET_KEY, ALGORITHM
from backend.database import Base, get_db

client = TestClient(app)

class TestKulkasPintarAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure database tables are created
        from backend.database import engine
        from backend.models import Base
        Base.metadata.create_all(bind=engine)

        # Create user accounts for testing
        cls.test_email_1 = "chef1@example.com"
        cls.test_password_1 = "SecurePassword123!"
        cls.test_email_2 = "chef2@example.com"
        cls.test_password_2 = "CookingIsFun456!"
        cls.token_1 = None
        cls.token_2 = None

    def test_01_user_registration_and_login(self):
        # 1. Register user 1
        resp = client.post("/api/v1/auth/register", json={
            "email": self.test_email_1,
            "password": self.test_password_1
        })
        # If user already exists (e.g. from previous manual runs), we might get 400. That's fine.
        if resp.status_code == 400:
            print("User 1 already registered, skipping registration check.")
        else:
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["email"], self.test_email_1)
            self.assertEqual(data["dietary_restrictions"], [])

        # Register user 2
        resp = client.post("/api/v1/auth/register", json={
            "email": self.test_email_2,
            "password": self.test_password_2
        })
        if resp.status_code == 400:
            print("User 2 already registered, skipping registration check.")
        else:
            self.assertEqual(resp.status_code, 200)

        # 2. Login user 1
        resp = client.post("/api/v1/auth/login", json={
            "email": self.test_email_1,
            "password": self.test_password_1
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        TestKulkasPintarAPI.token_1 = data["access_token"]

        # Login user 2
        resp = client.post("/api/v1/auth/login", json={
            "email": self.test_email_2,
            "password": self.test_password_2
        })
        self.assertEqual(resp.status_code, 200)
        TestKulkasPintarAPI.token_2 = resp.json()["access_token"]

        # 3. Get profile details
        resp = client.get(f"/api/v1/auth/me?token={self.token_1}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], self.test_email_1)

    def test_02_update_dietary_restrictions(self):
        # Update user 1 profile
        new_restrictions = ["Vegetarian", "Gluten-Free"]
        resp = client.put(
            f"/api/v1/auth/profile?token={self.token_1}",
            json={"dietary_restrictions": new_restrictions}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["dietary_restrictions"], new_restrictions)

        # Verify profile was updated in next fetch
        resp = client.get(f"/api/v1/auth/me?token={self.token_1}")
        self.assertEqual(resp.json()["dietary_restrictions"], new_restrictions)

    def test_03_inventory_crud_operations(self):
        # Clear existing items for user 1 (done via deletions if any exist, or we just test creating)
        # Create an item
        item_data = {
            "name": "Organic Milk",
            "quantity": 2.0,
            "unit": "cartons",
            "category": "Dairy/Eggs",
            "expires_at": "2026-06-01T00:00:00"
        }
        resp = client.post(f"/api/v1/inventory?token={self.token_1}", json=item_data)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "Organic Milk")
        self.assertEqual(data["quantity"], 2.0)
        self.assertEqual(data["unit"], "cartons")
        item_id = data["id"]

        # Read inventory items
        resp = client.get(f"/api/v1/inventory?token={self.token_1}")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertTrue(any(item["id"] == item_id for item in items))

        # Update item
        resp = client.put(
            f"/api/v1/inventory/{item_id}?token={self.token_1}",
            json={"quantity": 3.5, "unit": "liters"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["quantity"], 3.5)
        self.assertEqual(resp.json()["unit"], "liters")

        # Delete item
        resp = client.delete(f"/api/v1/inventory/{item_id}?token={self.token_1}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["message"], "Item deleted successfully")

        # Verify deletion
        resp = client.get(f"/api/v1/inventory?token={self.token_1}")
        items = resp.json()
        self.assertFalse(any(item["id"] == item_id for item in items))

    def test_04_collaborative_rooms_and_merging(self):
        # 1. Leave any active rooms first
        client.post(f"/api/v1/rooms/leave?token={self.token_1}")
        client.post(f"/api/v1/rooms/leave?token={self.token_2}")

        # 2. Add inventory item for user 1
        resp = client.post(f"/api/v1/inventory?token={self.token_1}", json={
            "name": "Cheddar Cheese",
            "quantity": 1.0,
            "unit": "block",
            "category": "Dairy/Eggs"
        })
        self.assertEqual(resp.status_code, 200)
        cheese_id = resp.json()["id"]

        # Add inventory item for user 2
        resp = client.post(f"/api/v1/inventory?token={self.token_2}", json={
            "name": "Tomatoes",
            "quantity": 5.0,
            "unit": "pcs",
            "category": "Vegetables"
        })
        self.assertEqual(resp.status_code, 200)
        tomatoes_id = resp.json()["id"]

        # 3. Check separate inventories
        resp = client.get(f"/api/v1/inventory?token={self.token_1}")
        self.assertTrue(any(item["name"] == "Cheddar Cheese" for item in resp.json()))
        self.assertFalse(any(item["name"] == "Tomatoes" for item in resp.json()))

        # 4. Both join Room "kitchen123"
        resp = client.post(f"/api/v1/rooms/join?token={self.token_1}", json={"room_id": "kitchen123"})
        self.assertEqual(resp.status_code, 200)
        
        resp = client.post(f"/api/v1/rooms/join?token={self.token_2}", json={"room_id": "kitchen123"})
        self.assertEqual(resp.status_code, 200)

        # 5. Check merged inventory (user 1 should now see tomatoes, and user 2 should see cheddar cheese!)
        resp = client.get(f"/api/v1/inventory?token={self.token_1}")
        items_user_1 = resp.json()
        self.assertTrue(any(item["name"] == "Cheddar Cheese" for item in items_user_1))
        self.assertTrue(any(item["name"] == "Tomatoes" for item in items_user_1))

        # Check room details
        resp = client.get(f"/api/v1/rooms/active?token={self.token_1}")
        self.assertEqual(resp.status_code, 200)
        room_data = resp.json()
        self.assertTrue(room_data["in_room"])
        self.assertEqual(room_data["room_id"], "kitchen123")
        self.assertEqual(len(room_data["members"]), 2)

        # 6. Leave Room
        client.post(f"/api/v1/rooms/leave?token={self.token_1}")
        
        # Verify inventories are split again
        resp = client.get(f"/api/v1/inventory?token={self.token_1}")
        self.assertFalse(any(item["name"] == "Tomatoes" for item in resp.json()))

        # Clean up inventory items
        client.delete(f"/api/v1/inventory/{cheese_id}?token={self.token_1}")
        client.delete(f"/api/v1/inventory/{tomatoes_id}?token={self.token_2}")

    def test_05_multimodal_mock_analysis_fallback(self):
        # Temporarily remove GEMINI_API_KEY from environment to force Mock Mode
        old_api_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        
        try:
            # We upload a dummy file to test multimodal analyzer fallback
            dummy_file_content = b"fake-image-bytes-content-structure"
            
            resp = client.post(
                "/api/v1/analyze-fridge",
                data={
                    "token": self.token_1,
                    "strict_match": False,
                    "save_the_food": False
                },
                files={"image": ("fridge.jpg", dummy_file_content, "image/jpeg")}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("ingredients", data)
            self.assertIn("recipes", data)
            self.assertTrue(len(data["ingredients"]) > 0)
            self.assertEqual(len(data["recipes"]), 3)
        finally:
            # Restore key
            if old_api_key is not None:
                os.environ["GEMINI_API_KEY"] = old_api_key

    def test_06_multimodal_api_failure_handling(self):
        # Set an invalid or dummy API key
        old_api_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "some-invalid-key"
        
        try:
            # We upload a dummy file
            dummy_file_content = b"fake-image-bytes-content-structure"
            
            resp = client.post(
                "/api/v1/analyze-fridge",
                data={
                    "token": self.token_1,
                    "strict_match": False,
                    "save_the_food": False
                },
                files={"image": ("fridge.jpg", dummy_file_content, "image/jpeg")}
            )
            # It should fail and return 502 Bad Gateway
            self.assertEqual(resp.status_code, 502)
            self.assertIn("detail", resp.json())
            self.assertTrue(
                "Gemini API Error" in resp.json()["detail"] or 
                "Failed to initialize Gemini Client" in resp.json()["detail"]
            )
        finally:
            if old_api_key is not None:
                os.environ["GEMINI_API_KEY"] = old_api_key
            else:
                if "GEMINI_API_KEY" in os.environ:
                    del os.environ["GEMINI_API_KEY"]


if __name__ == "__main__":
    unittest.main()
