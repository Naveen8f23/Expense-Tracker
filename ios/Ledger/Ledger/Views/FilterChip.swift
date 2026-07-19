import SwiftUI

/// One removable "active filter" pill (BACKLOG.md J2, mirrors web G1).
struct FilterChip: View {
    let label: String
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.caption)
            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .font(.caption)
            }
            .accessibilityLabel("Remove \(label) filter")
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Color.accentColor.opacity(0.15))
        .foregroundStyle(Color.accentColor)
        .clipShape(Capsule())
    }
}

#Preview {
    HStack {
        FilterChip(label: "Payee: Cafe", onRemove: {})
        FilterChip(label: "UPI", onRemove: {})
    }
    .padding()
}
