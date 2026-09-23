import io
import json

from tests.conftest import auth_headers, create_user_with_role, register_org

MINIMAL_SARIF = {
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "Semgrep", "rules": []}},
            "results": [
                {
                    "ruleId": "test-rule",
                    "level": "error",
                    "message": {"text": "Test finding"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "app.py"},
                                "region": {"startLine": 1},
                            }
                        }
                    ],
                }
            ],
        }
    ],
}


def create_project(client, token, name="Scan Project"):
    response = client.post(
        "/api/v1/projects", json={"name": name, "description": "d"}, headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


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


def upload_scan(client, token, project_id, scan_type="SAST"):
    return client.post(
        f"/api/v1/scans/upload/{project_id}",
        data={"scan_type": scan_type},
        files={"file": ("results.sarif", io.BytesIO(json.dumps(MINIMAL_SARIF).encode()), "application/json")},
        headers=auth_headers(token),
    )


def test_project_admin_can_upload_a_scan(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token)

    response = upload_scan(client, admin_token, project["id"])
    assert response.status_code == 200, response.text
    assert response.json()["tool"] == "Semgrep"


def test_uploading_to_a_nonexistent_project_name_auto_creates_it(client, db):
    admin_token = register_org(client)

    response = upload_scan(client, admin_token, "brand-new-project")
    assert response.status_code == 200, response.text

    from app.models.project import Project

    created = db.query(Project).filter(Project.name == "brand-new-project").first()
    assert created is not None
    assert created.owner_id is not None


def test_uploading_without_scans_upload_permission_is_rejected(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token)

    viewer_token = create_user_with_role(
        client, admin_token, role_name="auditor", email="scanviewer@example.com",
    )
    viewer_id = user_id_for(client, admin_token, "scanviewer@example.com")
    grant_project_access(client, admin_token, project["id"], viewer_id)

    response = upload_scan(client, viewer_token, project["id"])
    assert response.status_code == 403


def test_deleting_a_scan_requires_scans_delete_permission(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token)
    scan = upload_scan(client, admin_token, project["id"]).json()

    editor_token = create_user_with_role(
        client, admin_token, role_name="auditor", email="scaneditor@example.com",
    )
    editor_id = user_id_for(client, admin_token, "scaneditor@example.com")
    grant_project_access(client, admin_token, project["id"], editor_id)

    response = client.delete(f"/api/v1/scans/{scan['scan_id']}", headers=auth_headers(editor_token))
    assert response.status_code == 403

    admin_response = client.delete(f"/api/v1/scans/{scan['scan_id']}", headers=auth_headers(admin_token))
    assert admin_response.status_code == 204


def test_viewing_findings_only_requires_project_membership(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token)
    upload_scan(client, admin_token, project["id"])

    viewer_token = create_user_with_role(
        client, admin_token, role_name=None, email="findingviewer@example.com",
    )
    viewer_id = user_id_for(client, admin_token, "findingviewer@example.com")
    grant_project_access(client, admin_token, project["id"], viewer_id)

    response = client.get(
        f"/api/v1/projects/{project['id']}/findings", headers=auth_headers(viewer_token),
    )
    assert response.status_code == 200


def test_triage_requires_findings_triage_permission(client):
    admin_token = register_org(client)
    project = create_project(client, admin_token)
    upload_scan(client, admin_token, project["id"])

    viewer_token = create_user_with_role(
        client, admin_token, role_name="auditor", email="triageviewer@example.com",
    )
    viewer_id = user_id_for(client, admin_token, "triageviewer@example.com")
    grant_project_access(client, admin_token, project["id"], viewer_id)

    findings = client.get(
        f"/api/v1/projects/{project['id']}/findings", headers=auth_headers(admin_token),
    ).json()
    assert findings["items"], "expected the uploaded scan to produce at least one finding"

    finding_id = findings["items"][0]["id"]
    response = client.put(
        f"/api/v1/projects/{project['id']}/findings/{finding_id}/triage",
        json={"triage_status": "Confirmed", "comments": "test"},
        headers=auth_headers(viewer_token),
    )
    assert response.status_code == 403

    admin_triage = client.put(
        f"/api/v1/projects/{project['id']}/findings/{finding_id}/triage",
        json={"triage_status": "Confirmed", "comments": "test"},
        headers=auth_headers(admin_token),
    )
    assert admin_triage.status_code == 200
