import XCTest
@testable import Ledger

@MainActor
final class CategoryManagementStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: nil)

        XCTAssertTrue(store.categories.isEmpty)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesCategories() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"items":[{"id":1,"name":"Food"},{"id":2,"name":"Travel"}]}"#) }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.categories.map(\.name), ["Food", "Travel"])
    }

    func testCreateCategoryAppendsAndKeepsSortedByName() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "POST" {
                return StubURLSession.json(#"{"id":3,"name":"Bills"}"#)
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"},{"id":2,"name":"Travel"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        let ok = await store.createCategory(baseURL: baseURL, name: "Bills")

        XCTAssertTrue(ok)
        XCTAssertEqual(store.categories.map(\.name), ["Bills", "Food", "Travel"])
    }

    func testRenameCategoryUpdatesItInPlace() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "PATCH" {
                return StubURLSession.json(#"{"id":1,"name":"Groceries"}"#)
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        let ok = await store.renameCategory(baseURL: baseURL, id: 1, name: "Groceries")

        XCTAssertTrue(ok)
        XCTAssertEqual(store.categories.map(\.name), ["Groceries"])
    }

    func testDeleteCategoryNotInUseRemovesItLocally() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "DELETE" {
                return StubURLSession.json("", status: 204)
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        await store.deleteCategory(baseURL: baseURL, id: 1)

        XCTAssertTrue(store.categories.isEmpty)
        XCTAssertNil(store.pendingReassignment)
    }

    func testDeleteCategoryInUseSetsPendingReassignmentInsteadOfFailingSilently() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "DELETE" {
                return StubURLSession.json(#"{"detail": {"message": "Category 1 is used by 3 transaction(s)", "transaction_count": 3}}"#, status: 409)
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"},{"id":2,"name":"Travel"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        await store.deleteCategory(baseURL: baseURL, id: 1)

        XCTAssertEqual(store.pendingReassignment?.id, 1)
        XCTAssertEqual(store.pendingReassignment?.transactionCount, 3)
        XCTAssertEqual(store.categories.map(\.name), ["Food", "Travel"], "not removed until reassignment is confirmed")
    }

    func testConfirmReassignmentAndDeleteCompletesTheDeleteWithReassignToQuery() async {
        var deleteCallCount = 0
        var capturedQuery: String?
        let stub = StubURLSession { request in
            if request.httpMethod == "DELETE" {
                deleteCallCount += 1
                if deleteCallCount == 1 {
                    return StubURLSession.json(#"{"detail": {"message": "Category 1 is used by 3 transaction(s)", "transaction_count": 3}}"#, status: 409)
                }
                capturedQuery = request.url?.query
                return StubURLSession.json("", status: 204)
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"},{"id":2,"name":"Travel"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        await store.deleteCategory(baseURL: baseURL, id: 1)
        XCTAssertNotNil(store.pendingReassignment)

        await store.confirmReassignmentAndDelete(baseURL: baseURL, reassignTo: 2)

        XCTAssertEqual(store.categories.map(\.name), ["Travel"])
        XCTAssertNil(store.pendingReassignment)
        XCTAssertEqual(capturedQuery, "reassign_to=2")
    }

    func testConfirmReassignmentAndDeleteIsANoOpWithoutAPendingReassignment() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "DELETE" {
                XCTFail("should never be called without a pending reassignment")
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        await store.confirmReassignmentAndDelete(baseURL: baseURL, reassignTo: 2)

        XCTAssertEqual(store.categories.count, 1)
    }

    func testCancelReassignmentClearsPendingWithoutDeleting() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "DELETE" {
                return StubURLSession.json(#"{"detail": {"message": "in use", "transaction_count": 1}}"#, status: 409)
            }
            return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
        }
        let store = CategoryManagementStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)
        await store.deleteCategory(baseURL: baseURL, id: 1)
        XCTAssertNotNil(store.pendingReassignment)

        store.cancelReassignment()

        XCTAssertNil(store.pendingReassignment)
        XCTAssertEqual(store.categories.count, 1, "cancelling must not delete anything")
    }
}
