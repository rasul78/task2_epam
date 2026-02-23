"""
Unit tests for the Task Manager API.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import db


@pytest.fixture(autouse=True)
def clear_db():
    """Reset the database before each test to ensure isolation."""
    db.clear()
    yield
    db.clear()


client = TestClient(app)


# ─── Health check ────────────────────────────────────────────────────────────

def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Task Manager API is running"


# ─── Create task ─────────────────────────────────────────────────────────────

def test_create_task_success():
    payload = {"title": "Write tests", "status": "todo", "priority": 2}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Write tests"
    assert data["status"] == "todo"
    assert data["priority"] == 2
    assert "id" in data
    assert "created_at" in data


def test_create_task_default_status():
    response = client.post("/tasks", json={"title": "Default task"})
    assert response.status_code == 201
    assert response.json()["status"] == "todo"


def test_create_task_missing_title_returns_422():
    response = client.post("/tasks", json={"status": "todo"})
    assert response.status_code == 422


def test_create_task_empty_title_returns_422():
    response = client.post("/tasks", json={"title": ""})
    assert response.status_code == 422


def test_create_task_priority_out_of_range_returns_422():
    response = client.post("/tasks", json={"title": "Bad priority", "priority": 10})
    assert response.status_code == 422


# ─── Get tasks ───────────────────────────────────────────────────────────────

def test_get_all_tasks_empty():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_tasks_returns_created_tasks():
    client.post("/tasks", json={"title": "Task 1"})
    client.post("/tasks", json={"title": "Task 2"})
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_task_by_id_success():
    create_resp = client.post("/tasks", json={"title": "Find me"})
    task_id = create_resp.json()["id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Find me"


def test_get_task_by_id_not_found():
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ─── Update task ─────────────────────────────────────────────────────────────

def test_update_task_success():
    task_id = client.post("/tasks", json={"title": "Old title"}).json()["id"]
    response = client.put(f"/tasks/{task_id}", json={"title": "New title", "status": "done"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert data["status"] == "done"


def test_update_task_partial():
    task_id = client.post("/tasks", json={"title": "Original", "priority": 1}).json()["id"]
    response = client.put(f"/tasks/{task_id}", json={"priority": 5})
    assert response.status_code == 200
    assert response.json()["priority"] == 5
    assert response.json()["title"] == "Original"


def test_update_task_not_found():
    response = client.put("/tasks/999", json={"title": "Ghost"})
    assert response.status_code == 404


# ─── Delete task ─────────────────────────────────────────────────────────────

def test_delete_task_success():
    task_id = client.post("/tasks", json={"title": "Delete me"}).json()["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_task_not_found():
    response = client.delete("/tasks/999")
    assert response.status_code == 404


def test_deleted_task_no_longer_accessible():
    task_id = client.post("/tasks", json={"title": "Gone soon"}).json()["id"]
    client.delete(f"/tasks/{task_id}")
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404


# ─── Filter by status ────────────────────────────────────────────────────────

def test_get_tasks_by_status_success():
    client.post("/tasks", json={"title": "A", "status": "todo"})
    client.post("/tasks", json={"title": "B", "status": "done"})
    client.post("/tasks", json={"title": "C", "status": "todo"})
    response = client.get("/tasks/status/todo")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert all(t["status"] == "todo" for t in tasks)


def test_get_tasks_by_invalid_status():
    response = client.get("/tasks/status/invalid_status")
    assert response.status_code == 400