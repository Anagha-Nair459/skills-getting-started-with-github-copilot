"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    # Store original state
    from app import activities
    original_state = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    activities.clear()
    for name, activity in original_state.items():
        activities[name] = activity


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_includes_chess_club(self, client):
        """Test that Chess Club is in the activities"""
        response = client.get("/activities")
        data = response.json()
        assert "Chess Club" in data


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_valid_activity(self, client, reset_activities):
        """Test signing up for a valid activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        client.post(
            "/activities/Basketball/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        response = client.get("/activities")
        activities = response.json()
        assert "newstudent@mergington.edu" in activities["Basketball"]["participants"]
    
    def test_signup_for_nonexistent_activity_returns_404(self, client, reset_activities):
        """Test that signing up for a nonexistent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_duplicate_returns_400(self, client, reset_activities):
        """Test that signing up twice returns 400"""
        signup_response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert signup_response.status_code == 200
        
        # Try to sign up again
        duplicate_response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert duplicate_response.status_code == 400
        assert "already signed up" in duplicate_response.json()["detail"].lower()
    
    def test_signup_preserves_existing_participants(self, client, reset_activities):
        """Test that signup doesn't remove existing participants"""
        response = client.get("/activities")
        original_participants = response.json()["Chess Club"]["participants"].copy()
        
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "newparticipant@mergington.edu"}
        )
        
        response = client.get("/activities")
        new_participants = response.json()["Chess Club"]["participants"]
        
        # Check all original participants are still there
        for participant in original_participants:
            assert participant in new_participants


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_from_valid_activity(self, client, reset_activities):
        """Test unregistering from a valid activity"""
        # First sign up
        client.post(
            "/activities/Art Club/signup",
            params={"email": "testuser@mergington.edu"}
        )
        
        # Then unregister
        response = client.post(
            "/activities/Art Club/unregister",
            params={"email": "testuser@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "removetest@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        
        # Unregister
        client.post(
            "/activities/Debate Team/unregister",
            params={"email": email}
        )
        
        # Check participant is removed
        response = client.get("/activities")
        participants = response.json()["Debate Team"]["participants"]
        assert email not in participants
    
    def test_unregister_from_nonexistent_activity_returns_404(self, client, reset_activities):
        """Test that unregistering from a nonexistent activity returns 404"""
        response = client.post(
            "/activities/Fake Club/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
    
    def test_unregister_not_signed_up_returns_400(self, client, reset_activities):
        """Test that unregistering when not signed up returns 400"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "notexist@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_unregister_preserves_other_participants(self, client, reset_activities):
        """Test that unregistering doesn't affect other participants"""
        email_to_remove = "remove@mergington.edu"
        
        # Add a new participant
        client.post(
            "/activities/Science Club/signup",
            params={"email": email_to_remove}
        )
        
        # Get original participants
        response = client.get("/activities")
        original_participants = response.json()["Science Club"]["participants"].copy()
        
        # Unregister
        client.post(
            "/activities/Science Club/unregister",
            params={"email": email_to_remove}
        )
        
        # Check other participants are still there
        response = client.get("/activities")
        remaining_participants = response.json()["Science Club"]["participants"]
        
        for participant in original_participants:
            if participant != email_to_remove:
                assert participant in remaining_participants


class TestRootRedirect:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code in [301, 302, 307, 308]
        assert "static/index.html" in response.headers.get("location", "")


class TestIntegration:
    """Integration tests combining multiple endpoints"""
    
    def test_signup_and_unregister_workflow(self, client, reset_activities):
        """Test a complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify participant added
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        
        # Verify participant removed
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
        assert email not in response.json()[activity]["participants"]
