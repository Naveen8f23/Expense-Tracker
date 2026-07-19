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

    /// BACKLOG.md J5 walkthrough — swipe reveals Edit/Dismiss; Edit opens J3's sheet; Dismiss
    /// calls the endpoint directly and the row disappears without a reload.
    func testJ5SwipeActions() throws {
        let scratchDir = "/private/tmp/claude-502/-Users-naveen-18163-projects-expense-tracker/c95f4903-6984-4003-a537-c6b6ecf8eb63/scratchpad"
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.staticTexts["Ledger"].waitForExistence(timeout: 5))
        let row = app.staticTexts["NAVEEN V"].firstMatch
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
        let row = app.staticTexts["NAVEEN V"].firstMatch
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
        let reassignedRow = app.buttons.matching(
            NSPredicate(format: "label CONTAINS 'NAVEEN V' AND label CONTAINS 'Groceries'")
        ).firstMatch
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
        let row = app.staticTexts["NAVEEN V"].firstMatch
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
        let updatedRow = app.buttons.matching(
            NSPredicate(format: "label CONTAINS 'NAVEEN V' AND label CONTAINS 'Inline Snacks'")
        ).firstMatch
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
