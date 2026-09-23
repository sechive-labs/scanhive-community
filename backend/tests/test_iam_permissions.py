from tests.conftest import auth_headers, create_custom_role, create_user_with_role, register_org


def test_user_with_no_roles_cannot_list_users(client):
    admin_token = register_org(client)
    member_token = create_user_with_role(
        client, admin_token, role_name=None, email="member@example.com",
    )
    response = client.get("/api/v1/iam/users", headers=auth_headers(member_token))
    assert response.status_code == 403


def test_iam_admin_can_list_and_invite_users(client):
    admin_token = register_org(client)
    iam_admin_token = create_user_with_role(
        client, admin_token, role_name="iam-admin", email="iamadmin@example.com",
    )

    list_response = client.get("/api/v1/iam/users", headers=auth_headers(iam_admin_token))
    assert list_response.status_code == 200

    invite_response = client.post(
        "/api/v1/iam/invitations",
        json={"email": "newbie@example.com", "role_ids": []},
        headers=auth_headers(iam_admin_token),
    )
    assert invite_response.status_code == 201


def test_granular_user_create_permission_allows_invite_but_not_role_management(client):
    admin_token = register_org(client)
    invite_role_id = create_custom_role(
        client, admin_token, name="inviter-only", permissions=["iam.users.create"],
    )
    inviter_token = create_user_with_role(
        client, admin_token, role_name=None, email="inviter@example.com",
    )
    assign_response = client.put(
        f"/api/v1/iam/users/{_user_id_for(client, admin_token, 'inviter@example.com')}/roles",
        json={"role_ids": [invite_role_id]},
        headers=auth_headers(admin_token),
    )
    assert assign_response.status_code == 200

    login = client.post(
        "/api/v1/auth/login", json={"email": "inviter@example.com", "password": "Password123!"},
    )
    inviter_token = login.json()["access_token"]

    invite_response = client.post(
        "/api/v1/iam/invitations",
        json={"email": "another@example.com", "role_ids": []},
        headers=auth_headers(inviter_token),
    )
    assert invite_response.status_code == 201

    role_create_response = client.post(
        "/api/v1/iam/roles",
        json={"name": "should-fail", "description": "x", "permissions": []},
        headers=auth_headers(inviter_token),
    )
    assert role_create_response.status_code == 403


def test_user_cannot_remove_their_own_iam_access(client):
    admin_token = register_org(client)
    response = client.get("/api/v1/iam/profile", headers=auth_headers(admin_token))
    admin_id = response.json()["id"]

    update_response = client.put(
        f"/api/v1/iam/users/{admin_id}",
        json={
            "email": "admin@example.com",
            "first_name": "Ada",
            "last_name": "Admin",
            "is_active": True,
            "role_ids": [],
        },
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 400


def test_admin_cannot_disable_their_own_account(client):
    admin_token = register_org(client)
    response = client.get("/api/v1/iam/profile", headers=auth_headers(admin_token))
    admin_id = response.json()["id"]

    update_response = client.put(
        f"/api/v1/iam/users/{admin_id}",
        json={
            "email": "admin@example.com",
            "first_name": "Ada",
            "last_name": "Admin",
            "is_active": False,
            "role_ids": [],
        },
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 400


def test_role_and_group_management_require_dedicated_permissions(client):
    admin_token = register_org(client)
    security_analyst_token = create_user_with_role(
        client, admin_token, role_name="security-analyst", email="analyst@example.com",
    )

    role_response = client.post(
        "/api/v1/iam/roles",
        json={"name": "nope", "description": "x", "permissions": []},
        headers=auth_headers(security_analyst_token),
    )
    assert role_response.status_code == 403

    group_response = client.get("/api/v1/iam/groups", headers=auth_headers(security_analyst_token))
    assert group_response.status_code == 403


def _user_id_for(client, admin_token: str, email: str) -> int:
    users = client.get("/api/v1/iam/users", headers=auth_headers(admin_token)).json()
    for user in users:
        if user["email"] == email:
            return user["id"]
    raise AssertionError(f"user {email!r} not found")
