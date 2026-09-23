from app.services.role_templates import (
    ATOMIC_ROLE_TEMPLATES,
    COMPOSITE_ROLE_TEMPLATES,
    PLATFORM_ADMIN_INCLUDES,
    PLATFORM_ADMIN_NAME,
)
from tests.conftest import auth_headers, create_custom_role, register_org

ATOMIC_ROLE_NAMES = {template["name"] for template in ATOMIC_ROLE_TEMPLATES}
COMPOSITE_ROLE_NAMES = {template["name"] for template in COMPOSITE_ROLE_TEMPLATES}
ALL_SEEDED_ROLE_NAMES = ATOMIC_ROLE_NAMES | COMPOSITE_ROLE_NAMES | {PLATFORM_ADMIN_NAME}


def test_atomic_role_templates_exclude_sso():
    for template in ATOMIC_ROLE_TEMPLATES:
        assert template["permission"] != "iam.sso.manage"
        assert "sso" not in template["name"].lower()


def test_platform_admin_includes_iam_admin_and_project_admin():
    assert set(PLATFORM_ADMIN_INCLUDES) == {"iam-admin", "project-admin"}


def test_organization_is_seeded_with_full_role_catalog(client):
    token = register_org(client)
    response = client.get("/api/v1/iam/roles", headers=auth_headers(token))
    assert response.status_code == 200
    roles = response.json()
    assert {role["name"] for role in roles} == ALL_SEEDED_ROLE_NAMES


def test_atomic_roles_are_locked_and_composite_roles_are_not(client):
    token = register_org(client)
    response = client.get("/api/v1/iam/roles", headers=auth_headers(token))
    roles_by_name = {role["name"]: role for role in response.json()}

    for name in ATOMIC_ROLE_NAMES:
        assert roles_by_name[name]["locked"] is True, name
        assert roles_by_name[name]["is_system"] is True, name

    for name in COMPOSITE_ROLE_NAMES | {PLATFORM_ADMIN_NAME}:
        assert roles_by_name[name]["locked"] is False, name
        assert roles_by_name[name]["is_system"] is True, name


def test_composite_role_effective_permissions_are_recursive(client):
    token = register_org(client)
    response = client.get("/api/v1/iam/roles", headers=auth_headers(token))
    roles_by_name = {role["name"]: role for role in response.json()}

    iam_admin_permissions = set(roles_by_name["iam-admin"]["effective_permissions"])
    project_admin_permissions = set(roles_by_name["project-admin"]["effective_permissions"])
    platform_admin_permissions = set(roles_by_name["platform-admin"]["effective_permissions"])

    assert "iam.users.manage" in iam_admin_permissions
    assert "projects.create" in project_admin_permissions
    assert platform_admin_permissions == iam_admin_permissions | project_admin_permissions


def _role_id_by_name(client, admin_token, name: str) -> int:
    roles = client.get("/api/v1/iam/roles", headers=auth_headers(admin_token)).json()
    return next(role["id"] for role in roles if role["name"] == name)


def test_atomic_role_cannot_be_edited_or_deleted(client):
    admin_token = register_org(client)
    role_id = _role_id_by_name(client, admin_token, "create-project")

    update_response = client.put(
        f"/api/v1/iam/roles/{role_id}",
        json={"name": "create-project", "description": "changed", "permissions": ["projects.create"]},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 400

    delete_response = client.delete(
        f"/api/v1/iam/roles/{role_id}", headers=auth_headers(admin_token),
    )
    assert delete_response.status_code == 400


def test_composite_role_can_be_edited_and_deleted(client):
    admin_token = register_org(client)
    role_id = _role_id_by_name(client, admin_token, "auditor")

    update_response = client.put(
        f"/api/v1/iam/roles/{role_id}",
        json={"name": "auditor", "description": "Custom description", "permissions": [], "included_role_ids": []},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Custom description"

    delete_response = client.delete(
        f"/api/v1/iam/roles/{role_id}", headers=auth_headers(admin_token),
    )
    assert delete_response.status_code == 204


def test_custom_role_can_compose_from_existing_roles(client):
    admin_token = register_org(client)
    view_project_id = _role_id_by_name(client, admin_token, "view-project")
    edit_results_id = _role_id_by_name(client, admin_token, "edit-results")

    create_response = client.post(
        "/api/v1/iam/roles",
        json={
            "name": "reviewer",
            "description": "Composed role",
            "permissions": [],
            "included_role_ids": [view_project_id, edit_results_id],
        },
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert set(body["effective_permissions"]) == {"projects.read", "findings.triage"}


def test_role_cannot_include_itself_creating_a_cycle(client):
    admin_token = register_org(client)
    custom_role_id = create_custom_role(client, admin_token, name="cyclic", permissions=[])

    update_response = client.put(
        f"/api/v1/iam/roles/{custom_role_id}",
        json={
            "name": "cyclic",
            "description": "cyclic",
            "permissions": [],
            "included_role_ids": [custom_role_id],
        },
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 400


def test_first_org_user_is_seeded_with_platform_admin(client):
    token = register_org(client)
    response = client.get("/api/v1/iam/profile", headers=auth_headers(token))
    body = response.json()
    role_names = {role["name"] for role in body["roles"]}
    assert role_names == {PLATFORM_ADMIN_NAME}
    assert "analytics.dashboard" in body["effective_permissions"]
    assert "iam.users.manage" in body["effective_permissions"]
