import XCTest
@testable import Ledger

final class ReadableEmailContentTests: XCTestCase {
    func testStripsTagsAndDecodesEntities() {
        let html = "Dear Customer,<br>Rs.<b>120.00</b>&nbsp;is debited from your account."

        let text = ReadableEmailContent.string(from: html)

        XCTAssertEqual(text, "Dear Customer,\nRs.120.00 is debited from your account.")
    }

    func testDropsStyleAndHeadBlocksEntirely() {
        let html = "<html><head><style>body { color: red; }</style></head>" +
            "<body><p>Rs.554.00 debited</p></body></html>"

        let text = ReadableEmailContent.string(from: html)

        XCTAssertFalse(text.contains("color: red"))
        XCTAssertTrue(text.contains("Rs.554.00 debited"))
    }

    func testCollapsesExcessBlankLinesFromBlockTags() {
        let html = "<div>Line one</div><div>Line two</div><table><tr><td>Line three</td></tr></table>"

        let text = ReadableEmailContent.string(from: html)

        XCTAssertFalse(text.contains("\n\n\n"))
        XCTAssertTrue(text.contains("Line one"))
        XCTAssertTrue(text.contains("Line two"))
        XCTAssertTrue(text.contains("Line three"))
    }

    func testEmptyInputStaysEmpty() {
        XCTAssertEqual(ReadableEmailContent.string(from: ""), "")
    }
}
