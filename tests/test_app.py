"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        "Basketball": {
            "description": "Team sport focusing on basketball skills and competitive play",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["alex@mergington.edu"]
        },
        "Tennis Club": {
            "description": "Learn tennis techniques and participate in friendly matches",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 10,
            "participants": ["sarah@mergington.edu"]
        },
        "Debate Team": {
            "description": "Develop public speaking and critical thinking skills through debate",
            "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 16,
            "participants": ["james@mergington.edu", "rachel@mergington.edu"]
        },
    }
    
    # Clear and reset activities
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Clean up after test
    activities.clear()
    activities.update(original_activities)


class TestRoot:
    """Test root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Test /activities endpoint"""
    
    def test_get_activities(self, client, reset_activities):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Basketball" in data
        assert "Tennis Club" in data
        assert "Debate Team" in data
    
    def test_activities_have_correct_structure(self, client, reset_activities):
        """Test that activities have the required fields"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Basketball"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)


class TestSignupEndpoint:
    """Test /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup"""
        response = client.post(
            "/activities/Basketball/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        
        # Verify participant was added
        activity_response = client.get("/activities")
        activities_data = activity_response.json()
        assert "newstudent@mergington.edu" in activities_data["Basketball"]["participants"]
    
    def test_signup_duplicate(self, client, reset_activities):
        """Test that duplicate signups are prevented"""
        # First signup
        response1 = client.post(
            "/activities/Basketball/signup?email=duplicate@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Attempt duplicate signup
        response2 = client.post(
            "/activities/Basketball/signup?email=duplicate@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/FakeActivity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_signup_existing_participant(self, client, reset_activities):
        """Test that existing participants cannot signup again"""
        response = client.post(
            "/activities/Basketball/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 400


class TestUnregisterEndpoint:
    """Test /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister"""
        # Verify participant exists
        get_response = client.get("/activities")
        assert "alex@mergington.edu" in get_response.json()["Basketball"]["participants"]
        
        # Unregister
        response = client.delete(
            "/activities/Basketball/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        
        # Verify participant was removed
        get_response = client.get("/activities")
        assert "alex@mergington.edu" not in get_response.json()["Basketball"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/FakeActivity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregistering a student who isn't registered"""
        response = client.delete(
            "/activities/Basketball/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_multiple_participants(self, client, reset_activities):
        """Test that unregistering only removes the correct participant"""
        # Add another participant
        client.post(
            "/activities/Debate Team/signup?email=newdebater@mergington.edu"
        )
        
        # Unregister one
        response = client.delete(
            "/activities/Debate Team/unregister?email=james@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify only the correct participant was removed
        get_response = client.get("/activities")
        participants = get_response.json()["Debate Team"]["participants"]
        assert "james@mergington.edu" not in participants
        assert "rachel@mergington.edu" in participants
        assert "newdebater@mergington.edu" in participants


class TestSignupAndUnregisterFlow:
    """Test complete signup and unregister workflows"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signing up and then unregistering"""
        email = "workflow@mergington.edu"
        activity = "Basketball"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify registered
        get_response = client.get("/activities")
        assert email in get_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        get_response = client.get("/activities")
        assert email not in get_response.json()[activity]["participants"]
    
    def test_signup_after_unregister(self, client, reset_activities):
        """Test that a student can signup again after unregistering"""
        email = "comeback@mergington.edu"
        activity = "Tennis Club"
        
        # Sign up
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Unregister
        client.delete(f"/activities/{activity}/unregister?email={email}")
        
        # Sign up again
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
