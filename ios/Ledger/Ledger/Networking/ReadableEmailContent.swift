import Foundation

/// BACKLOG.md J4/K1 follow-up — `SourceEmailView` used to show the cached email's raw HTML
/// source (`<html><body>...<b>120.00</b>...`) verbatim, which is technically safe (SwiftUI `Text`
/// never interprets it as markup) but unreadable. This strips tags/entities down to plain text
/// for *display only* — extraction itself still parses the original raw content untouched
/// (`backend/app/domain/extraction.py`), this has no bearing on that pipeline.
///
/// Deliberately not a real HTML parser and not `NSAttributedString(html:)`/`WKWebView` — both of
/// those actually interpret the markup (and can fetch remote resources referenced by it, e.g. a
/// tracking pixel in an `<img>`), which is exactly the risk this file's sibling comment in
/// `SourceEmailView` warns against for untrusted external HTML (ADR-0006). A plain string
/// transform keeps the output just as inert as the raw text was.
enum ReadableEmailContent {
    private static let stripBlockTags = try! NSRegularExpression(
        pattern: "<(script|style|head)[^>]*>.*?</\\1>",
        options: [.caseInsensitive, .dotMatchesLineSeparators]
    )
    private static let lineBreakTags = try! NSRegularExpression(
        pattern: "<(br|/p|/div|/tr|/table|/li|/h[1-6])[^>]*>",
        options: [.caseInsensitive]
    )
    private static let anyTag = try! NSRegularExpression(pattern: "<[^>]+>")
    private static let blankLines = try! NSRegularExpression(pattern: "\n{3,}")

    private static let entities: [(String, String)] = [
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", "\""), ("&#39;", "'"), ("&apos;", "'"),
    ]

    static func string(from html: String) -> String {
        var text = html as NSString
        text = stripBlockTags.stringByReplacingMatches(
            in: text as String, range: NSRange(location: 0, length: text.length), withTemplate: ""
        ) as NSString
        text = lineBreakTags.stringByReplacingMatches(
            in: text as String, range: NSRange(location: 0, length: text.length), withTemplate: "\n"
        ) as NSString
        text = anyTag.stringByReplacingMatches(
            in: text as String, range: NSRange(location: 0, length: text.length), withTemplate: ""
        ) as NSString

        var result = text as String
        for (entity, replacement) in entities {
            result = result.replacingOccurrences(of: entity, with: replacement)
        }

        let lines = result.components(separatedBy: "\n").map {
            $0.trimmingCharacters(in: .whitespaces)
        }
        result = lines.joined(separator: "\n")
        result = blankLines.stringByReplacingMatches(
            in: result, range: NSRange(location: 0, length: (result as NSString).length),
            withTemplate: "\n\n"
        )
        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
