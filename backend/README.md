# Merge Marshal Backend

FastAPI service that owns loading and validating a repository's canonical
`.graph/graph.json` artifact.

## Run the full application with Docker

From the repository root, create `backend/.env` as described below and run:

```powershell
docker compose -f compose.yaml.dev up --build
```

The frontend is available at `http://127.0.0.1:5173` and the backend at
`http://127.0.0.1:8000`. Source files are mounted for development reloads.

To shut down compose stack, just run

```powershell
docker compose -f compose.yaml.dev down
```

## Prerequisites

- Python 3.11+

## Install

From the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -e "./backend[dev]"
```

On macOS or Linux, activate the environment with:

```bash
source backend/.venv/bin/activate
```

## Configure and run

Create the local dotenv file and set the repository whose graph should be served:

```powershell
Copy-Item backend/.env.example backend/.env
```

```dotenv
MERGE_MARSHAL_REPO_PATH=../test_repo_2
```

Relative repository paths are resolved from `backend/`. Operating-system
environment variables are intentionally ignored; runtime configuration is read
from `backend/.env` through the Pydantic settings model.

If the setting is absent, the repository root is used. After changing `.env`,
fully restart the backend process so the application creates a new settings
instance.

Start the API through the root entrypoint:

```powershell
uvicorn main:app --app-dir backend/src --reload --host 127.0.0.1 --port 8000
```

The target repository must contain:

```text
.graph/graph.json
```

Available endpoints:

- `GET /api/health`
- `GET /api/graph`
- Interactive API documentation at `http://127.0.0.1:8000/docs`

The graph is read and validated on every request. Successful responses include
`Cache-Control: no-store`, allowing later graph updates to appear without
restarting the API.

## Error responses

- `404 graph_not_found`: no `.graph/graph.json` exists in the configured repo.
- `422 graph_invalid`: malformed JSON, unsupported schema, invalid relationships,
  or missing referenced repository paths.
- `500 graph_unreadable`: the graph exists but cannot be read.

## Test

```powershell
cd backend
pytest
```
