"""Ticket workflow and state-machine tests."""


def test_user_can_create_ticket(user_client):
    r = user_client.post(
        "/tickets",
        json={"title": "Teste novo", "description": "desc", "priority": "medium", "category_id": 1},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "open"
    assert body["title"] == "Teste novo"


def test_user_sees_only_own_tickets(user_client):
    r = user_client.get("/tickets")
    assert r.status_code == 200
    items = r.json()["items"]
    creator_ids = {t["creator_id"] for t in items}
    assert len(creator_ids) <= 1  # só o próprio


def test_admin_sees_all_tickets(admin_client):
    r = admin_client.get("/tickets")
    assert r.status_code == 200
    assert r.json()["total"] >= 10  # seed creates 10


def test_filter_by_status(admin_client):
    r = admin_client.get("/tickets", params={"status": "open"})
    assert r.status_code == 200
    for t in r.json()["items"]:
        assert t["status"] == "open"


def test_filter_by_priority(admin_client):
    r = admin_client.get("/tickets", params={"priority": "urgent"})
    assert r.status_code == 200
    for t in r.json()["items"]:
        assert t["priority"] == "urgent"


def test_text_search(admin_client):
    r = admin_client.get("/tickets", params={"q": "monitor"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any("monitor" in t["title"].lower() for t in items)


def test_get_ticket_detail(admin_client):
    r = admin_client.get("/tickets/1")
    assert r.status_code == 200
    detail = r.json()
    assert "comments" in detail
    assert "history" in detail
    assert detail["history"]  # seed adds history rows


def test_user_cannot_view_others_ticket(user_client, admin_client):
    """Cria ticket como admin, tenta ver como user → 403."""
    r = admin_client.post(
        "/tickets",
        json={"title": "Admin only", "description": "", "priority": "low", "category_id": 5},
    )
    ticket_id = r.json()["id"]
    r2 = user_client.get(f"/tickets/{ticket_id}")
    assert r2.status_code == 403


def test_valid_status_transition(admin_client):
    """open → in_progress é válido."""
    r = admin_client.get("/tickets", params={"status": "open", "page_size": 1})
    tid = r.json()["items"][0]["id"]
    r2 = admin_client.put(f"/tickets/{tid}/status", json={"status": "in_progress"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "in_progress"


def test_invalid_status_transition_returns_400(admin_client):
    """closed → open é inválido (closed é terminal)."""
    # Primeiro fechamos um ticket
    r = admin_client.get("/tickets", params={"status": "open", "page_size": 1})
    tid = r.json()["items"][0]["id"]
    admin_client.put(f"/tickets/{tid}/status", json={"status": "resolved"})
    admin_client.put(f"/tickets/{tid}/status", json={"status": "closed"})
    # Tentar reabrir um ticket closed → 400
    r2 = admin_client.put(f"/tickets/{tid}/status", json={"status": "open"})
    assert r2.status_code == 400
    assert "inválida" in r2.json()["detail"].lower()


def test_skip_state_is_rejected(admin_client):
    """open → closed não é uma transição directa válida no nosso fluxo?
    No nosso state machine open→closed É válido (terminal direct), mas open→awaiting NÃO é.
    """
    r = admin_client.get("/tickets", params={"status": "open", "page_size": 1})
    tid = r.json()["items"][0]["id"]
    r2 = admin_client.put(f"/tickets/{tid}/status", json={"status": "awaiting"})
    assert r2.status_code == 400


def test_assign_ticket(admin_client):
    # Find an unassigned open ticket
    r = admin_client.get("/tickets", params={"status": "open"})
    target = next((t for t in r.json()["items"] if t["assignee_id"] is None), None)
    assert target is not None, "Seed should leave at least one unassigned ticket"
    r2 = admin_client.put(f"/tickets/{target['id']}/assign", json={"assignee_id": 2})
    assert r2.status_code == 200
    assert r2.json()["assignee_id"] == 2


def test_assign_invalid_user_rejected(admin_client):
    r = admin_client.get("/tickets", params={"page_size": 1})
    tid = r.json()["items"][0]["id"]
    # User 4 is a regular user, not a tech
    r2 = admin_client.put(f"/tickets/{tid}/assign", json={"assignee_id": 4})
    assert r2.status_code == 400


def test_add_comment(user_client):
    r = user_client.get("/tickets")
    tid = r.json()["items"][0]["id"]
    r2 = user_client.post(
        f"/tickets/{tid}/comments",
        json={"body": "Adicionar info", "is_internal": False},
    )
    assert r2.status_code == 201
    assert r2.json()["body"] == "Adicionar info"


def test_user_cannot_post_internal_comment(user_client):
    """is_internal=True passado por um user comum é silenciosamente forçado a False."""
    r = user_client.get("/tickets")
    tid = r.json()["items"][0]["id"]
    r2 = user_client.post(
        f"/tickets/{tid}/comments",
        json={"body": "tentativa", "is_internal": True},
    )
    assert r2.status_code == 201
    assert r2.json()["is_internal"] is False
