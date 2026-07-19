import SwiftUI

// BACKLOG.md I3 — entered once, remembered locally. Reached via a gear button on the Ledger tab
// (no dedicated Settings tab exists in the confirmed 3-tab design).
struct ConnectionSettingsView: View {
    @ObservedObject var store: ConnectionSettingsStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Tailscale hostname", text: $store.host)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    TextField("Port", text: $store.port)
                        .keyboardType(.numberPad)
                } header: {
                    Text("Backend")
                } footer: {
                    Text("The VM's Tailscale hostname or IP, e.g. turnny-vm or 100.x.x.x. Requires the Tailscale app installed with VPN On Demand set to Always (ADR-0025) — Ledger doesn't manage that connection itself.")
                }

                Section("Status") {
                    statusRow
                }
            }
            .navigationTitle("Connection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        store.save()
                        dismiss()
                    }
                }
            }
            .task {
                if store.baseURL != nil {
                    await store.checkReachability()
                }
            }
        }
    }

    @ViewBuilder
    private var statusRow: some View {
        switch store.reachability {
        case .unknown:
            Button("Check connection") {
                Task { await store.checkReachability() }
            }
        case .checking:
            HStack {
                ProgressView()
                Text("Checking…")
            }
        case .reachable(let connected, let synced):
            Label(reachableDescription(connected: connected, synced: synced), systemImage: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .unreachable(let message):
            VStack(alignment: .leading, spacing: 4) {
                Label("Unreachable", systemImage: "xmark.circle.fill")
                    .foregroundStyle(.red)
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                Button("Try again") {
                    Task { await store.checkReachability() }
                }
            }
        }
    }

    private func reachableDescription(connected: Bool, synced: Bool) -> String {
        if !connected { return "Reachable — no Gmail account connected yet" }
        return synced ? "Reachable — synced" : "Reachable — connected, first sync pending"
    }
}

#Preview {
    ConnectionSettingsView(store: ConnectionSettingsStore())
}
