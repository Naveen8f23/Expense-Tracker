import SwiftUI

// BACKLOG.md J7 — tapping the nav-bar sync-health dot shows the same scanned/matched/skipped/
// failed counts GET /sync/status already returns (B5/E7), instead of the dot being the only signal.
struct SyncHealthView: View {
    @ObservedObject var store: SyncHealthStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Sync Health")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { dismiss() }
                    }
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        List {
            switch store.health {
            case .notConnected:
                Section {
                    Label("No Gmail account connected yet", systemImage: "envelope.badge")
                        .foregroundStyle(.secondary)
                }
            case .unknown:
                Section {
                    Text(store.errorMessage ?? "Checking sync status…")
                        .foregroundStyle(store.errorMessage == nil ? Color.secondary : Color.red)
                }
            case .pendingFirstSync, .healthy, .issues:
                if let status = store.status {
                    statusSections(status)
                }
            }
        }
    }

    @ViewBuilder
    private func statusSections(_ status: SyncStatus) -> some View {
        Section("Last sync") {
            LabeledContent("Scanned", value: "\(status.lastScanned ?? 0)")
            LabeledContent("Matched", value: "\(status.lastMatched ?? 0)")
            LabeledContent("Skipped", value: "\(status.lastSkipped ?? 0)")
            LabeledContent("Failed", value: "\(status.lastFailed ?? 0)")
        }
        if let lastSyncAt = status.lastSyncAt {
            Section("Last synced") {
                Text(lastSyncAt)
            }
        } else {
            Section {
                Text("Connected — first sync pending").foregroundStyle(.secondary)
            }
        }
        if let lastError = status.lastError {
            Section("Last error") {
                Text(lastError).foregroundStyle(.red)
            }
        }
    }
}

#Preview {
    SyncHealthView(store: SyncHealthStore())
}
