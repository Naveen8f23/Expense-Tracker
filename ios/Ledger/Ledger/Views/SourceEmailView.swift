import SwiftUI

// BACKLOG.md J4 (mirrors web F3, TRC-2). The email content is untrusted external HTML (a real
// bank email, ADR-0006). Unlike the web dashboard, which had to deliberately avoid
// `dangerouslySetInnerHTML` to prevent a stored-XSS vector, SwiftUI's `Text` never interprets its
// string as markup in the first place, so this view is safe by construction as long as nothing
// here reaches for an HTML-parsing/-rendering API (`NSAttributedString(data:options:
// [.documentType: .html])` or a `WKWebView`) — don't add either. `ReadableEmailContent` only ever
// does plain string transforms (tag/entity stripping), never interprets the markup, so displaying
// its output here keeps that same safety property while actually being readable — the raw source
// used to render as literal `<html><body>...<b>120.00</b>...` tags.
struct SourceEmailView: View {
    let email: EmailMessage
    /// Only set when reached from the Review tab's unmatched-email list (BACKLOG.md K2) — `nil`
    /// for `TransactionDetailView`'s "View source email" case, where there's nothing to ignore.
    /// Returns whether the ignore actually succeeded, so this view only dismisses on success —
    /// a failure still surfaces via the parent `ReviewView`'s existing alert either way.
    var onIgnore: (() async -> Bool)? = nil
    @Environment(\.dismiss) private var dismiss
    @State private var isIgnoring = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    LabeledContent("Received", value: email.receivedAt)
                    LabeledContent("Status", value: email.status)
                }
                .font(.footnote)
                .foregroundStyle(.secondary)

                Divider()

                Text(ReadableEmailContent.string(from: email.content))
                    .font(.footnote)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding()
        }
        .navigationTitle("Source Email")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let onIgnore {
                ToolbarItem(placement: .primaryAction) {
                    Button(role: .destructive) {
                        Task {
                            isIgnoring = true
                            if await onIgnore() { dismiss() }
                            isIgnoring = false
                        }
                    } label: {
                        if isIgnoring {
                            ProgressView()
                        } else {
                            Label("Ignore", systemImage: "xmark.circle")
                        }
                    }
                    .disabled(isIgnoring)
                }
            }
        }
    }
}

#Preview {
    NavigationStack {
        SourceEmailView(email: EmailMessage(
            id: 1, messageId: "18abc", receivedAt: "2026-07-19T14:32:10",
            status: "matched", classifiedPatternId: "hdfc_upi_debit_v1",
            content: "Dear Customer,<br>Rs.<b>120.00</b> is debited from your account ending 4958..."
        ), onIgnore: { true })
    }
}
