"""Dashboard and report tests."""


def test_dashboard_admin_only(user_client):
    r = user_client.get("/admin/dashboard")
    assert r.status_code == 403


def test_dashboard_returns_metrics(admin_client):
    r = admin_client.get("/admin/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "cards" in data
    assert "daily_series" in data
    assert "top_techs" in data
    assert "category_distribution" in data
    assert len(data["daily_series"]) == 30


def test_monthly_report_csv(admin_client):
    r = admin_client.get("/admin/reports/monthly")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    csv_body = r.text
    assert "id,titulo" in csv_body  # header row


def test_monthly_report_specific_month(admin_client):
    r = admin_client.get("/admin/reports/monthly?month=2025-01")
    assert r.status_code == 200


def test_monthly_report_invalid_month_format(admin_client):
    r = admin_client.get("/admin/reports/monthly?month=invalid")
    assert r.status_code == 422
