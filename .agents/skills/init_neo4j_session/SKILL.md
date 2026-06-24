---
name: init_neo4j_session
description: Initializes a Neo4j session using the docker-gateway MCP server to log the SnapRise repository context, user (Snaprise), and session (feature/boards-core).
---

# Init Neo4j Session

This skill initializes a Neo4j graph context for the repository. It sets up the user, the active session, and structural knowledge of the SnapRise repository using the `docker-gateway` MCP server.

## Trigger
Trigger this skill at the beginning of a task or session to ensure the Neo4j database has the foundational context for the current work environment.

## Context Details
- **User:** Dynamically determined from the user's prompt or current context. If not provided, **ask the user** for their name.
- **Session Name:** Dynamically determined from the user's prompt or task. If not provided, **ask the user** for the session or feature name.
- **Repository Context:** SnapRise repository, which is a FastAPI backend with Celery workers, Redis, and SQLAlchemy. The primary application code lives in `otp_service/app/`, migrations in `otp_service/alembic/versions/`, and tests in `otp_service/tests/`.

## Execution Steps

1. **Verify Context:**
   Check if the user has provided their name and the current session name. If either is missing, explicitly ask the user for this information before proceeding.

2. **Create Context Entities:**
   Use the `call_mcp_tool` tool with `ToolName: "create_entities"` on the `docker-gateway` server to create the core nodes:
   - A `User` entity with the dynamically provided name.
   - A `Session` entity with the dynamically provided session name.
   - A `Repository` entity named `SnapRise` containing key observations about its structure (FastAPI, Celery, Redis, `otp_service/`).

3. **Link the Entities:**
   Use the `call_mcp_tool` tool with `ToolName: "create_relations"` on the `docker-gateway` server to establish their relationships:
   - Link the dynamically named `User` to the dynamically named `Session` with a `STARTED` or `OWNS` relationship.
   - Link the dynamically named `Session` to `SnapRise` with a `WORKS_ON` or `MODIFIES` relationship.

## Example Payload

**Entities Setup:**
```json
{
  "entities": [
    {
      "name": "<USER_NAME_FROM_PROMPT>",
      "type": "User",
      "observations": ["The user developing the application"]
    },
    {
      "name": "<SESSION_NAME_FROM_PROMPT>",
      "type": "Session",
      "observations": ["Active development session for the feature"]
    },
    {
      "name": "SnapRise",
      "type": "Repository",
      "observations": [
        "Backend primarily lives in otp_service/",
        "Uses FastAPI, Celery, Redis, and SQLAlchemy",
        "Migrations are managed with Alembic in otp_service/alembic/"
      ]
    }
  ]
}
```

**Relations Setup:**
```json
{
  "relations": [
    {
      "source": "<USER_NAME_FROM_PROMPT>",
      "target": "<SESSION_NAME_FROM_PROMPT>",
      "relationType": "STARTED"
    },
    {
      "source": "<SESSION_NAME_FROM_PROMPT>",
      "target": "SnapRise",
      "relationType": "WORKS_ON"
    }
  ]
}
```
