import SwiftUI

// BACKLOG.md J1 — every filter F1 exposes on the web (category, date range, amount range,
// method, type); free-text search lives in the main list view, not here. Plain functional
// controls for now — J2 is where this gets the debounced/chip-based polish from the confirmed
// design.
struct TransactionFilterSheet: View {
    @Binding var filters: TransactionFilters
    let categories: [Category]
    @Environment(\.dismiss) private var dismiss

    @State private var dateFromEnabled: Bool
    @State private var dateToEnabled: Bool
    @State private var dateFrom: Date
    @State private var dateTo: Date
    @State private var amountMinText: String
    @State private var amountMaxText: String
    @State private var selectedCategoryId: Int?
    @State private var selectedMethod: String?
    @State private var selectedType: String?

    init(filters: Binding<TransactionFilters>, categories: [Category]) {
        _filters = filters
        self.categories = categories
        let current = filters.wrappedValue
        _dateFromEnabled = State(initialValue: current.dateFrom != nil)
        _dateToEnabled = State(initialValue: current.dateTo != nil)
        _dateFrom = State(initialValue: WireDate.parse(current.dateFrom) ?? Date())
        _dateTo = State(initialValue: WireDate.parse(current.dateTo) ?? Date())
        _amountMinText = State(initialValue: current.amountMin ?? "")
        _amountMaxText = State(initialValue: current.amountMax ?? "")
        _selectedCategoryId = State(initialValue: current.categoryId)
        _selectedMethod = State(initialValue: current.paymentMethod)
        _selectedType = State(initialValue: current.txnType)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Category") {
                    Picker("Category", selection: $selectedCategoryId) {
                        Text("Any").tag(Int?.none)
                        ForEach(categories) { category in
                            Text(category.name).tag(Optional(category.id))
                        }
                    }
                    .pickerStyle(.menu)
                }

                Section("Type") {
                    Picker("Payment method", selection: $selectedMethod) {
                        Text("Any").tag(String?.none)
                        Text("UPI").tag(Optional("upi"))
                        Text("Credit card").tag(Optional("credit_card"))
                    }
                    .pickerStyle(.segmented)

                    Picker("Debit / Credit", selection: $selectedType) {
                        Text("Any").tag(String?.none)
                        Text("Debit").tag(Optional("debit"))
                        Text("Credit").tag(Optional("credit"))
                    }
                    .pickerStyle(.segmented)
                }

                Section("Date range") {
                    Toggle("From", isOn: $dateFromEnabled)
                    if dateFromEnabled {
                        DatePicker("Start date", selection: $dateFrom, displayedComponents: .date)
                            .labelsHidden()
                    }
                    Toggle("To", isOn: $dateToEnabled)
                    if dateToEnabled {
                        DatePicker("End date", selection: $dateTo, displayedComponents: .date)
                            .labelsHidden()
                    }
                }

                Section("Amount range (\u{20B9})") {
                    TextField("Min", text: $amountMinText)
                        .keyboardType(.decimalPad)
                    TextField("Max", text: $amountMaxText)
                        .keyboardType(.decimalPad)
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Clear all") {
                        filters = TransactionFilters()
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Apply") {
                        apply()
                        dismiss()
                    }
                }
            }
        }
    }

    private func apply() {
        filters.categoryId = selectedCategoryId
        filters.paymentMethod = selectedMethod
        filters.txnType = selectedType
        filters.dateFrom = dateFromEnabled ? WireDate.format(dateFrom) : nil
        filters.dateTo = dateToEnabled ? WireDate.format(dateTo) : nil
        filters.amountMin = amountMinText.isEmpty ? nil : amountMinText
        filters.amountMax = amountMaxText.isEmpty ? nil : amountMaxText
    }
}

#Preview {
    TransactionFilterSheet(filters: .constant(TransactionFilters()), categories: [
        Category(id: 1, name: "Food"), Category(id: 2, name: "Transport"),
    ])
}
