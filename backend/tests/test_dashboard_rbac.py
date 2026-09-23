from tests.conftest import auth_headers, create_user_with_role, register_org


def test_admin_can_view_portfolio_dashboard(client):
    admin_token = register_org(client)
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers(admin_token))
    assert response.status_code == 200


def test_role_without_analytics_dashboard_permission_is_forbidden(client):
    admin_token = register_org(client)
    # iam-admin: user/role/group management only, no analytics.dashboard
    member_token = create_user_with_role(
        client, admin_token, role_name="iam-admin", email="noanalytics@example.com",
    )
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers(member_token))
    assert response.status_code == 403


def test_auditor_can_view_analytics_endpoints(client):
    admin_token = register_org(client)
    auditor_token = create_user_with_role(
        client, admin_token, role_name="auditor", email="auditor@example.com",
    )
    summary_response = client.get("/api/v1/dashboard/summary", headers=auth_headers(auditor_token))
    assert summary_response.status_code == 200

    analytics_response = client.get("/api/v1/dashboard/analytics", headers=auth_headers(auditor_token))
    assert analytics_response.status_code == 200

    vulnerabilities_response = client.get(
        "/api/v1/dashboard/vulnerabilities", headers=auth_headers(auditor_token),
    )
    assert vulnerabilities_response.status_code == 200
