import SwiftUI

// BACKLOG.md M1 (COR-5, mirrors web H2) — a create-only escape hatch for a transaction with no
// corresponding email (e.g. cash). Deliberately a separate view from TransactionDetailView (which
// is fetch-and-edit shaped around an existing id) rather than a retrofit, matching H2's own
// precedent. No time field, matching J3's shape. Reached only via a toolbar "+" — never its own
// tab — so it stays the rare exception it's meant to be, not a primary workflow.
struct AddTransactionView: View {
    let categories: [Category]
    var onCreated: () -> Void = {}
    var onCategoryCreated: () -> Void = {}

    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @StateObject private var store = AddTransactionStore()
    @Environment(\.dismiss) private var dismiss

    @State private var amountText = ""
    @State private var date = Date()
    @State private var payeeName = ""
    @State private var categoryId: Int?
    @State private var paymentMethod = "upi"
    @State private var txnType = "debit"

    // "+ New category…" inline creation, same shape as TransactionDetailView's (BACKLOG.md J6).
    @State private var newlyCreatedCategories: [Category] = []
    @State private var showingNewCategoryAlert = false
    @State private var newCategoryName = ""
    private static let newCategorySentinel = -1

    private var pickerCategories: [Category] {
        let existingIds = Set(categories.map(\.id))
        return categories + newlyCreatedCategories.filter { !existingIds.contains($0.id) }
    }

    private var canSave: Bool {
        !amountText.trimmingCharacters(in: .whitespaces).isEmpty
            && !payeeName.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Label(
                        "Manually added — no source email. Use this only for the rare transaction with nothing in your inbox (e.g. cash), not as a regular habit.",
                        systemImage: "info.circle"
                    )
                    .font(.footnote)
                    .foregroundStyle(.secondary)
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
                        .textInputAutocapitalization(.words)
                    Picker("Category", selection: $categoryId) {
                        Text("Uncategorized").tag(Int?.none)
                        ForEach(pickerCategories) { category in
                            Text(category.name).tag(Optional(category.id))
                        }
                        Text("+ New category…").tag(Optional(Self.newCategorySentinel))
                    }
                    .onChange(of: categoryId) { oldValue, newValue in
                        if newValue == Self.newCategorySentinel {
                            categoryId = oldValue
                            showingNewCategoryAlert = true
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

                if let errorMessage = store.errorMessage {
                    Section {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Add Transaction")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }
                        .disabled(!canSave || store.isSaving)
                }
            }
            .alert("New category", isPresented: $showingNewCategoryAlert) {
                TextField("Name", text: $newCategoryName)
                Button("Create") { Task { await createInlineCategory() } }
                Button("Cancel", role: .cancel) { newCategoryName = "" }
            }
        }
    }

    private func save() async {
        let request = ManualTransactionRequest(
            amount: amountText.trimmingCharacters(in: .whitespaces),
            txnDate: WireDate.format(date),
            payeeName: payeeName.trimmingCharacters(in: .whitespaces),
            paymentMethod: paymentMethod,
            txnType: txnType,
            categoryId: categoryId
        )
        if await store.save(baseURL: connectionSettings.baseURL, request: request) {
            onCreated()
            dismiss()
        }
    }

    private func createInlineCategory() async {
        let name = newCategoryName.trimmingCharacters(in: .whitespaces)
        newCategoryName = ""
        guard !name.isEmpty else { return }
        if let created = await store.createCategory(baseURL: connectionSettings.baseURL, name: name) {
            newlyCreatedCategories.append(created)
            categoryId = created.id
            onCategoryCreated()
        }
    }
}

#Preview {
    AddTransactionView(categories: [Category(id: 1, name: "Food")])
        .environmentObject(ConnectionSettingsStore())
}
