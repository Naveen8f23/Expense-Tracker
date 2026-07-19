import SwiftUI

// BACKLOG.md J1 (list, non-text filters) + J2 (debounced text search, removable chips, mirrors
// web G1). "Payee contains" lives here, not J1's filter sheet — matching the web dashboard, where
// it's a distinct debounced field alongside free-text search, not a sheet-only picker.
struct LedgerListView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @StateObject private var store = TransactionListStore()
    @State private var filters = TransactionFilters()
    @State private var searchText = ""
    @State private var payeeText = ""
    @State private var showingSettings = false
    @State private var showingFilters = false
    @State private var selectedTransaction: Transaction?
    @State private var debounceTask: Task<Void, Never>?

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Ledger")
                .searchable(text: $searchText, prompt: "Search payee or category")
                .onSubmit(of: .search) { Task { await reload() } }
                .onChange(of: searchText) { _, _ in scheduleDebouncedReload() }
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            showingFilters = true
                        } label: {
                            Image(systemName: "line.3.horizontal.decrease.circle")
                        }
                        .accessibilityLabel("Filters")
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            showingSettings = true
                        } label: {
                            Image(systemName: "gearshape")
                        }
                        .accessibilityLabel("Connection settings")
                    }
                }
                .sheet(isPresented: $showingSettings) {
                    ConnectionSettingsView(store: connectionSettings)
                }
                .sheet(isPresented: $showingFilters, onDismiss: { Task { await reload() } }) {
                    TransactionFilterSheet(filters: $filters, categories: store.categories)
                }
                .sheet(item: $selectedTransaction) { transaction in
                    TransactionDetailView(
                        transactionId: transaction.id,
                        categories: store.categories,
                        onChanged: { Task { await reload() } }
                    )
                }
                .task { await reload() }
                .refreshable { await reload() }
        }
    }

    @ViewBuilder
    private var content: some View {
        VStack(spacing: 0) {
            payeeField
            chipsRow
            listOrEmptyState
        }
    }

    private var payeeField: some View {
        HStack {
            Image(systemName: "person")
                .foregroundStyle(.secondary)
            TextField("Payee contains…", text: $payeeText)
                .textInputAutocapitalization(.words)
            if !payeeText.isEmpty {
                Button {
                    payeeText = ""
                    scheduleDebouncedReload()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .accessibilityLabel("Clear payee filter")
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .onChange(of: payeeText) { _, _ in scheduleDebouncedReload() }
    }

    @ViewBuilder
    private var chipsRow: some View {
        let chips = activeChips
        if !chips.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(chips) { chip in
                        FilterChip(label: chip.label, onRemove: chip.onRemove)
                    }
                    Button("Clear all") { clearAll() }
                        .font(.caption)
                        .buttonStyle(.borderless)
                }
                .padding(.horizontal, 16)
            }
            .padding(.bottom, 8)
        }
    }

    @ViewBuilder
    private var listOrEmptyState: some View {
        if let errorMessage = store.errorMessage, store.transactions.isEmpty {
            ContentUnavailableView {
                Label("Couldn't load transactions", systemImage: "wifi.slash")
            } description: {
                Text(errorMessage)
            } actions: {
                Button("Try again") { Task { await reload() } }
            }
        } else if store.transactions.isEmpty && !store.isLoading {
            ContentUnavailableView("No transactions", systemImage: "tray")
        } else {
            List {
                ForEach(store.transactions) { transaction in
                    Button {
                        selectedTransaction = transaction
                    } label: {
                        TransactionRowView(transaction: transaction)
                    }
                    .buttonStyle(.plain)
                }
                if store.hasMore {
                    HStack {
                        Spacer()
                        if store.isLoadingMore {
                            ProgressView()
                        } else {
                            Button("Load more") { Task { await loadMore() } }
                        }
                        Spacer()
                    }
                }
            }
            .listStyle(.plain)
        }
    }

    // MARK: - Chips

    private struct Chip: Identifiable {
        let id: String
        let label: String
        let onRemove: () -> Void
    }

    private var activeChips: [Chip] {
        var chips: [Chip] = []
        if !searchText.isEmpty {
            chips.append(Chip(id: "q", label: "Search: \(searchText)") { searchText = ""; Task { await reload() } })
        }
        if !payeeText.isEmpty {
            chips.append(Chip(id: "payee", label: "Payee: \(payeeText)") { payeeText = ""; Task { await reload() } })
        }
        if let categoryId = filters.categoryId {
            let name = store.categories.first(where: { $0.id == categoryId })?.name ?? "Category"
            chips.append(Chip(id: "category", label: name) { filters.categoryId = nil; Task { await reload() } })
        }
        if let method = filters.paymentMethod {
            chips.append(Chip(id: "method", label: method == "upi" ? "UPI" : "Credit card") {
                filters.paymentMethod = nil; Task { await reload() }
            })
        }
        if let type = filters.txnType {
            chips.append(Chip(id: "type", label: type == "debit" ? "Debit" : "Credit") {
                filters.txnType = nil; Task { await reload() }
            })
        }
        if let dateFrom = filters.dateFrom {
            chips.append(Chip(id: "dateFrom", label: "From \(dateFrom)") { filters.dateFrom = nil; Task { await reload() } })
        }
        if let dateTo = filters.dateTo {
            chips.append(Chip(id: "dateTo", label: "To \(dateTo)") { filters.dateTo = nil; Task { await reload() } })
        }
        if let amountMin = filters.amountMin {
            chips.append(Chip(id: "amountMin", label: "Min \u{20B9}\(amountMin)") { filters.amountMin = nil; Task { await reload() } })
        }
        if let amountMax = filters.amountMax {
            chips.append(Chip(id: "amountMax", label: "Max \u{20B9}\(amountMax)") { filters.amountMax = nil; Task { await reload() } })
        }
        return chips
    }

    private func clearAll() {
        searchText = ""
        payeeText = ""
        filters = TransactionFilters()
        Task { await reload() }
    }

    // MARK: - Data

    private func currentFilters() -> TransactionFilters {
        var effective = filters
        effective.q = searchText.isEmpty ? nil : searchText
        effective.payee = payeeText.isEmpty ? nil : payeeText
        return effective
    }

    /// ~400ms debounce (BACKLOG.md J2, mirrors web G1) — cancels any pending reload and schedules
    /// a fresh one, so typing doesn't fire a request per keystroke.
    private func scheduleDebouncedReload() {
        debounceTask?.cancel()
        debounceTask = Task {
            try? await Task.sleep(nanoseconds: 400_000_000)
            guard !Task.isCancelled else { return }
            await reload()
        }
    }

    private func reload() async {
        await store.load(baseURL: connectionSettings.baseURL, filters: currentFilters())
    }

    private func loadMore() async {
        await store.loadMore(baseURL: connectionSettings.baseURL, filters: currentFilters())
    }
}

#Preview {
    LedgerListView()
        .environmentObject(ConnectionSettingsStore())
}
