# DOE knowledge base

Factorial originally planned a Neo4j knowledge graph to hold DOE domain
knowledge: design types, statistical concepts, diagnostic guidance, and the
decision rules that pick a design for a problem. That graph was never
populated, and the `app/graph/` driver it would have used was 15 lines of
unused connection setup.

It is no longer needed here, because that knowledge now lives upstream in
`process-improve` as versioned YAML, alongside the code that acts on it:

```
process_improve/experiments/knowledge/
    data/concepts.yaml          # statistical concept definitions
    data/design_types.yaml      # design descriptions and when each applies
    data/diagnostics.yaml       # residual-diagnostic troubleshooting
    data/decision_rules.yaml    # which design for which problem
    engine.py, api.py, models.py
```

The agent reaches it through two registry tools:

- **`doe_knowledge`** — retrieves concept definitions, design-type
  descriptions, diagnostic guides and worked examples.
- **`recommend_strategy`** — applies the decision rules to a described problem
  and returns a staged experimental plan, with run counts, transition rules,
  budget allocation, assumptions and risks.

## Why this is better than a graph database here

The knowledge is small, hand-curated, and read-only. A few hundred entries of
curated text do not need a graph database; they need to be reviewable in a
pull request, versioned with the code that consumes them, and testable. YAML
in the library gives all three, and it means the same knowledge serves the
hosted app, the MCP server, and the `doe-designer` Claude Skill without being
duplicated or drifting between them.

If a genuine graph workload appears later (say, similarity search across a
large corpus of past experiments to suggest starting points), that is the
point to revisit a graph store. It should be driven by a query that relational
storage cannot answer well, not by the assumption that domain knowledge
implies a knowledge graph.
