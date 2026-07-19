import SwiftUI

// Skeleton for BACKLOG.md Epic K (needs-review queue). No networking yet — see I2/K1.
struct ReviewView: View {
    var body: some View {
        NavigationStack {
            Text("Review")
                .navigationTitle("Review")
        }
    }
}

#Preview {
    ReviewView()
}
