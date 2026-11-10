<!-- KABISA-RULES:START -->
# Kabisa assistant rules

- Start every task by reading `docs/AI_CONTEXT.md`.
- If `graphify-out/graph.json` exists, also run `graphify query "<question>"` / `graphify explain "<symbol>"` to find callers and existing code before editing; do not depend on Graphify when absent.
- Before writing any new function, component, hook, endpoint, schema, helper or constant, check section 5 (Reuse list) and grep the repository with `rg`.
- Reuse or extend existing implementations. Never create a second implementation of the same thing or a parallel file (`utils2`, `helpers_new`, `*-v2`). If duplication seems unavoidable, explain why in the final message.
- Change only what the task needs. Do not make drive-by refactors, renames, reformatting or dependency changes.
- Do not change an existing function's behavior unless the task says so. Before changing a shared function, component or type, list its callers and state the impact.
- Say which files you will touch before editing.
- Respect section 3 (Invariants) and section 2 (Business rules) of `docs/AI_CONTEXT.md`.
- Update `docs/AI_CONTEXT.md` in the same change only when changing a business rule, main flow, shared helper/component (added, renamed, removed, changed signature), repo layout or how-to recipe; then update `Last synced commit` using `git rev-parse --short HEAD`.
- Do not update context for ordinary UI/text/style edits. If context and code disagree, treat code as truth: fix the context and say so.
- Treat local `.env` DATABASE_URL as potentially using an SSH tunnel (`127.0.0.1:5440`) to the same Postgres as the live site; verify the target before database operations without printing credentials.
- Run pytest only with its own TEST_DATABASE_URL pointing to a throwaway local Postgres *_test database, never the tunnel; fixtures drop/recreate tables.
- Do not run bootstrap/seed scripts casually. Take a backup before destructive or schema-changing operations.
- Accompany every schema change with an Alembic migration and a final-message note that deploy needs `alembic upgrade head`; production does not auto-migrate by default. Follow `docs/DEPLOYMENT.md` for deployment.
- Never print or commit secrets.
- Say what you could not verify. Do not invent endpoints, fields or flows; mark uncertain context claims `UNVERIFIED:` with what was checked.
- Include in every final message: files changed; whether `docs/AI_CONTEXT.md` was updated (or why no update was needed); anything needing Archit's decision.
<!-- KABISA-RULES:END -->

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
