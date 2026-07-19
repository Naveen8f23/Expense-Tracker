import SwiftUI

// BACKLOG.md J3 — every E3-editable field (amount, date, payee, category, method, type) plus
// "Not a real expense" (COR-4). No time field, matching H2's own web precedent. Category
// assignment is a manual picker only — no auto-suggestion (REQUIREMENTS.md MOB-3). J4 added the
// "View source email" disclosure below.
struct TransactionDetailView: View {
    let transactionId: Int
    let categories: [Category]
    var onChanged: () -> Void = {}

    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @StateObject private var store = TransactionDetailStore()
    @Environment(\.dismiss) private var dismiss

    @State private var amountText = ""
    @State private var date = Date()
    @State private var payeeName = ""
    @State private var categoryId: Int?
    @State private var paymentMethod = "upi"
    @State private var txnType = "debit"
    @State private var showingDismissConfirm = false
    @State private var formPopulated = false

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Transaction")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { dismiss() }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save") { Task { await save() } }
                            .disabled(store.transaction == nil || store.isSaving)
                    }
                }
                .confirmationDialog(
                    "Mark as not a real expense?",
                    isPresented: $showingDismissConfirm,
                    titleVisibility: .visible
                ) {
                    Button("Not a real expense", role: .destructive) { Task { await performDismiss() } }
                    Button("Cancel", role: .cancel) {}
                } message: {
                    Text("This keeps the transaction and its history, but excludes it from search and analytics.")
                }
                .task {
                    await store.load(baseURL: connectionSettings.baseURL, id: transactionId)
                    populateFormIfNeeded()
                }
                .onChange(of: store.transaction) { _, _ in populateFormIfNeeded() }
        }
    }

    @ViewBuilder
    private var content: some View {
        if let transaction = store.transaction {
            Form {
                if transaction.dismissed {
                    Section {
                        Label("Dismissed — not counted as a real expense", systemImage: "eye.slash")
                            .foregroundStyle(.secondary)
                    }
                }

                Section("Details") {
                    HStack {
                        Text("Amount")
                        Spacer()
                        TextField("Amount", text: $amountText)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                    DatePicker("Date", selection: $date, displayedComponents: .date)
                    TextField("Payee", text: $payeeName)
                    Picker("Category", selection: $categoryId) {
                        Text("Uncategorized").tag(Int?.none)
                        ForEach(categories) { category in
                            Text(category.name).tag(Optional(category.id))
                        }
                    }
                }

                Section("Type") {
                    Picker("Payment method", selection: $paymentMethod) {
                        Text("UPI").tag("upi")
                        Text("Credit card").tag("credit_card")
                    }
                    .pickerStyle(.segmented)

                    Picker("Debit / Credit", selection: $txnType) {
                        Text("Debit").tag("debit")
                        Text("Credit").tag("credit")
                    }
                    .pickerStyle(.segmented)
                }

                if let sourceEmail = transaction.sourceEmail {
                    Section {
                        NavigationLink {
                            SourceEmailView(email: sourceEmail)
                        } label: {
                            Label("View source email", systemImage: "envelope")
                        }
                    }
                } else if transaction.emailMessageId == nil {
                    Section {
                        Label("Manually added — no source email", systemImage: "square.and.pencil")
                            .foregroundStyle(.secondary)
                    }
                }

                if let errorMessage = store.errorMessage {
                    Section {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }

                Section {
                    Button("Not a real expense", role: .destructive) {
                        showingDismissConfirm = true
                    }
                    .disabled(transaction.dismissed || store.isSaving)
                }
            }
        } else if let errorMessage = store.errorMessage {
            ContentUnavailableView {
                Label("Couldn't load transaction", systemImage: "wifi.slash")
            } description: {
                Text(errorMessage)
            }
        } else {
            // Covers both `store.isLoading == true` and the brief window before `.task` even
            // starts (transaction nil, isLoading still false, errorMessage still nil) — without
            // this branch as the catch-all, that window rendered nothing at all.
            ProgressView()
        }
    }

    private func populateFormIfNeeded() {
        guard !formPopulated, let transaction = store.transaction else { return }
        amountText = transaction.amount
        date = WireDate.parse(transaction.txnDate) ?? Date()
        payeeName = transaction.payee.name
        categoryId = transaction.categoryId
        paymentMethod = transaction.paymentMethod
        txnType = transaction.txnType
        formPopulated = true
    }

    private func save() async {
        var correction = TransactionCorrectionRequest()
        correction.amount = amountText
        correction.txnDate = WireDate.format(date)
        correction.payeeName = payeeName
        // Picking "Uncategorized" can't actually clear an existing category — the backend's PATCH
        // endpoint has no way to explicitly null a field, only to leave it unchanged (see
        // Networking/APIClient.swift's ground-truth note on TransactionCorrectionRequest). Only
        // send categoryId when a real category is selected.
        if let categoryId { correction.categoryId = categoryId }
        correction.paymentMethod = paymentMethod
        correction.txnType = txnType

        if await store.save(baseURL: connectionSettings.baseURL, correction: correction) {
            onChanged()
            dismiss()
        }
    }

    private func performDismiss() async {
        if await store.dismissTransaction(baseURL: connectionSettings.baseURL) {
            onChanged()
            dismiss()
        }
    }
}

#Preview {
    TransactionDetailView(transactionId: 1, categories: [Category(id: 1, name: "Food")])
        .environmentObject(ConnectionSettingsStore())
}
