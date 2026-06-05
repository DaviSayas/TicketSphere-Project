"""Authentication and RBAC tests."""


def test_login_success(client):
    r = client.post("/auth/login", json={"email": "admin@empresa.pt", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["role"] == "admin"


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"email": "admin@empresa.pt", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", json={"email": "nobody@empresa.pt", "password": "x"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(admin_client):
    r = admin_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "admin@empresa.pt"


def test_tech_cannot_access_admin_users(tech_client):
    """RBAC: técnico a tentar listar utilizadores deve receber 403."""
    r = tech_client.get("/users")
    assert r.status_code == 403


def test_user_cannot_access_admin_users(user_client):
    r = user_client.get("/users")
    assert r.status_code == 403


def test_admin_can_list_users(admin_client):
    r = admin_client.get("/users")
    assert r.status_code == 200
    assert len(r.json()) >= 5


def test_admin_can_create_user(admin_client):
    r = admin_client.post(
        "/users",
        json={"name": "Novo", "email": "novo@empresa.pt", "password": "novopass", "role": "user"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "novo@empresa.pt"


def test_duplicate_email_rejected(admin_client):
    r = admin_client.post(
        "/users",
        json={"name": "X", "email": "admin@empresa.pt", "password": "x", "role": "user"},
    )
    assert r.status_code in (400, 422)
