import XCTest
import SwiftUI
@testable import Ledger

final class CategoryColorTests: XCTestCase {
    func testSameNameAlwaysReturnsTheSameColor() {
        let first = CategoryColor.color(for: "Groceries")
        let second = CategoryColor.color(for: "Groceries")

        XCTAssertEqual(first, second)
    }

    func testNilFallsBackToSecondary() {
        XCTAssertEqual(CategoryColor.color(for: nil), .secondary)
    }

    func testEmptyStringFallsBackToSecondary() {
        XCTAssertEqual(CategoryColor.color(for: ""), .secondary)
    }

    func testDifferentNamesCanReturnDifferentColors() {
        // Not a guarantee for every possible pair (it's a hash into a fixed palette), but these
        // two should land in different buckets — catches an accidental "always returns the first
        // color" regression.
        let groceries = CategoryColor.color(for: "Groceries")
        let travel = CategoryColor.color(for: "Travel")

        XCTAssertNotEqual(groceries, travel)
    }
}
