---
name: load_neo4j_session
description: Retrieves previously logged memory, context, and entities from the Neo4j graph database for a specific User and Session using the docker-gateway MCP server.
---

# Load Neo4j Session Memory

This skill allows the agent to recall context, learned concepts, and progress from a previous or ongoing session in the Neo4j database. 

## Trigger
Use this skill when:
- The user asks you to resume a previous task or feature.
- You need to recall the architecture, preferences, or work done in a specific session.
- You are starting work and the user mentions they have already logged progress for their session.

## Execution Steps

1. **Verify Context:**
   Check if the user name and the session (or feature) name are available in the prompt or current context. If either is missing, explicitly ask the user for this information before proceeding.

2. **Retrieve Session Context:**
   Use the `call_mcp_tool` tool with `ToolName: "default-read_neo4j_cypher"` (or `read-cypher`) on the `docker-gateway` server to query the database.
   You want to find the User and Session nodes, and any related context nodes (e.g., Features, Tasks, Repositories, Code Modules) connected to that session.

3. **Process and Present Insights:**
   Analyze the returned graph data and present a summary of the recovered session context to the user so they know what you've remembered.

## Example Usage

**Cypher Query to Load Memory:**
Use the `default-read_neo4j_cypher` tool with a query to find the session and its related entities up to a few hops away.

```json
{
  "ServerName": "docker-gateway",
  "ToolName": "default-read_neo4j_cypher",
  "Arguments": {
    "query": "MATCH (u:User {name: '<USER_NAME_FROM_PROMPT>'})-[*1..2]-(s:Session {name: '<SESSION_NAME_FROM_PROMPT>'})-[r*1..3]-(context) RETURN u, s, type(r), context LIMIT 50"
  }
}
```

*Note: You can adjust the Cypher query as needed based on the relationships (e.g., `STARTED`, `WORKS_ON`, `OWNS`) or node types to retrieve specific tasks, bugs, or modules.*
