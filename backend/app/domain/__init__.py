"""Domain layer: core business rules (Transaction, Payee, Category, dedup, correction).

May depend on: nothing else in this project (pure Python only).
Must NOT depend on: Gmail API, the database engine, FastAPI, or any other framework/library.

See docs/ARCHITECTURE.md section 3 for the full layer-boundary rationale.
"""
