import SwiftUI

// BACKLOG.md J4 (mirrors web F3, TRC-2). The email content is untrusted external HTML (a real
// bank email, ADR-0006) — rendered here as plain text only. Unlike the web dashboard, which had
// to deliberately avoid `dangerouslySetInnerHTML` to prevent a stored-XSS vector, SwiftUI's
// `Text` never interprets its string as markup in the first place, so this view is safe by
// construction as long as nothing here reaches for an HTML-parsing API
// (`NSAttributedString(data:options:[.documentType: .html])` or a `WKWebView`) — don't add either.
struct SourceEmailView: View {
    let email: EmailMessage

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

                Text(email.content)
                    .font(.system(.footnote, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding()
        }
        .navigationTitle("Source Email")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        SourceEmailView(email: EmailMessage(
            id: 1, messageId: "18abc", receivedAt: "2026-07-19T14:32:10",
            status: "matched", classifiedPatternId: "hdfc_upi_debit_v1",
            content: "Dear Customer,\n\nRs.120.00 is debited from your account ending 4958..."
        ))
    }
}
