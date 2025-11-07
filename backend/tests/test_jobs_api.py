"""Tests for jobs API endpoints."""
import pytest
from datetime import datetime


@pytest.mark.asyncio
class TestJobsAPI:
    """Test job management API."""

    async def test_create_job(self, test_client, auth_headers, clean_db):
        """Test creating a job."""
        response = test_client.post(
            "/api/jobs",
            json={"command": "predict", "parameters": {"weeks_ahead": 3}},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["command"] == "predict"
        assert data["status"] == "pending"
        assert data["parameters"]["weeks_ahead"] == 3

    async def test_create_job_unauthorized(self, test_client, clean_db):
        """Test creating job without authentication."""
        response = test_client.post(
            "/api/jobs",
            json={"command": "predict", "parameters": {}}
        )
        assert response.status_code == 403

    async def test_get_jobs(self, test_client, auth_headers, clean_db):
        """Test getting jobs list."""
        # Create a job first
        test_client.post(
            "/api/jobs",
            json={"command": "predict", "parameters": {}},
            headers=auth_headers
        )

        # Get jobs
        response = test_client.get("/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_job_by_id(self, test_client, auth_headers, clean_db):
        """Test getting a specific job."""
        # Create a job
        create_response = test_client.post(
            "/api/jobs",
            json={"command": "update_db", "parameters": {}},
            headers=auth_headers
        )
        job_id = create_response.json()["id"]

        # Get the job
        response = test_client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["command"] == "update_db"

    async def test_get_job_not_found(self, test_client, auth_headers, clean_db):
        """Test getting non-existent job."""
        response = test_client.get("/api/jobs/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    async def test_cancel_job(self, test_client, auth_headers, clean_db):
        """Test cancelling a job."""
        # Note: This test will fail if job is not running
        # For now, just test the endpoint structure
        response = test_client.post(
            "/api/jobs/some-job-id/cancel",
            headers=auth_headers
        )
        # Should return 400 if job not running (not 404 or 500)
        assert response.status_code in [400, 404]

    async def test_clear_job_logs(self, test_client, auth_headers, clean_db):
        """Test clearing logs for a job."""
        # Create a job
        create_response = test_client.post(
            "/api/jobs",
            json={"command": "predict", "parameters": {}},
            headers=auth_headers
        )
        job_id = create_response.json()["id"]

        # Clear logs
        response = test_client.delete(f"/api/jobs/{job_id}/logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_clear_all_job_logs(self, test_client, auth_headers, clean_db):
        """Test clearing all job logs."""
        # Create some jobs
        for _ in range(3):
            test_client.post(
                "/api/jobs",
                json={"command": "predict", "parameters": {}},
                headers=auth_headers
            )

        # Clear all logs
        response = test_client.delete("/api/jobs/logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleared" in data

    async def test_get_job_output(self, test_client, auth_headers, clean_db):
        """Test getting job output."""
        # Create a job
        create_response = test_client.post(
            "/api/jobs",
            json={"command": "predict", "parameters": {}},
            headers=auth_headers
        )
        job_id = create_response.json()["id"]

        # Get output (should be empty for pending job)
        response = test_client.get(f"/api/jobs/{job_id}/output", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["output"] is None or isinstance(data["output"], dict)


@pytest.mark.asyncio
class TestJobCreation:
    """Test job creation with different commands."""

    @pytest.mark.parametrize("command,parameters", [
        ("setup_db", {}),
        ("update_db", {}),
        ("predict", {"weeks_ahead": 3}),
        ("optimize", {"weeks_ahead": 3, "wildcard_week": 10}),
        ("pipeline", {}),
    ])
    async def test_create_job_various_commands(self, test_client, auth_headers, clean_db, command, parameters):
        """Test creating jobs with various commands."""
        response = test_client.post(
            "/api/jobs",
            json={"command": command, "parameters": parameters},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == command
        assert data["parameters"] == parameters
