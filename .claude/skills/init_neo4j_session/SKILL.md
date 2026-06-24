---
name: init_neo4j_session
description: Initializes a Neo4j session via the `neo4j` MCP server to log the current User, working Session, and SnapRise repository context as a graph. Invoke at the start of a task to give AI agents foundational context. Triggers — "init a neo4j session", "start a neo4j session", "log my session in neo4j".
---

# Init Neo4j Session

Initialize a Neo4j graph context for the repository. This creates (or updates) the **User**, the active **Session**, and a **Repository** node for SnapRise, then links them — using the `neo4j` MCP server.

For a richer, full-architecture scan, use the companion skill `init-project-graph`. This skill is the lightweight equivalent of the original `.agents/skills/init_neo4j_session` agent.

## Trigger
Run this at the beginning of a task or session so the Neo4j database holds the foundational context for the current work environment.

## Inputs
- **User** — the person working. Accept natural language ("User Snaprise"), `User=Snaprise`, or positional.
- **Session** — the working session / feature name (e.g. `feature/boards-core`).

**If either input is missing, ask the user before proceeding. Do not guess.**

## Context Details
- **Repository:** SnapRise — a FastAPI backend with Celery workers, Redis, and SQLAlchemy. App code lives in `otp_service/app/`, migrations in `otp_service/alembic/versions/`, tests in `otp_service/tests/`. Frontend is Next.js in `snaprise-frontend/`.

## Execution Steps

1. **Verify context.** Confirm User and Session are known; ask if not.

2. **Create context entities.** Call `mcp__neo4j__create_entities` (entities merge by exact `name`, so re-running is idempotent):
   - A `User` entity named with the provided user.
   - A `Session` entity named with the provided session.
   - A `Repository` (or `Project`) entity named `SnapRise` with key structural observations.

3. **Link the entities.** Call `mcp__neo4j__create_relations`:
   - `User` —`STARTED`→ `Session`
   - `Session` —`WORKS_ON`→ `SnapRise`

4. **Confirm.** Briefly report to the user what was written (entities + relations).

## Example Payloads

`mcp__neo4j__create_entities`:
```json
{
  "entities": [
    { "name": "<USER>", "type": "User", "observations": ["The user developing the application"] },
    { "name": "<SESSION>", "type": "Session", "observations": ["Active development session for the feature"] },
    {
      "name": "SnapRise",
      "type": "Repository",
      "observations": [
        "Backend primarily lives in otp_service/",
        "Uses FastAPI, Celery, Redis, and SQLAlchemy",
        "Migrations are managed with Alembic in otp_service/alembic/",
        "Frontend is Next.js in snaprise-frontend/"
      ]
    }
  ]
}
```

`mcp__neo4j__create_relations`:
```json
{
  "relations": [
    { "source": "<USER>", "target": "<SESSION>", "relationType": "STARTED" },
    { "source": "<SESSION>", "target": "SnapRise", "relationType": "WORKS_ON" }
  ]
}
```

## Notes
- These are the actual Claude Code tool names — the original agent's `call_mcp_tool` + `ToolName: "create_entities"` on `docker-gateway` maps to `mcp__neo4j__create_entities` here.
- Add further context (tasks, bugs, modules) with `mcp__neo4j__add_observations` or by creating more entities and relations.
