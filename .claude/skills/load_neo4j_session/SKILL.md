---
name: load_neo4j_session
description: Retrieves previously logged context, memory, and entities from the Neo4j graph for a given User and Session via the `neo4j` MCP server, then summarizes what was recalled. Triggers — "load my neo4j session", "resume my session", "recall what we did in neo4j".
---

# Load Neo4j Session Memory

Recall context, learned concepts, and progress from a previous or ongoing session stored in Neo4j. This is the Claude Code equivalent of the original `.agents/skills/load_neo4j_session` agent, rewired to the real `neo4j` MCP tools.

It reads the graph written by `init_neo4j_session` / `init-project-graph`, so the naming contract (User, Session, `STARTED`, `WORKS_ON`) is assumed.

## Trigger
Use this skill when:
- The user asks to resume a previous task or feature.
- You need to recall the architecture, preferences, or work done in a specific session.
- The user mentions they already logged progress for their session.

## Inputs
- **User** — the person whose session to load.
- **Session** — the working session / feature name.

**If either is missing, ask the user before proceeding. Do not guess.**

## Execution Steps

1. **Verify context.** Confirm User and Session; ask if not provided.

2. **Retrieve session context.** Query the graph with `mcp__neo4j__default-read_neo4j_cypher`. Find the `User` and `Session` nodes plus any related context (Features, Tasks, Repositories, Modules, Conventions) within a few hops.
   - If the user only gives a name, you can also use `mcp__neo4j__search_memories` or `mcp__neo4j__find_memories_by_name` to locate nodes, or `mcp__neo4j__read_graph` to dump the whole graph as a fallback.

3. **Process and present.** Analyze the returned graph data and present a concise summary of the recovered context so the user knows what you remembered.

## Example Usage

`mcp__neo4j__default-read_neo4j_cypher`:
```json
{
  "query": "MATCH (u:User {name: '<USER>'})-[*1..2]-(s:Session {name: '<SESSION>'})-[r*1..3]-(context) RETURN u, s, type(r), context LIMIT 50"
}
```

Adjust the Cypher as needed for specific relationship types (`STARTED`, `WORKS_ON`, `OWNS`) or node labels to retrieve particular tasks, bugs, or modules.

## Notes
- The original agent's `call_mcp_tool` with `ToolName: "default-read_neo4j_cypher"` on `docker-gateway` maps to `mcp__neo4j__default-read_neo4j_cypher` here.
- Inspect the live schema first with `mcp__neo4j__default-get_neo4j_schema` if your queries return nothing — labels/relationship names may differ from the assumed contract.
