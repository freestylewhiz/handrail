"""Presentation input contract shared by workflow authoring and board rendering."""
import re
from handrail.shared.errors import HandrailError

def validate(presentation, criteria):
    if presentation is None:
        return None
    if not isinstance(presentation, dict) or not isinstance(presentation.get("en"), dict):
        raise HandrailError("CARD_CONTENT_INVALID", "Provide an en section and a separate user-language section")
    language = presentation.get("language", "en")
    if not isinstance(language, str) or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)*", language):
        raise HandrailError("CARD_LANGUAGE_INVALID", "Use a language tag such as en or ko")
    languages = ["en"] if language == "en" else ["en", language]
    sections = []
    for lang in languages:
        section = presentation.get(lang)
        if not isinstance(section, dict) or not isinstance(section.get("overview"), str) or not section["overview"].strip():
            raise HandrailError("CARD_CONTENT_INVALID", "Each language requires an overview")
        translated = section.get("criteria")
        if not isinstance(translated, dict) or set(translated) != set(criteria) or any(
                not isinstance(t, str) or not t.strip() for t in translated.values()):
            raise HandrailError("CARD_CRITERIA_INVALID", "Each language must preserve all criterion IDs")
        if not isinstance(section.get("sections", []), list):
            raise HandrailError("CARD_CONTENT_INVALID", "sections must be a list")
        for detail in section.get("sections", []):
            if not isinstance(detail, dict) or not isinstance(detail.get("title"), str):
                raise HandrailError("CARD_CONTENT_INVALID", "Every detail section needs a title")
            for field in ("paragraphs", "items"):
                if not isinstance(detail.get(field, []), list) or any(not isinstance(v, str) for v in detail.get(field, [])):
                    raise HandrailError("CARD_CONTENT_INVALID", "Paragraphs and items must be lists of text")
        sections.append(section)
        if lang not in ("en", "ko") and (not isinstance(section.get("headings"), dict) or any(
            not isinstance(section["headings"].get(k), str) or not section["headings"][k].strip()
            for k in ("overview", "criteria", "expected"))):
            raise HandrailError("CARD_HEADINGS_REQUIRED", "Supply translated overview, criteria and expected headings")
    # Critical literal values must survive translation. Semantic equivalence is
    # reviewed by the authoring agent, never claimed by this renderer.
    tokens = lambda text: set(re.findall(r"https?://[^\s<>]+|\b\d+(?:\.\d+)*\b", text))
    for key, source in criteria.items():
        for section in sections:
            if not tokens(source) <= tokens(section["criteria"][key]):
                raise HandrailError("CARD_TRANSLATION_LOSS", "Preserve numeric constraints and source URLs", details={"criterion": key})
    return presentation
