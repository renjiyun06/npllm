# Section 3: Compilation Principles

**Goal**: Standards for compiling—how to extract intent, abstract code, ensure completeness, and handle edge cases.

**Intent extraction**:

- Signals: type structure, identifier semantics, comments/docstrings, overall code context.
- Conflicts priority: (1) Types (hard constraints) → (2) Compiler directives → (3) Comments/docstrings → (4) Names.
- If unclear: choose the most general reasonable interpretation, prefer conservative roles, avoid unsupported assumptions, document ambiguity in NOTES.

**Abstraction and translation**:

- Hide: class/function/variable names, implementation structure, programming-language concepts (unless inherently technical).
- Expose: JSON Schema field names (output contract), semantically meaningful type names, domain terms.
- Language: write in the task’s domain language (business/technical/creative), not code-execution terms.

**Completeness**:

- Self-contained: prompts alone must suffice; do not assume external context.
- Precision: clear task, explicit/obvious parameter meaning, unambiguous output requirements, placeholders understandable to runtime LLM.
- Schema precision: assess input schema; refine if generic/incomplete; include schema (SYSTEM or USER); choose presentation (schema/natural language/example) for clarity.
- Instantiability: use valid placeholders; map to actual parameters; template remains coherent after substitution.

**Critical prohibitions**:

1) Do not expose code structure.
2) Do not reproduce copyrighted content; summarize instead.
3) Do not use invalid placeholders.
4) Do not add unsupported assumptions.
5) Do not generate harmful content.

**Edge cases**:

- Conflicting/outdated info: prioritize types; note conflicts.
- Missing types: describe generally from names/usage.
- Ambiguous domain: use neutral language; avoid strong assumptions.
- Multi-language: translate to English; if an output language is specified, include that as a guideline in English.

**Quality self-check** (before finalizing):

- Role defined without exposing code structure
- Task focuses on intent, not implementation
- All parameters use valid placeholders
- Output schema included and correctly placed
- Schema sufficiently precise (refine if needed)
- Output requirements clear and match return spec
- Guidance targets execution, not formatting niceties
- No unsupported assumptions
- Ambiguities/conflicts/refinements noted in NOTES