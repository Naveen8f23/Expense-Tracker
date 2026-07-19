import XCTest

/// Not a BACKLOG.md story test — a one-off walkthrough that drives the real app via Xcode's
/// UI-testing runner (works without the macOS Accessibility/System Events permission this
/// environment lacks) and saves a screenshot at each step directly to disk, since the simulator
/// process can write to the host filesystem like any other macOS process.
final class LedgerDemoUITests: XCTestCase {
    private let outputDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/8133110a-2255-411c-9f65-022fa385da92/scratchpad"

    func testJ4SourceEmailViewer() throws {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))

        // A real synced transaction (has a source email), not a manual one — NAVEEN V rows are
        // real UPI entries from earlier epic verification.
        let row = app.staticTexts["NAVEEN V"].firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        row.tap()

        XCTAssertTrue(app.navigationBars["Transaction"].waitForExistence(timeout: 5))
        Thread.sleep(forTimeInterval: 1) // let GET /transactions/{id} resolve with source_email

        let viewSourceEmail = app.buttons["View source email"]
        XCTAssertTrue(viewSourceEmail.waitForExistence(timeout: 3))
        capture(app, "demo_j4_01_detail_with_disclosure")

        viewSourceEmail.tap()
        XCTAssertTrue(app.navigationBars["Source Email"].waitForExistence(timeout: 3))
        Thread.sleep(forTimeInterval: 1)
        capture(app, "demo_j4_02_source_email")
    }

    private func capture(_ app: XCUIApplication, _ name: String) {
        let screenshot = app.screenshot()
        let path = "\(outputDir)/\(name).png"
        try? screenshot.pngRepresentation.write(to: URL(fileURLWithPath: path))
    }
}
