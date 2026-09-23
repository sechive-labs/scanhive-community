from tests.conftest import auth_headers, create_custom_role, create_user_with_role, register_org


def create_project(client, token, name="Test Project"):
    return client.post(
        "/api/v1/projects",
        json={"name": name, "description": "d"},
        headers=auth_headers(token),
    )


def grant_project_access(client, admin_token, project_id, user_id):
    response = client.put(
        f"/api/v1/projects/{project_id}/access",
        json={"assignments": [{"user_id": user_id}], "group_ids": []},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200, response.text


def user_id_for(client, admin_token, email):
    users = client.get("/api/v1/iam/users", headers=auth_headers(admin_token)).json()
    return next(user["id"] for user in users if user["email"] == email)


def test_user_without_projects_create_permission_cannot_create_project(client):
    admin_token = register_org(client)
    member_token = create_user_with_role(
        client, admin_token, role_name="auditor", email="auditor@example.com",
    )
    response = create_project(client, member_token)
    assert response.status_code == 403


def test_security_analyst_can_create_project(client):
    admin_token = register_org(client)
    analyst_token = create_user_with_role(
        client, admin_token, role_name="security-analyst", email="analyst@example.com",
    )
    response = create_project(client, analyst_token)
    assert response.status_code == 200


def test_viewing_a_project_only_requires_membership_not_a_permission(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token).json()

    # No roles at all grants zero permissions, but project membership alone
    # should be enough to view the project.
    viewer_token = create_user_with_role(
        client, admin_token, role_name=None, email="viewer@example.com",
    )
    viewer_id = user_id_for(client, admin_token, "viewer@example.com")
    grant_project_access(client, admin_token, project["id"], viewer_id)

    response = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers(viewer_token))
    assert response.status_code == 200


def test_project_not_visible_without_membership(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token).json()

    outsider_token = create_user_with_role(
        client, admin_token, role_name="platform-admin", email="outsider@example.com",
    )
    response = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers(outsider_token))
    assert response.status_code == 403


def test_editing_a_project_requires_projects_edit_permission(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token).json()

    # Custom role: projects.read + projects.settings, no projects.edit
    role_id = create_custom_role(
        client, admin_token, name="settings-only", permissions=["projects.read", "projects.settings"],
    )
    editor_token = create_user_with_role(
        client, admin_token, role_name=None, email="editor@example.com",
    )
    editor_id = user_id_for(client, admin_token, "editor@example.com")
    assign_response = client.put(
        f"/api/v1/iam/users/{editor_id}/roles",
        json={"role_ids": [role_id]},
        headers=auth_headers(admin_token),
    )
    assert assign_response.status_code == 200
    grant_project_access(client, admin_token, project["id"], editor_id)

    response = client.put(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Renamed", "description": "d"},
        headers=auth_headers(editor_token),
    )
    assert response.status_code == 403


def test_project_admin_can_edit_and_delete_a_project_they_have_access_to(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token).json()

    project_admin_token = create_user_with_role(
        client, admin_token, role_name="project-admin", email="padmin@example.com",
    )
    padmin_id = user_id_for(client, admin_token, "padmin@example.com")
    grant_project_access(client, admin_token, project["id"], padmin_id)

    edit_response = client.put(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Renamed", "description": "d"},
        headers=auth_headers(project_admin_token),
    )
    assert edit_response.status_code == 200

    delete_response = client.delete(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(project_admin_token),
    )
    assert delete_response.status_code == 200


def test_project_settings_access_tab_requires_projects_settings_permission(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token).json()

    analyst_token = create_user_with_role(
        client, admin_token, role_name="security-analyst", email="analyst2@example.com",
    )
    analyst_id = user_id_for(client, admin_token, "analyst2@example.com")
    grant_project_access(client, admin_token, project["id"], analyst_id)

    # security-analyst has no projects.settings permission.
    response = client.get(
        f"/api/v1/projects/{project['id']}/access", headers=auth_headers(analyst_token),
    )
    assert response.status_code == 403


def test_project_owner_always_retains_full_control(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token).json()

    # The admin token here is also the project owner (creator).
    response = client.get(
        f"/api/v1/projects/{project['id']}/access", headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
