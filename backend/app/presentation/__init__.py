"""Presentation layer: the API Layer (REST/JSON endpoints) that any UI talks to.

May depend on: the application layer (use cases).
Must NOT depend on: infrastructure internals directly (e.g. must not import a repository or
the Gmail client itself — go through an application-layer use case instead).

This is the only layer a UI (the web dashboard, and later a mobile app) may call into.

See docs/ARCHITECTURE.md section 3 for the full layer-boundary rationale.
"""
