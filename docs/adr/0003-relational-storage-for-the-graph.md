# 0003. Store the graph in relational tables, not a graph database

- Status: Accepted
- Date: 2026-10-03

## Context
The product is called Action*Graph*: meetings, actions, people, decisions and
risks are connected (OWNED_BY, BLOCKS, UPDATED, …). Graph databases such as
Neo4j model this natively. But our queries are shallow: "open actions",
"this action's history", "what blocks this action", all 1–2 hops. We also
need transactions, simple local setup and a mainstream query skill set.

## Decision
Store entities and relationships as relational tables with foreign keys
(`storage/models.py`). Build the graph view (nodes + edges) *on request* in
`graph/builder.py`, and export it as JSON (for the UI) or Mermaid (for docs).

## Consequences
- One database, one transaction model, no extra server.
- The graph can never be out of sync with the data, because it is derived from it.
- Edges are typed by foreign keys and the `ActionEvent` table, which keeps the schema explicit and validated.
- Multi-hop questions ("everything transitively blocked by X") would need recursive SQL (CTEs) or loading into memory. Revisit this ADR if such queries become core.

## Alternatives considered
- **Neo4j / graph database:** expressive traversals, but another service, another query language (Cypher), weaker fit for transactional CRUD.
- **Generic `nodes` + `edges` tables:** flexible, but loses type safety and foreign-key integrity; queries get harder, not easier.
- **NetworkX in memory only:** great for analysis, no persistence.
