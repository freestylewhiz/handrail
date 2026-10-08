"""Escaped HTML card sections: overview, details, then a compact criteria table."""
import re
from html import escape
from handrail.shared.errors import HandrailError


from handrail.shared.presentation import validate


def rich_text(value):
    pieces, offset = [], 0
    for match in re.finditer(r"https?://[^\s<>\"']+", value):
        pieces.append(escape(value[offset:match.start()]))
        url = escape(match.group(), quote=True)
        pieces.append('<a href="' + url + '">' + url + '</a>')
        offset = match.end()
    pieces.append(escape(value[offset:]))
    return "".join(pieces)


def render(document):
    criteria = document["criteria"]
    presentation = validate(document.get("presentation"), criteria)
    language = (presentation or {}).get("language", "en")
    sections = [("en", (presentation or {}).get("en", {"overview": document["title"], "criteria": criteria}))]
    if language != "en":
        sections.append((language, presentation[language]))
    html = []
    for lang, content in sections:
        localized = lang == "ko"
        headings = content.get("headings", {"overview": "개요" if localized else "Overview",
                    "criteria": "수용 기준" if localized else "Acceptance criteria",
                    "expected": "기대 결과" if localized else "Expected outcome"})
        label = "English" if lang == "en" else content.get("language_name", {"ko": "한국어"}.get(lang, lang)) + " (" + lang + ")"
        html += ["<h2>" + escape(label) + "</h2>",
                 "<h3>" + escape(headings["overview"]) + "</h3>",
                 "<p>" + rich_text(content["overview"]) + "</p>"]
        for detail in content.get("sections", []):
            html.append("<h3>" + escape(detail["title"]) + "</h3>")
            html.extend("<p>" + rich_text(p) + "</p>" for p in detail.get("paragraphs", []))
            if detail.get("items"):
                html.append("<ul>" + "".join("<li>" + rich_text(i) + "</li>" for i in detail["items"]) + "</ul>")
        html += ["<h3>" + escape(headings["criteria"]) + "</h3>",
                 "<table><thead><tr><th>ID</th><th>" + escape(headings["expected"]) + "</th></tr></thead><tbody>"]
        html.extend("<tr><td><strong>" + escape(k) + "</strong></td><td>" + rich_text(v) + "</td></tr>"
                    for k, v in content["criteria"].items())
        html.append("</tbody></table>")
    html.append("<p>Handrail " + escape("task" if document["kind"] == "work" else document["kind"]) + ": " + escape(document["id"]) + "</p>")
    return "\n".join(html)


def select_sections(description, language="en", sections=None):
    """Return selected generated sections; legacy content remains explicitly raw."""
    from html import unescape
    parts = re.split(r"(?=<h2>)", description)
    managed = "<h2>English</h2>" in description
    if not managed:
        return {"format": "legacy", "content": description, "selection_available": False}
    candidates = [p for p in parts if p.startswith("<h2>") and (
        "<h2>English</h2>" in p if language == "en" else re.search(r"^<h2>[^<]*\(" + re.escape(language) + r"\)</h2>", p))]
    if not candidates:
        raise HandrailError("CARD_LANGUAGE_UNAVAILABLE", "The requested language section is absent")
    selected = "\n".join(candidates)
    if sections:
        blocks = re.split(r"(?=<h3>)", selected)
        selected = "\n".join(b for b in blocks if any(
            "<h3>" + escape(title) + "</h3>" in b or "<h3>" + title + "</h3>" in b for title in sections))
        if not selected:
            raise HandrailError("CARD_SECTION_UNKNOWN", "Choose a section title from this language's heading directory",
                                details={"headings": [unescape(v) for v in re.findall(r"<h3>(.*?)</h3>", "\n".join(candidates))]})
    return {"format": "handrail-html", "language": language, "sections": sections, "content": selected,
            "selection_available": True}
