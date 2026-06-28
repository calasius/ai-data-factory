# Deploying to Railway

The app deploys as **two Docker services** (api, web) + a **managed Postgres** +
a **Volume** for project files. opencode, `uv`, and the DeepSeek config are baked
into the api image, so the deploy is self-contained.

## Services

| Service | Build | Notes |
|---|---|---|
| **Postgres** | Railway plugin | provides connection vars |
| **api** | `docker/Dockerfile.api` | FastAPI + opencode + uv; needs a Volume |
| **web** | `docker/Dockerfile.web` | Next.js; `NEXT_PUBLIC_API_URL` baked at build |

Redis is **not required** (SSE is in-process).

## Per-service build config

The Dockerfiles live under `docker/`, but they need the **repo root** as build
context (they `COPY api/`, `tools/`, `.claude/`, `web/`). So for each service:

- **Root Directory:** `/` (leave default — do NOT set it to `docker/`)
- Point the service at its config file via **Settings → Config File Path**:
  - api → `railway.api.json`
  - web → `railway.web.json`

Those files set `build.dockerfilePath` (and healthcheck/restart). Alternatively,
skip the config files and set a service variable
`RAILWAY_DOCKERFILE_PATH=docker/Dockerfile.api` (or `.web`).

## Environment variables

### api
```
DEEPSEEK_API_KEY=<secret>
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}
PROJECTS_DIR=/data/projects
SECRET_KEY=<secret>
# optional (have defaults): DEEPSEEK_MODEL, DEEPSEEK_AUTHORING_MODEL, DEEPSEEK_EDIT_MODEL
```
- Attach a **Volume** mounted at `/data/projects`.
- `$PORT` is honored automatically (the Dockerfile CMD uses it).

### web (build-time)
```
NEXT_PUBLIC_API_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}
```
- `PORT` / `HOSTNAME` are handled by the image.

## Deploy order

1. Create **Postgres** (plugin).
2. Create **api** → config file `railway.api.json`, set `DEEPSEEK_API_KEY` +
   `DATABASE_URL`, attach the Volume at `/data/projects`, deploy. Generate its
   public domain.
3. Create **web** → config file `railway.web.json`, set `NEXT_PUBLIC_API_URL` to
   the api's public domain, deploy.

## Gotchas

- **Single instance for the api.** opencode runs in-process (one server per
  pipeline step) and the Volume + in-memory SSE are per-instance — don't scale
  the api to multiple replicas. To scale, split opencode into its own service.
- Give the api service enough memory (**≥1–2 GB**): the coding step runs an
  opencode server plus `uv`/pytest.
- Templates (`.claude/commands`, `tools/templates`) ship **in the image** — edit
  + redeploy to change them (no live bind-mounts like local compose).
- DB schema is created on startup (`create_all`) — no migration step needed.
