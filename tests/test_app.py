"""
Tests for the Mergington High School Activities API
"""

import sys
import uuid
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src directory to path to import app module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import app as app_module


@pytest.fixture
def client():
    """Create a test client and reload the `app` module to reset state before each test."""
    importlib.reload(app_module)
    return TestClient(app_module.app)


class TestRoot:
    """Tests for root endpoint"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for get_activities endpoint"""

    def test_get_activities_returns_dict(self, client):
        """Test that activities endpoint returns a dictionary"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_activities_contains_chess_club(self, client):
        """Test that activities list contains Chess Club"""
        response = client.get("/activities")
        data = response.json()
        assert "Chess Club" in data

    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)

    def test_get_activities_includes_participants(self, client):
        """Test that activities include participant information"""
        response = client.get("/activities")
        data = response.json()

        # Check that at least one activity has participants
        has_participants = any(a["participants"] for a in data.values())
        assert has_participants


class TestSignup:
    """Tests for signup endpoint"""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant"""
        email = f"test_{uuid.uuid4()}@mergington.edu"
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]

    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signups return error"""
        email = f"duplicate_{uuid.uuid4()}@mergington.edu"

        # First signup should succeed
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response1.status_code == 200

        # Second signup with same email should fail
        response2 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            f"/activities/Nonexistent Club/signup?email=test_{uuid.uuid4()}@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_full_activity(self, client):
        """Test signup when activity is at capacity"""
        # Get an activity and check its capacity
        activities_response = client.get("/activities")
        activities = activities_response.json()

        # Generate unique test ID to avoid conflicts
        test_id = str(uuid.uuid4())[:8]

        # Find an activity and fill it up
        for activity_name, details in activities.items():
            if len(details["participants"]) < details["max_participants"]:
                # Try to fill it up (generate a few more than capacity)
                remaining = details["max_participants"] - len(details["participants"])
                emails = [f"fill{test_id}_{i}@mergington.edu" for i in range(remaining + 5)]

                for i, email in enumerate(emails):
                    response = client.post(
                        f"/activities/{activity_name}/signup?email={email}"
                    )

                    if i < remaining:
                        # Should succeed until remaining slots are filled
                        assert response.status_code == 200
                    else:
                        # Should fail when full
                        assert response.status_code == 400
                        assert "full" in response.json()["detail"].lower()
                break


class TestUnregister:
    """Tests for unregister endpoint"""

    def test_unregister_participant(self, client):
        """Test unregistering a participant"""
        email = f"unregister_{uuid.uuid4()}@mergington.edu"

        # First signup
        response1 = client.post(
            f"/activities/Programming Class/signup?email={email}"
        )
        assert response1.status_code == 200

        # Then unregister
        response2 = client.delete(
            f"/activities/Programming Class/unregister?email={email}"
        )
        assert response2.status_code == 200
        data = response2.json()
        assert "message" in data
        assert email in data["message"]

    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering someone not signed up"""
        response = client.delete(
            f"/activities/Chess Club/unregister?email=notexist_{uuid.uuid4()}@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister for non-existent activity"""
        response = client.delete(
            f"/activities/Nonexistent Club/unregister?email=test_{uuid.uuid4()}@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
