---
name: save_neo4j_conversation
description: Distills the current Claude Code conversation into a graph and persists it to Neo4j via the `neo4j` MCP server — the Session, each user request as a Turn, plus the Tasks, Decisions, Topics, and changed Files it produced. Reuses the User/Session/Repository contract from init_neo4j_session. Triggers — "save this conversation to neo4j", "load this session's chat into neo4j", "persist our conversation in neo4j", "log what we did to the graph".
---

# Save Neo4j Conversation

Capture the **current Claude Code conversation** as a knowledge graph in Neo4j so a later
session (or another agent) can recall what was asked, decided, and changed — using the
`neo4j` MCP server.

This skill writes *on top of* the graph created by `init_neo4j_session`: it reuses the same
**User**, **Session**, and **Repository (SnapRise)** nodes and the `STARTED` / `WORKS_ON`
relations, then hangs a **Conversation** and its **Turns** off the Session. Recall it later
with `load_neo4j_session`.

## Trigger
Use when the user wants the work from this chat written to the graph — e.g. at the end of a
task, before switching context, or to checkpoint progress.

## Inputs
Parse both from the invoking prompt. Accept natural language (`User Satrajeeth`,
`Session boards-core-integration`), `User=...` / `Session=...`, or positional args.

- **User** — the person working.
- **Session** — the working session / feature name. If absent, fall back to the current git
  branch (`git rev-parse --abbrev-ref HEAD`) and confirm it with the user.

**If User is missing and cannot be inferred, ask before proceeding. Do not guess the User.**

## Graph model

```
User ──STARTED──▶ Session ──WORKS_ON──▶ SnapRise (Repository)
                     │
                     └──HAD──▶ Conversation ──INCLUDES──▶ Turn 1, Turn 2, …
                                                              │
                Turn ──PRODUCED──▶ File        (files created/edited)
                Turn ──DECIDED──▶ Decision     (choices made + rationale)
                Turn ──ABOUT────▶ Topic        (subject/feature area)
                Turn ──NEXT─────▶ Turn          (chronological order)
```

**Naming for idempotency.** Entities merge by exact `name`, so make names stable and unique:
- Conversation: `<SESSION> · conversation`
- Turn: `<SESSION> · Turn N — <short slug>` (e.g. `boards-core-integration · Turn 1 — postman-to-frontend integration`)
- File: the repo-relative path (e.g. `snaprise-frontend/src/lib/api/boards.ts`)
- Decision / Topic: a short stable phrase (e.g. `Use position not order for ordering`).

Re-running the skill is safe: existing nodes merge and new observations append.

## Execution Steps

1. **Resolve inputs.** Extract User and Session from the prompt; default Session to the git
   branch if unstated (confirm it). Ask for User only if it cannot be determined.

2. **Ensure base context exists** (idempotent — same contract as `init_neo4j_session`).
   Call `mcp__neo4j__create_entities` for the `User`, `Session`, and `SnapRise` `Repository`
   nodes, then `mcp__neo4j__create_relations` for `User`-`STARTED`->`Session` and
   `Session`-`WORKS_ON`->`SnapRise`. (Skip the writes you already know exist this session.)

3. **Distill the conversation from context.** Walk the actual messages in this session and
   extract, per user request (a "Turn"):
   - the user's intent (1–2 sentence summary),
   - the outcome / what you did,
   - **Files** created or edited (repo-relative paths),
   - **Decisions** made and their rationale (especially user choices and tradeoffs),
   - **Topics** / feature areas touched.
   Keep each observation a single atomic fact. Do **not** store secrets, tokens, or full file
   contents — store paths, summaries, and decisions.

4. **Write the conversation graph.**
   - `mcp__neo4j__create_entities` — the `Conversation`, every `Turn`, and the `File` /
     `Decision` / `Topic` nodes, each with concise observations.
   - `mcp__neo4j__create_relations` — `Session`-`HAD`->`Conversation`,
     `Conversation`-`INCLUDES`->each `Turn`, `Turn`-`NEXT`->next `Turn`, and each Turn's
     `PRODUCED` / `DECIDED` / `ABOUT` edges.
   - For follow-up runs on a Turn that already exists, prefer `mcp__neo4j__add_observations`
     to append rather than recreating the node.

5. **Verify (optional).** Run `mcp__neo4j__default-read_neo4j_cypher` to count what landed:
   `MATCH (s:Session {name:'<SESSION>'})-[:HAD]->(:Conversation)-[:INCLUDES]->(t:Turn) RETURN count(t)`.

6. **Confirm.** Report the entities and relations written (Turns, Files, Decisions, Topics).

## Example Payloads

These use the contract from this repo's actual work as a concrete illustration.

`mcp__neo4j__create_entities`:
```json
{
  "entities": [
    { "name": "<USER>", "type": "User", "observations": ["The user developing SnapRise"] },
    { "name": "<SESSION>", "type": "Session", "observations": ["Active development session"] },
    { "name": "<SESSION> · conversation", "type": "Conversation", "observations": ["Claude Code chat for this session"] },
    {
      "name": "<SESSION> · Turn 1 — postman-to-frontend integration",
      "type": "Turn",
      "observations": [
        "User asked to integrate the Board_Api Postman collection into snaprise-frontend",
        "Probed the live board service OpenAPI at localhost:8002 to confirm shapes",
        "Generated a full typed client covering all 33 endpoints"
      ]
    },
    { "name": "snaprise-frontend/src/lib/api/boards.ts", "type": "File", "observations": ["Typed Board Service client (boardApi)"] },
    { "name": "Use position not order for ordering", "type": "Decision", "observations": ["API orders by 'position'; frontend was sending 'order', which FastAPI dropped — fixed"] },
    { "name": "Board API integration", "type": "Topic", "observations": ["Frontend wiring for the SnapRise board service"] }
  ]
}
```

`mcp__neo4j__create_relations`:
```json
{
  "relations": [
    { "source": "<USER>", "target": "<SESSION>", "relationType": "STARTED" },
    { "source": "<SESSION>", "target": "SnapRise", "relationType": "WORKS_ON" },
    { "source": "<SESSION>", "target": "<SESSION> · conversation", "relationType": "HAD" },
    { "source": "<SESSION> · conversation", "target": "<SESSION> · Turn 1 — postman-to-frontend integration", "relationType": "INCLUDES" },
    { "source": "<SESSION> · Turn 1 — postman-to-frontend integration", "target": "snaprise-frontend/src/lib/api/boards.ts", "relationType": "PRODUCED" },
    { "source": "<SESSION> · Turn 1 — postman-to-frontend integration", "target": "Use position not order for ordering", "relationType": "DECIDED" },
    { "source": "<SESSION> · Turn 1 — postman-to-frontend integration", "target": "Board API integration", "relationType": "ABOUT" }
  ]
}
```

## Notes
- These are the real Claude Code tool names; on the `neo4j` MCP server the writers are
  `mcp__neo4j__create_entities`, `mcp__neo4j__create_relations`, and
  `mcp__neo4j__add_observations`. Reads use `mcp__neo4j__default-read_neo4j_cypher`.
- Inspect the live schema with `mcp__neo4j__default-get_neo4j_schema` first if labels or
  relationship names differ from the assumed contract.
- Pairs with `init_neo4j_session` (bootstraps User/Session/Repository) and
  `load_neo4j_session` (reads it all back). Keep the relation vocabulary consistent so recall
  queries keep working.
- Privacy: store summaries, file paths, and decisions — never secrets, credentials, tokens,
  or verbatim file contents.
