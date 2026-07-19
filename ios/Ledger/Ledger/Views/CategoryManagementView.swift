import SwiftUI

// BACKLOG.md J6 — full category CRUD (mirrors web E6/F5), reached from the gear-icon toolbar
// alongside Connection Settings (same one-tap-deeper pattern I3 established). Inline "+ New
// category" creation from J3's picker is a separate, smaller flow — this screen is for
// list/rename/delete, including the reassign-on-delete flow when a category is in use.
struct CategoryManagementView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @ObservedObject var store: CategoryManagementStore
    @Environment(\.dismiss) private var dismiss

    @State private var newCategoryName = ""
    // `showingRenameAlert` and `categoryBeingRenamed` are deliberately separate state (not one
    // derived from the other's non-nil-ness): tapping the alert's "Save" dismisses the alert —
    // which, if `isPresented` were `categoryBeingRenamed != nil`, would nil it out as a side
    // effect of dismissal *before* the async `performRename()` task actually runs, silently
    // no-op'ing the rename. Keeping them independent means `categoryBeingRenamed` is still valid
    // when `performRename()` reads it.
    @State private var showingRenameAlert = false
    @State private var categoryBeingRenamed: Category?
    @State private var renameText = ""

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Categories")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { dismiss() }
                    }
                }
                .task { await store.load(baseURL: connectionSettings.baseURL) }
                .alert("Rename category", isPresented: $showingRenameAlert) {
                    TextField("Name", text: $renameText)
                    Button("Save") { Task { await performRename() } }
                    Button("Cancel", role: .cancel) {}
                }
                .sheet(item: Binding(
                    get: { store.pendingReassignment },
                    set: { if $0 == nil { store.cancelReassignment() } }
                )) { pending in
                    ReassignmentSheet(
                        pending: pending,
                        otherCategories: store.categories.filter { $0.id != pending.id },
                        onReassign: { targetId in
                            await store.confirmReassignmentAndDelete(baseURL: connectionSettings.baseURL, reassignTo: targetId)
                        },
                        onCancel: { store.cancelReassignment() }
                    )
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        List {
            Section {
                HStack {
                    TextField("New category name", text: $newCategoryName)
                        .textInputAutocapitalization(.words)
                    Button("Add") { Task { await addCategory() } }
                        .disabled(newCategoryName.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }

            if let errorMessage = store.errorMessage {
                Section {
                    Text(errorMessage).foregroundStyle(.red)
                }
            }

            Section {
                if store.isLoading && store.categories.isEmpty {
                    ProgressView()
                } else if store.categories.isEmpty {
                    Text("No categories yet").foregroundStyle(.secondary)
                } else {
                    ForEach(store.categories) { category in
                        Text(category.name)
                            .swipeActions(edge: .trailing) {
                                Button(role: .destructive) {
                                    Task { await store.deleteCategory(baseURL: connectionSettings.baseURL, id: category.id) }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                                Button {
                                    categoryBeingRenamed = category
                                    renameText = category.name
                                    showingRenameAlert = true
                                } label: {
                                    Label("Rename", systemImage: "pencil")
                                }
                                .tint(.blue)
                            }
                    }
                }
            }
        }
    }

    private func addCategory() async {
        let name = newCategoryName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        if await store.createCategory(baseURL: connectionSettings.baseURL, name: name) {
            newCategoryName = ""
        }
    }

    private func performRename() async {
        guard let category = categoryBeingRenamed else { return }
        let name = renameText.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        await store.renameCategory(baseURL: connectionSettings.baseURL, id: category.id, name: name)
    }
}

/// BACKLOG.md J6's reassign-on-delete flow — shown instead of a dead-end error when the backend's
/// `DELETE /categories/{id}` 409s because the category is still in use (E6). Picking a target
/// retries the delete with `reassign_to` set; there's no "just delete anyway" option, matching the
/// backend's own contract (a category in use can only be deleted by reassigning its transactions).
private struct ReassignmentSheet: View {
    let pending: CategoryManagementStore.PendingReassignment
    let otherCategories: [Category]
    /// `async` and awaited before `dismiss()` below — dismissing this sheet clears
    /// `store.pendingReassignment` as a side effect (see the parent's `sheet(item:)` binding), so
    /// dismissing first would race the store's own read of it during the actual reassign-and-delete
    /// call. Awaiting keeps the store's state valid for the whole duration of the call.
    let onReassign: (Int) async -> Void
    let onCancel: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text("\"\(pending.name)\" is used by \(pending.transactionCount) transaction\(pending.transactionCount == 1 ? "" : "s"). Choose a category to move them to before deleting.")
                        .foregroundStyle(.secondary)
                }
                if otherCategories.isEmpty {
                    Section {
                        Text("Create another category first — there's nothing to reassign to yet.")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Section {
                        ForEach(otherCategories) { category in
                            Button(category.name) {
                                Task {
                                    await onReassign(category.id)
                                    dismiss()
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Reassign & Delete")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        onCancel()
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    CategoryManagementView(store: CategoryManagementStore())
        .environmentObject(ConnectionSettingsStore())
}
