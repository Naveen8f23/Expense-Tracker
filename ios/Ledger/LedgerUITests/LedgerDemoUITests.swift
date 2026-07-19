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
        let row = app.cells.containing(.button, identifier: "NAVEEN V").firstMatch
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

    /// BACKLOG.md J5 walkthrough — swipe reveals Edit/Dismiss; Edit opens J3's sheet; Dismiss
    /// calls the endpoint directly and the row disappears without a reload.
    func testJ5SwipeActions() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        let row = app.cells.containing(.button, identifier: "NAVEEN V").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))

        // Swipe left to reveal the Edit/Dismiss actions.
        row.swipeLeft()
        let editButton = app.buttons["Edit"]
        let dismissButton = app.buttons["Dismiss"]
        XCTAssertTrue(editButton.waitForExistence(timeout: 3))
        XCTAssertTrue(dismissButton.exists)
        capture(app, "demo_j5_01_swipe_revealed", scratchDir)

        // Edit opens J3's detail sheet.
        editButton.tap()
        XCTAssertTrue(app.navigationBars["Transaction"].waitForExistence(timeout: 5))
        capture(app, "demo_j5_02_edit_opens_detail_sheet", scratchDir)
        app.buttons["Cancel"].tap()

        // Dismiss calls the endpoint directly — no confirmation — and the row disappears.
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        row.swipeLeft()
        XCTAssertTrue(app.buttons["Dismiss"].waitForExistence(timeout: 3))
        app.buttons["Dismiss"].tap()
        Thread.sleep(forTimeInterval: 1) // let the request resolve
        capture(app, "demo_j5_03_after_dismiss", scratchDir)
    }

    /// BACKLOG.md J6 walkthrough — create/rename a category in the new "Manage categories"
    /// screen, assign it to a real transaction via J3's inline "+ New category" flow isn't needed
    /// here (this exercises the management screen instead), then delete it while it's in use and
    /// confirm the reassignment sheet appears and completes the delete.
    func testJ6CategoryManagement() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))

        // Open Manage Categories via the new tag toolbar button.
        app.buttons["Manage categories"].tap()
        XCTAssertTrue(app.navigationBars["Categories"].waitForExistence(timeout: 5))
        capture(app, "demo_j6_01_manage_categories_initial", scratchDir)

        // Create a new category.
        let nameField = app.textFields["New category name"]
        XCTAssertTrue(nameField.waitForExistence(timeout: 3))
        nameField.tap()
        nameField.typeText("Test Snacks")
        app.buttons["Add"].tap()
        let newRow = app.staticTexts["Test Snacks"]
        XCTAssertTrue(newRow.waitForExistence(timeout: 5))
        capture(app, "demo_j6_02_created", scratchDir)

        // Rename it via swipe -> Rename -> alert text field.
        newRow.swipeLeft()
        XCTAssertTrue(app.buttons["Rename"].waitForExistence(timeout: 3))
        app.buttons["Rename"].tap()
        let renameField = app.textFields["Name"]
        XCTAssertTrue(renameField.waitForExistence(timeout: 3))
        renameField.clearAndTypeText("Test Snacks Renamed")
        app.buttons["Save"].tap()
        XCTAssertTrue(app.staticTexts["Test Snacks Renamed"].waitForExistence(timeout: 5))
        capture(app, "demo_j6_03_renamed", scratchDir)

        app.navigationBars["Categories"].buttons["Done"].tap()

        // Assign the renamed category to a real transaction via J3's picker.
        let row = app.cells.containing(.button, identifier: "NAVEEN V").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        row.tap()
        XCTAssertTrue(app.navigationBars["Transaction"].waitForExistence(timeout: 5))
        let categoryPickerButton = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Category,'")).firstMatch
        XCTAssertTrue(categoryPickerButton.waitForExistence(timeout: 3))
        categoryPickerButton.tap()
        app.buttons["Test Snacks Renamed"].tap()
        app.navigationBars["Transaction"].buttons["Save"].tap()
        XCTAssertTrue(row.waitForExistence(timeout: 5))

        // Back in Manage Categories, deleting the now-in-use category must trigger reassignment,
        // not a silent failure or a dead end.
        app.buttons["Manage categories"].tap()
        XCTAssertTrue(app.navigationBars["Categories"].waitForExistence(timeout: 5))
        let inUseRow = app.staticTexts["Test Snacks Renamed"].firstMatch
        XCTAssertTrue(inUseRow.waitForExistence(timeout: 5))
        inUseRow.swipeLeft()
        app.buttons["Delete"].tap()
        XCTAssertTrue(app.navigationBars["Reassign & Delete"].waitForExistence(timeout: 5))
        capture(app, "demo_j6_04_reassignment_sheet", scratchDir)

        app.buttons["Groceries"].tap()
        XCTAssertTrue(app.navigationBars["Categories"].waitForExistence(timeout: 5))
        capture(app, "demo_j6_05_after_reassign_and_delete", scratchDir)

        // Close the sheet entirely before checking absence — a background transaction row
        // (obscured but still present in the accessibility tree while this sheet is up) can
        // still carry the pre-reassignment category name for a moment, which would make an
        // app-wide "does this text exist anywhere" check ambiguous. Dismissing first, and
        // reopening Manage Categories fresh, checks one unambiguous, fully-settled screen state.
        app.navigationBars["Categories"].buttons["Done"].tap()
        // The payee is now its own Button (BACKLOG.md L3), not combined into one big row-wide
        // accessibility label — check the cell contains both the payee button and the new
        // category text, rather than a single combined label.
        let reassignedRow = app.cells
            .containing(.button, identifier: "NAVEEN V")
            .containing(.staticText, identifier: "Groceries")
            .firstMatch
        XCTAssertTrue(reassignedRow.waitForExistence(timeout: 5), "the reassigned transaction must show its new category, not the deleted one")

        app.buttons["Manage categories"].tap()
        XCTAssertTrue(app.navigationBars["Categories"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["Test Snacks Renamed"].exists, "deleted category must not reappear in a fresh load")
        capture(app, "demo_j6_06_confirmed_gone_after_reload", scratchDir)
    }

    /// BACKLOG.md J6's *other* half — the inline "+ New category…" option in J3's own picker
    /// (distinct from the dedicated Manage Categories screen `testJ6CategoryManagement` covers).
    func testJ6InlineNewCategoryFromDetailPicker() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        let row = app.cells.containing(.button, identifier: "NAVEEN V").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        row.tap()
        XCTAssertTrue(app.navigationBars["Transaction"].waitForExistence(timeout: 5))

        let categoryPickerButton = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Category,'")).firstMatch
        XCTAssertTrue(categoryPickerButton.waitForExistence(timeout: 3))
        categoryPickerButton.tap()
        let newCategoryOption = app.buttons["+ New category…"]
        XCTAssertTrue(newCategoryOption.waitForExistence(timeout: 3))
        newCategoryOption.tap()

        let nameField = app.textFields["Name"]
        XCTAssertTrue(nameField.waitForExistence(timeout: 3))
        nameField.typeText("Inline Snacks")
        app.buttons["Create"].tap()

        // Created-then-selected in one flow — the picker should now show the new category as the
        // current value without a second trip to select it.
        let updatedPickerButton = app.buttons.matching(NSPredicate(format: "label == 'Category, Inline Snacks'")).firstMatch
        XCTAssertTrue(updatedPickerButton.waitForExistence(timeout: 5))
        capture(app, "demo_j6_inline_01_created_and_selected", scratchDir)

        app.navigationBars["Transaction"].buttons["Save"].tap()
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        // Same reasoning as testJ6CategoryManagement's final check — the payee is its own Button
        // now (BACKLOG.md L3), so check the cell contains both it and the new category text
        // rather than one combined row-wide label.
        let updatedRow = app.cells
            .containing(.button, identifier: "NAVEEN V")
            .containing(.staticText, identifier: "Inline Snacks")
            .firstMatch
        XCTAssertTrue(updatedRow.waitForExistence(timeout: 5), "the saved transaction must show the newly-created category")
        capture(app, "demo_j6_inline_02_saved", scratchDir)
    }

    /// BACKLOG.md J7 — the nav-bar sync-health dot and its tap-through detail sheet.
    func testJ7SyncHealthIndicator() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        let dot = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Sync status:'")).firstMatch
        XCTAssertTrue(dot.waitForExistence(timeout: 5))
        capture(app, "demo_j7_01_list_with_dot", scratchDir)

        dot.tap()
        XCTAssertTrue(app.navigationBars["Sync Health"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Scanned"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Matched"].exists)
        XCTAssertTrue(app.staticTexts["Skipped"].exists)
        XCTAssertTrue(app.staticTexts["Failed"].exists)
        capture(app, "demo_j7_02_sync_health_sheet", scratchDir)

        app.navigationBars["Sync Health"].buttons["Done"].tap()
        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 3))
    }

    /// BACKLOG.md M1 — the "+" toolbar escape hatch for a transaction with no source email.
    func testM1AddTransaction() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        let addButton = app.buttons["Add transaction"]
        XCTAssertTrue(addButton.waitForExistence(timeout: 5))
        addButton.tap()

        XCTAssertTrue(app.navigationBars["Add Transaction"].waitForExistence(timeout: 5))
        capture(app, "demo_m1_01_form", scratchDir)

        let amountField = app.textFields["Amount"]
        XCTAssertTrue(amountField.waitForExistence(timeout: 3))
        amountField.tap()
        amountField.typeText("42")

        let payeeField = app.textFields["Payee"]
        payeeField.tap()
        payeeField.typeText("Corner Kirana Store")

        // Save is disabled until amount + payee are both present — confirm it's enabled now.
        let saveButton = app.navigationBars["Add Transaction"].buttons["Save"]
        XCTAssertTrue(saveButton.isEnabled)
        capture(app, "demo_m1_02_filled_in", scratchDir)

        saveButton.tap()
        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))

        let newRow = app.cells.containing(.button, identifier: "Corner Kirana Store").firstMatch
        XCTAssertTrue(newRow.waitForExistence(timeout: 5), "the manually-added transaction must appear in the list")
        capture(app, "demo_m1_03_appears_in_list", scratchDir)
    }

    /// BACKLOG.md M2 — poll-driven local notification for a new transaction. `Process`/`NSTask`
    /// isn't available on iOS (this bundle compiles for the iOS SDK, even though XCUITest code
    /// executes via the simulator), so this smoke test alone can't create a "new" transaction
    /// mid-run and observe the resulting SpringBoard banner (which isn't reliably queryable from
    /// this app's own `XCUIApplication` anyway). The actual poll → detect → schedule pipeline was
    /// separately verified live this session by creating a real transaction via `curl` from the
    /// host side while this app ran, and confirming via temporary instrumentation that
    /// `NewTransactionNotifier.poll()` correctly detected it and `UNUserNotificationCenter`
    /// reported the request scheduled with no error (see BACKLOG.md M2 for the full account).
    /// This test just confirms the app launches cleanly and the permission prompt is handled
    /// without crashing or hanging.
    func testM2NewTransactionNotification() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()

        // Handle the system notification-permission alert the moment it appears.
        addUIInterruptionMonitor(withDescription: "Notification permission") { alert in
            let allow = alert.buttons["Allow"]
            if allow.exists {
                allow.tap()
                return true
            }
            return false
        }

        app.launch()
        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        // Tapping the (inert) nav bar title, not the app body, services the interruption monitor
        // without accidentally tapping a real row/button underneath the permission alert.
        app.navigationBars["Ledger"].tap()
        Thread.sleep(forTimeInterval: 2)
        capture(app, "demo_m2_00_launched", scratchDir)
        XCTAssertTrue(app.staticTexts["Ledger"].exists, "app must still be alive and responsive after the permission prompt")
    }

    /// BACKLOG.md Epic K walkthrough — the Review tab (K1), swipe-to-ignore (K2), tapping a
    /// low-confidence transaction reuses J3's sheet (K3), and the tab badge (K4).
    func testEpicKReviewTab() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        // K4 — the Review tab wears its queue size as a badge, fetched on launch.
        let reviewTab = app.tabBars.buttons["Review"]
        XCTAssertTrue(reviewTab.waitForExistence(timeout: 5))
        Thread.sleep(forTimeInterval: 1) // let the initial GET /needs-review resolve
        capture(app, "demo_k_01_tab_bar_with_badge", scratchDir)

        reviewTab.tap()
        XCTAssertTrue(app.navigationBars["Review"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Unmatched Emails"].waitForExistence(timeout: 5))
        capture(app, "demo_k_02_review_tab", scratchDir)

        // K1 — reason chip on the unmatched email row.
        XCTAssertTrue(app.staticTexts["Unrecognized"].exists || app.staticTexts["Extraction failed"].exists)

        // K1's "tap to view" (mirrors F3/J4) — opens the raw source email, read-only.
        let emailRow = app.cells.containing(.staticText, identifier: "Unrecognized").firstMatch
        if emailRow.exists {
            emailRow.tap()
            XCTAssertTrue(app.navigationBars["Source Email"].waitForExistence(timeout: 5))
            capture(app, "demo_k_03_source_email_from_review", scratchDir)
            app.navigationBars["Source Email"].buttons.firstMatch.tap()
            XCTAssertTrue(app.navigationBars["Review"].waitForExistence(timeout: 5))
        }

        // K2 — swipe reveals Ignore; tapping calls the endpoint directly.
        let unmatchedRow = app.staticTexts["Unrecognized"].firstMatch
        XCTAssertTrue(unmatchedRow.waitForExistence(timeout: 5))
        unmatchedRow.swipeLeft()
        XCTAssertTrue(app.buttons["Ignore"].waitForExistence(timeout: 3))
        capture(app, "demo_k_04_swipe_reveals_ignore", scratchDir)
        app.buttons["Ignore"].tap()

        let rowGone = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: unmatchedRow)
        wait(for: [rowGone], timeout: 10)
        capture(app, "demo_k_05_after_ignore", scratchDir)
    }

    /// BACKLOG.md Epic L walkthrough — monthly summary + month switcher (L1), category breakdown
    /// (L2), and tapping a payee name from the list opens the payee history panel (L3).
    func testEpicLAnalytics() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        app.tabBars.buttons["Analytics"].tap()
        XCTAssertTrue(app.navigationBars["Analytics"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Summary"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["By Category"].exists)
        capture(app, "demo_l_01_analytics_current_month", scratchDir)

        // L1 — month switcher moves back, re-fetches, and the label changes.
        let monthLabelBefore = app.staticTexts.matching(NSPredicate(format: "label MATCHES '\\\\d{4}-\\\\d{2}'")).firstMatch.label
        app.buttons["Previous month"].tap()
        Thread.sleep(forTimeInterval: 1)
        let monthLabelAfter = app.staticTexts.matching(NSPredicate(format: "label MATCHES '\\\\d{4}-\\\\d{2}'")).firstMatch.label
        XCTAssertNotEqual(monthLabelBefore, monthLabelAfter, "month label must change after Previous")
        capture(app, "demo_l_02_previous_month", scratchDir)
        app.buttons["Next month"].tap() // back to the current month
        Thread.sleep(forTimeInterval: 1)

        // L3 — tapping a payee name from the Ledger tab opens the payee history panel.
        app.tabBars.buttons["Ledger"].tap()
        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        let payeeButton = app.buttons["NAVEEN V"].firstMatch
        XCTAssertTrue(payeeButton.waitForExistence(timeout: 5))
        payeeButton.tap()
        XCTAssertTrue(app.navigationBars["NAVEEN V"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Transactions"].waitForExistence(timeout: 3))
        capture(app, "demo_l_03_payee_history", scratchDir)

        app.navigationBars["NAVEEN V"].buttons["Done"].tap()
        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 3))
    }

    private func capture(_ app: XCUIApplication, _ name: String) {
        capture(app, name, outputDir)
    }

    private func capture(_ app: XCUIApplication, _ name: String, _ directory: String) {
        let screenshot = app.screenshot()
        let path = "\(directory)/\(name).png"
        try? screenshot.pngRepresentation.write(to: URL(fileURLWithPath: path))
    }
}

private extension XCUIElement {
    /// Selects any pre-filled text (e.g. the rename alert's `TextField`, pre-populated with the
    /// current name) and replaces it, rather than appending to it.
    func clearAndTypeText(_ text: String) {
        tap()
        if let value = self.value as? String, !value.isEmpty {
            // Send one delete per existing character, as separate `typeText` calls — a single
            // call with a multi-character delete string isn't reliably interpreted as N deletes.
            for _ in value {
                typeText(XCUIKeyboardKey.delete.rawValue)
            }
        }
        typeText(text)
    }
}
