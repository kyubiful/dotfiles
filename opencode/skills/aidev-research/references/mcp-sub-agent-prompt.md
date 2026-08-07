# MCP-based Research Sub-agent: Definition Guide & Spawn Prompt

## How to define a dynamic sub-agent from an MCP

For each MCP deemed relevant at step 4b, build a sub-agent definition with:

- **Name**: Use the MCP server name (e.g., "DevHub", "Geppetto", "Confluence")
- **Scope**: Derive from the MCP's tools — what kind of information can it provide? (e.g., an MCP with `search_applications` and `search_artifacts` tools → "Discover internal products and artifacts")
- **Tools**: The specific MCP tools the sub-agent should use
- **Return format**: A structured summary relevant to the MCP's domain, with source attribution tag `[MCP-Name]`
- **Rationale**: Why this MCP is relevant to the current research topic — this is presented to the user at step 4c

## Spawn prompt template

Adapt to each MCP's domain — fill in all `{placeholders}`:

```
Research via {mcp_name} for: {research_topic}

Context: {research_context}

Product Context Inspector findings:
{step_3_summary}

Use these tools from {mcp_name}: {relevant_tool_list}

Focus your search on: {specific_query_from_4b}

Return ONLY a structured summary:

## {mcp_name} Findings

### Relevant discoveries
[What you found that relates to the research topic. Be specific — names, descriptions, teams, statuses.]

### Implications for the research
[How these findings affect the research direction — overlaps, gaps, opportunities, constraints.]

Tag every finding: [{mcp_name}]
```
