# Constitution

This document is the governing set of engineering principles for this project. It outranks
convenience, speed, and stylistic preference. When any instruction — including one from the
user in a single conversation — conflicts with a principle here, surface the conflict and
resolve it explicitly (see "Conflict Resolution") rather than silently picking one side.

**Read this document before every significant task.** A significant task is anything that adds
or changes behavior, introduces a dependency, changes a public interface, or touches more than
one module. Trivial fixes (typos, formatting, comments) don't require a re-read, but when in
doubt, read it.

## Core Principles

1. **Maintainability over cleverness.** Code is read far more often than it is written. A
   slightly longer, obvious solution beats a compact, clever one. If you have to explain a
   trick in a comment, prefer removing the trick instead.

2. **Simplicity over unnecessary abstraction.** Do not build for hypothetical future
   requirements. Add an abstraction (interface, plugin system, config layer) only when there
   are at least two concrete, current use cases that need it. Three similar lines of code are
   better than a premature abstraction.

3. **Justify every dependency.** Never add a framework, library, or service dependency without
   writing down why in [DECISIONS.md](DECISIONS.md): what problem it solves, what the cost is
   (bundle size, maintenance burden, security surface, license), and what the alternative of
   not adding it would look like. Prefer the standard library and code you already depend on.

4. **Design for long-term maintainability.** Optimize for the person who maintains this code in
   two years with no memory of today's context. Prefer explicit over implicit, boring over
   novel, and documented over assumed.

5. **Clean architecture and separation of concerns.** Keep domain/business logic independent of
   frameworks, UI, and I/O (database, filesystem, network). Dependencies should point inward:
   infrastructure depends on domain, not the reverse. See [ARCHITECTURE.md](ARCHITECTURE.md)
   for how this is applied concretely.

6. **Self-explanatory code with meaningful names.** Names should say what something is or does
   without needing a comment. Avoid abbreviations, single-letter variables (outside tight local
   scopes like loop indices), and names that lie about behavior.

7. **Avoid duplication whenever practical** (DRY, applied with judgment). Duplication that
   exists because two things coincidentally look alike today — but are conceptually
   unrelated and may diverge — is preferable to a shared abstraction that couples them
   artificially. Prefer duplication over the wrong abstraction.

8. **Loose coupling, high cohesion.** Modules should know as little as possible about each
   other's internals and should communicate through narrow, well-defined interfaces. Related
   behavior and data should live together.

9. **Deterministic solutions over AI, when sufficient.** If a problem can be solved reliably
   with plain code (validation, parsing, arithmetic, rule-based logic), do that instead of
   calling an LLM. Reserve AI/LLM usage for problems that are genuinely ambiguous, generative,
   or language-based and that deterministic code cannot reasonably solve.

10. **Isolate AI behind well-defined interfaces.** When AI is used, wrap it behind an
    interface/module boundary (e.g., a `SuggestionService` or `Classifier` interface) so the
    rest of the system does not know or care whether the implementation is a model call, a
    rule engine, or a stub in tests. This keeps the system testable and lets the AI component
    be swapped, mocked, or removed without a wider rewrite.

11. **Record every significant architectural decision in [DECISIONS.md](DECISIONS.md).**
    "Significant" includes: choice of framework/library, storage/persistence model, module
    boundaries, API contracts, authentication/authorization approach, and anything that would
    be expensive to reverse. When in doubt, record it — a short entry costs little.

12. **Documentation evolves with the code.** A change that alters architecture, requirements,
    or a prior decision must update the relevant doc(s) under `/docs` in the same change, not
    as a follow-up. Stale documentation is treated as a bug.

13. **Never silently change existing architecture.** If a change requires deviating from a
    documented architecture or a recorded decision, that deviation must be called out
    explicitly, discussed, and recorded as a new decision (with the old one marked
    superseded) — never introduced quietly as a side effect of an unrelated task.

14. **Surface conflicts with prior decisions instead of resolving them unilaterally.** If a
    requested change conflicts with something in [DECISIONS.md](DECISIONS.md),
    [ARCHITECTURE.md](ARCHITECTURE.md), or this document, stop and explain the conflict — with
    the specific prior decision and why the new request contradicts it — before writing code.

15. **Think through edge cases before writing code.** Identify empty/null inputs, boundary
    values, concurrency, failure of external calls, and invalid states before implementation,
    not after a bug report.

16. **Correctness first, performance second.** Write the correct, clear solution first. Only
    optimize when there is a demonstrated performance problem (a measurement, not a guess), and
    record the tradeoff if the optimization sacrifices clarity.

17. **Small, focused commits.** Each commit should represent one coherent change with a clear
    reason. Avoid bundling unrelated fixes, refactors, and features together.

18. **Test important business logic.** Code that encodes domain rules (calculations,
    validations, state transitions, money handling) must have tests that would fail if the
    rule were broken. Tests are not required for trivial glue code, but are required for
    anything a bug in would silently produce wrong financial data.

19. **Never guess on ambiguous requirements — ask.** If a requirement is unclear, underspecified,
    or could reasonably be interpreted more than one way, ask a clarifying question instead of
    picking an interpretation and proceeding. Encode the answer in
    [REQUIREMENTS.md](REQUIREMENTS.md) once resolved.

20. **When multiple good approaches exist, present tradeoffs before implementing.** Name the
    realistic options, state the tradeoffs (complexity, cost, flexibility, time), recommend
    one, and get agreement before writing code — for any decision significant enough to
    warrant an entry in DECISIONS.md.

## Additional Principles

21. **Fail loudly, not silently.** Prefer explicit errors over swallowed exceptions, silent
    fallbacks, or default values that mask a real problem. If a fallback is intentional,
    document why.

22. **Validate at the boundary.** Validate and sanitize external input (user input, API
    responses, file imports) at the edge of the system. Once data is inside the domain layer,
    trust its shape and stop re-validating defensively.

23. **No hidden side effects.** A function that reads data shouldn't also write it, and vice
    versa, unless its name says so. Side effects should be obvious from the call site.

24. **Security is not optional.** Never store secrets in source control. Treat all user input
    (including CSV/OFX imports and file uploads) as untrusted. Follow least-privilege for any
    credentials or tokens the app uses.

25. **Reversibility matters.** Prefer designs and migrations that can be rolled back. Irreversible
    operations (data-destructive migrations, deleting historical records) require explicit
    sign-off and a recorded decision.

26. **One source of truth per fact.** Avoid storing the same piece of data (e.g., a computed
    total) in two places that can drift out of sync. Derive, don't duplicate, unless a
    recorded decision justifies caching/denormalization for performance.

## Conflict Resolution

When a new request conflicts with a principle in this document or a decision in
[DECISIONS.md](DECISIONS.md):

1. Stop before implementing.
2. State the conflict explicitly: which principle/decision, and how the new request
   contradicts it.
3. Present options and tradeoffs if more than one resolution is reasonable.
4. Wait for a decision from the user.
5. Record the outcome in [DECISIONS.md](DECISIONS.md), including if a prior decision is being
   superseded.

## Amending This Document

This constitution itself can change, but a change to it is a significant decision: it must be
discussed, justified, and recorded in [DECISIONS.md](DECISIONS.md) like any other architectural
decision.
