<div align="center">
  <img src="./scanhive-logo.svg" alt="ScanHive" width="176" />

  <h1>ScanHive Community</h1>

  <p><strong>Unified Dashboard for modern DevSecOps teams.</strong></p>
  <p>Consolidate SARIF results, remove duplicate noise, triage vulnerabilities, and manage security access across projects and organizations.</p>
</div>

## Overview

ScanHive Community is the free, self-hosted edition of ScanHive. It provides a central workspace for security results produced throughout the software delivery lifecycle, normalizing SARIF reports from supported scanners, correlating recurring findings, and presenting the current security posture through project-level and portfolio-level dashboards.

The platform is designed for multi-tenant deployments with organization isolation, project access controls, role-based authorization, and API keys. Anyone can register and create their own organization; organization admins invite teammates by shareable link.

**No scanner plugin/integration marketplace.** Community edition has no native CI/CD plugins or one-click scanner integrations — every scan result reaches ScanHive either through the "Upload scan" button in the dashboard, or by pushing SARIF straight to the API with `curl` (or any HTTP client) as a CI/CD pipeline step. See [SARIF ingestion](#sarif-ingestion) below. In exchange, there is no scan-count limit: import as many SARIF reports as you like.

## Editions

This repository contains **ScanHive Community**, the self-hosted, free edition of ScanHive:

- **Unlimited scans.** No metering, no scan-count caps, no paid tiers — self-host it and ingest as much SARIF data as your infrastructure can take.
- **No scanner plugins/integrations.** Other ScanHive editions ship native CI/CD plugins and one-click scanner integrations; Community edition instead offers a manual "Upload scan" button in the dashboard plus a stable HTTP API for scripted/CI ingestion (`curl`, a pipeline step, a script — see [SARIF ingestion](#sarif-ingestion)).
- **No SSO.** Authentication is email/password only. Role-based access control, user groups, and project-level access are all still fully supported (see [Roles and permissions](#roles-and-permissions)) — only SSO/SAML is out of scope for this edition.


## Core capabilities

- Import and normalize SARIF 2.x reports, uploaded from the dashboard or pushed via the API.
- Classify scans as SAST, SCA, Secrets, Container Security, IaC, or DAST.
- Recognize common tools including Trivy, Semgrep, CodeQL, Snyk, Checkmarx, Fortify, Gitleaks, Grype, Checkov, KICS, OWASP ZAP, and others.
- Correlate results across scans to prevent duplicate vulnerability counts.
- Track new, recurrent, and fixed results.
- Triage results as To Verify, Confirmed, False Positive, Not Exploitable, or Fixed.
- Suppress previously triaged false positives in subsequent scans.
- Review project overview, scan history, scanner coverage, and vulnerability analytics.
- Export project, portfolio, and individual scan reports as PDF or CSV.
- Self-serve registration creates a new organization and its first administrator.
- Invite team members by shareable link, with roles assigned at invite time.
- Control access through users, roles, user groups, project assignments, and scoped permissions.
- Role-based UI: navigation and action buttons (create/edit/delete projects, upload/delete scans, triage findings, manage IAM) only appear for users whose effective permissions grant them — enforced identically on the API regardless of what the UI shows.
- Create user API keys with 365-day validity and regeneration support.


## Local development

### Prerequisites

- Docker Desktop with Docker Compose
- Git
- Node.js current LTS and npm (only required for optional frontend dev mode)

### 1. Configure the API

```bash
cp backend/.env.example backend/.env
```

| Variable | Purpose | Development default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string | Provided in `.env.example` |
| `FRONTEND_URL` | Browser application URL, used to build invitation links | `http://localhost` |
| `SMTP_HOST` | SMTP server for invitation emails; blank disables sending | Blank |
| `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS` | SMTP delivery settings | See `.env.example` |

### 2. Start the full application

```bash
docker compose up -d --build
```

This single command starts PostgreSQL, the API, and the web application (built and served as static assets — no dev server involved). Verify the services:

```bash
docker compose ps
curl http://localhost:8000/health
```

Open `http://localhost` once all three containers report as running.

The frontend's API address is baked in at image build time from `VITE_API_BASE_URL` (default `http://localhost:8000`). To point the built frontend at a different API address, set `VITE_API_BASE_URL` in your shell (or an `.env` file next to `docker-compose.yml`) before running `docker compose up -d --build`.

### Stop the environment

```bash
docker compose down
```

## Deploying to a VPS

`docker-compose.prod.yml` runs the same three services behind an `edge` reverse proxy. Only `edge` publishes a port (80 and 443) — Postgres and the backend are reachable exclusively from other containers on the internal network, so there is nothing listening on `:8000` or `:5432` for the outside world to find. The frontend's own nginx (`frontend/nginx.conf`) proxies `/api`, `/docs`, `/health`, and `/openapi.json` to the backend container internally, so the browser only ever talks to one origin, over one port.


### Configure and start the stack

On the VPS:

```bash
git clone <your-repo-url> scanhive-dashboard
cd scanhive-dashboard

cp backend/.env.example backend/.env
# edit backend/.env:
#   - DATABASE_URL: set its password to the same value you'll pass as
#     POSTGRES_PASSWORD below
#   - FRONTEND_URL=https://scanhive.example.com, real SMTP settings, etc.
# (see the "Configure the API" table above for what each variable does)

SERVER_NAME=scanhive.example.com \
POSTGRES_PASSWORD=<a strong, unique password> \
  docker compose -p scanhive-prod -f docker-compose.prod.yml up -d --build
```

Using `-p scanhive-prod` gives this stack its own project name, so its containers/volumes/network never collide with a `docker-compose.yml` (dev) stack on the same machine.

`docker-compose.prod.yml` has no default Postgres password — it refuses to start unless `POSTGRES_PASSWORD` is set, so a real deployment can never accidentally run on a guessable default. `POSTGRES_USER`/`POSTGRES_DB` default to `scanhive` and don't need to be set unless you want different values.


### 4. Verify

```bash
curl -I http://scanhive.example.com        # expect 301 -> https
curl https://scanhive.example.com/health   # expect {"database":"Connected","status":"Healthy"}
```

Then open `https://scanhive.example.com` in a browser and register your organization.


## SARIF ingestion

Upload endpoints accept SARIF 2.x files and require a project plus one of the supported scan types:

```text
SAST · SCA · Secrets · Container Security · IaC · DAST
```

The API derives the scanner name from the SARIF document and maps known aliases to canonical tool names. Results are normalized for severity and correlated within the project, scanner, and scan-type scope to identify new and recurrent vulnerabilities.

Two ways to get a scan in:

- **Dashboard**: the upload icon next to each project on the Projects page opens a modal (scan type + SARIF file), with live upload progress.
- **API / CI pipeline**: `POST` directly to the upload endpoint, authenticating with a personal API key. If the given project name doesn't exist yet, it's auto-created (owned by the uploading user) instead of failing — a pipeline shouldn't need someone to click "Create project" first.

Use Swagger UI at `http://localhost:8000/docs` to test authenticated scan uploads and inspect the request schema.

Example upload with `curl`, authenticating with a personal API key (create one under **Settings → API Keys**):

```bash
curl -X POST "http://localhost:8000/api/v1/scans/upload/<project-id-or-name>" \
  -H "X-API-Key: <your-api-key>" \
  -F "scan_type=SAST" \
  -F "file=@results.sarif"
```

## Roles and permissions

ScanHive's RBAC is hierarchical: every permission is backed by a real **role** row, and roles can *include* other roles instead of duplicating their permissions. Every new organization is seeded with the same role catalog as the rest of ScanHive, minus SSO (SSO/SAML is not part of Community edition).

- **Atomic roles** — one per individual capability (e.g. `create-project`, `delete-scan`, `manage-users`). Each holds exactly one permission and is **locked**: it can't be edited or deleted, only composed into other roles.
- **Composite roles** — `iam-admin`, `project-admin`, `auditor`, `security-analyst` — hold no permissions directly, just a list of included atomic roles. Unlike atomic roles, these are fully editable and deletable.
- **`platform-admin`** — a composite of composites (`iam-admin` + `project-admin`). Assigned automatically to the organization's first user at registration.

| Composite role | Grants |
| --- | --- |
| `platform-admin` | Everything below, combined. |
| `iam-admin` | Full IAM administration: manage users, roles, and user groups. |
| `project-admin` | Full project lifecycle: create/edit/delete projects, manage project access, upload/delete scans, triage findings, view the analytics dashboard. |
| `security-analyst` | Create/edit projects, triage findings, view analytics — no delete, no project access management. |
| `auditor` | Read-only: analytics dashboard plus project/scan visibility. |

Custom roles can be composed from any mix of the above (from **Settings → Roles**) — e.g. a role granting only `view-project` + `project-settings` recreates a settings-only reviewer. The underlying atomic permissions: `iam.users.manage`, `iam.users.create`, `iam.users.update`, `iam.users.delete`, `iam.roles.manage`, `iam.groups.manage`, `projects.create`, `projects.edit`, `projects.delete`, `projects.read` (report export), `scans.read`, `scans.upload`, `scans.delete`, `projects.settings` (project access list), `findings.triage`, `analytics.dashboard` (portfolio dashboard).

## Additional documentation

- [Interactive API documentation](http://localhost:8000/docs) — available while the API is running

- [ScanHive documentation](https://docs.sechivelabs.com/)

