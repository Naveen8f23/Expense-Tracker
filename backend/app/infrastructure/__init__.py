"""Infrastructure layer: concrete implementations of application/domain-defined interfaces.

Examples: GmailClient (Gmail OAuth + History API), the SQLAlchemy-based repositories,
AIFallbackClient (rare-case AI extraction).

May depend on: the application and domain layers (to implement their interfaces).
Must NOT be depended on directly by the domain layer, and should only be reached by the
application layer through an interface it defines — never hardcode a specific infrastructure
choice (e.g. "Gmail", "SQLite") into domain or application code.

See docs/ARCHITECTURE.md section 3 for the full layer-boundary rationale.
"""
