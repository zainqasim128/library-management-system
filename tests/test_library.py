import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Helper functions
def register_user(username, password, role):
    return client.post("/role/register", json={
        "username": username,
        "password": password,
        "role": role
    })

def login_user(username, password):
    res = client.post("/role/login", json={
        "username": username,
        "password": password
    })
    return res.json()["access_token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def setup_users_and_books():
    # Register users
    register_user("admin", "adminpass", "admin")
    register_user("staff", "staffpass", "staff")
    register_user("user", "userpass", "user")
    # Login
    admin_token = login_user("admin", "adminpass")
    staff_token = login_user("staff", "staffpass")
    user_token = login_user("user", "userpass")
    # Create authors and books as admin
    client.post("/authors/", json={"id": 1, "name": "Author1", "bio": "Bio"}, headers=auth_headers(admin_token))
    for i in range(1, 5):
        client.post("/books/", json={
            "id": i,
            "title": f"Book{i}",
            "isbn": f"1234567890{i:03d}",
            "author_id": 1,
            "published_date": "2020-01-01",
            "available": True,
            "last_borrowed_date": None
        }, headers=auth_headers(admin_token))
    return {"admin": admin_token, "staff": staff_token, "user": user_token}

def test_borrow_limit(setup_users_and_books):
    user_token = setup_users_and_books["user"]
    # Borrow 3 books
    for i in range(1, 4):
        r = client.post(f"/borrow/{i}", headers=auth_headers(user_token))
        assert r.status_code == 200
    # Try to borrow a 4th book
    r = client.post("/borrow/4", headers=auth_headers(user_token))
    assert r.status_code == 400
    assert "cannot borrow more than 3 books" in r.text

def test_permission_restrictions(setup_users_and_books):
    user_token = setup_users_and_books["user"]
    staff_token = setup_users_and_books["staff"]
    # User cannot create author
    r = client.post("/authors/", json={"id": 2, "name": "A2", "bio": "B"}, headers=auth_headers(user_token))
    assert r.status_code == 403
    # Staff can create author
    r = client.post("/authors/", json={"id": 2, "name": "A2", "bio": "B"}, headers=auth_headers(staff_token))
    assert r.status_code == 201
    # User cannot delete book
    r = client.delete("/books/1", headers=auth_headers(user_token))
    assert r.status_code == 403

def test_borrow_return_workflow(setup_users_and_books):
    user_token = setup_users_and_books["user"]
    # Borrow book 4 (should fail, already at limit)
    r = client.post("/borrow/4", headers=auth_headers(user_token))
    assert r.status_code == 400
    # Return book 1
    r = client.post("/return/1", headers=auth_headers(user_token))
    assert r.status_code == 200
    # Now borrow book 4 (should succeed)
    r = client.post("/borrow/4", headers=auth_headers(user_token))
    assert r.status_code == 200
    # Return all books
    for i in [2, 3, 4]:
        r = client.post(f"/return/{i}", headers=auth_headers(user_token))
        assert r.status_code == 200 