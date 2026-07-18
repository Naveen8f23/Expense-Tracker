"""Application layer: use case orchestration (SyncGmailAccount, ClassifyAndExtractEmail, etc.).

May depend on: the domain layer.
Must NOT depend on: the presentation layer (API/UI), or infrastructure internals directly —
only on infrastructure interfaces defined here or in the domain layer.

See docs/ARCHITECTURE.md section 3 for the full layer-boundary rationale.
"""
