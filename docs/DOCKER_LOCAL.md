# Docker Local Stack — NYC DOT Sidewalk Toolkit

Run the analyst autopilot and optional Dash UI locally with Docker Compose.

## Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine + Compose v2
- `.env` in the project root (create with the install wizard first)

## Quick start

```bash
# 1. Configure (host)
python -m socrata_toolkit.install_wizard
# or: python launcher.py setup wizard

# 2. Start Postgres + analyst stack
docker compose --profile analyst up -d postgres
docker compose --profile analyst run --rm setup

# 3. Run analyst pack on a schedule
docker compose --profile analyst up -d analyst-runner
```

Or use the launcher:

```bash
python launcher.py setup docker
docker compose --profile analyst run --rm setup
```

## Services (profile `analyst`)

| Service | Purpose |
|---------|---------|
| `postgres` | PostGIS warehouse (shared with full stack) |
| `setup` | One-shot install wizard / config bootstrap |
| `analyst-runner` | Scheduled `scripts/analyst_scheduler.py` |
| `dash-web` | Optional Dash UI on port `8050` |

## Wizard in a container

**Interactive** (TTY required):

```bash
docker compose --profile analyst run --rm setup
```

**Non-interactive** (CI / automation):

```bash
export WIZARD_NONINTERACTIVE=1
export SOCRATA_APP_TOKEN=your_token
export PG_DSN=postgresql://dot_user:dot_pass@postgres:5432/sidewalk_db
docker compose --profile analyst run --rm setup
```

Environment template: `config/.env.example`.

## Volumes

| Host path | Container | Use |
|-----------|-----------|-----|
| `./config` | `/app/config` | Analyst profile YAML |
| `./data` | `/app/data` | Excel / sample inputs |
| `./outputs` | `/app/outputs` | Analyst pack artifacts |
| `.env` | loaded via `env_file` | Secrets and paths |

## Setup entrypoint

`docker/setup-entrypoint.sh` (via `Dockerfile.analyst`):

1. Copies `config/.env.example` → `.env` inside the container if missing
2. Copies `analyst_profile.example.yaml` if profile missing
3. Runs DuckDB / optional Socrata health checks
4. Executes the service command

## Full stack vs analyst-only

- **Analyst only:** `--profile analyst` (Postgres + runner)
- **Full platform:** omit profile for API, Airflow, Grafana, etc. (see root `docker-compose.yml`)

## Troubleshooting

- **Missing `.env` on host:** Run `python -m socrata_toolkit.install_wizard` before `docker compose up`.
- **Postgres not ready:** `docker compose --profile analyst up -d postgres` and wait for healthy status.
- **Socrata checks fail:** Set `SOCRATA_APP_TOKEN` in `.env`; use `--skip-checks` for offline setup.
