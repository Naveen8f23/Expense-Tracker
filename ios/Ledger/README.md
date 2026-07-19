# Ledger (iOS)

Native Swift + SwiftUI companion app for the expense tracker backend (ADR-0023). Presentation-only
— no business logic lives here; every screen reads/writes through the existing FastAPI backend
(`../../backend`) over the owner's Tailscale network (ADR-0002, ADR-0020, ADR-0025).

## Folder layout and dependency direction

Mirrors the discipline `frontend/src/api/client.ts` already follows for the web dashboard: no
view ever talks to the network directly.

- `Ledger/App/` — app entry point (`LedgerApp.swift`). No business logic.
- `Ledger/Views/` — SwiftUI views. May depend on `ViewState`, may **not** import networking types
  or call the API client directly.
- `Ledger/ViewState/` — observable view-state/view-models. May depend on `Networking`. This is the
  only layer allowed to call into `Networking`.
- `Ledger/Networking/` — the API client module wrapping every backend endpoint (added in I2). Must
  **not** import SwiftUI — it has no knowledge of how its data is displayed.

## Project generation

The `.xcodeproj` is generated from [`project.yml`](project.yml) via
[XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`) rather than hand-edited
— regenerate after changing `project.yml` or adding/removing files:

```sh
cd ios/Ledger
xcodegen generate
```

The generated `Ledger.xcodeproj` itself is not checked into git (see `.gitignore`) — it's
reproducible from `project.yml` plus the source files, the same reasoning as not committing
`node_modules` or `__pycache__`.

## Running

Open `Ledger.xcodeproj` in Xcode, select your own Apple ID under Signing & Capabilities
(`CODE_SIGN_STYLE: Automatic`, no paid Developer Program needed — ADR-0024), connect your iPhone,
and Run. The free-signing provisioning profile expires roughly every 7 days and needs a
reconnect-and-rebuild — an accepted, recurring cost of this distribution path, not a bug.
