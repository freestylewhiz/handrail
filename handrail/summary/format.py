"""Separate language sections and select content before returning it to an agent."""
import html
import json
import re
from html.parser import HTMLParser
from handrail.shared.errors import HandrailError
from . import issues

FIELDS = ("intent", "outcome", "decisions", "rules", "avoid", "considerations", "verification")
LABELS = {
    "en": ("Intent", "Outcome", "Decisions and reasons", "Rules", "Avoid", "Considerations", "Verification and limits"),
    "ko": ("목적", "구현 결과", "결정과 이유", "유지할 규칙", "피할 사항", "고려사항", "검증과 한계"),
}
ISSUE_FIELD = "handrail_issues"
ISSUE_LABELS = {"en": "Handrail execution issues", "ko": "Handrail 수행 이슈"}
PROJECT_LABELS = {"en": "Project results", "ko": "프로젝트 결과"}


def project_knowledge(context):
    knowledge = context.get("knowledge", {})
    return knowledge.get("project_results", {}) if context.get("schema_version") == 2 else knowledge


def issue_knowledge(context):
    return context.get("knowledge", {}).get(ISSUE_FIELD, issues.template()) if context.get("schema_version") == 2 else issues.template()


def validate(content):
    if not isinstance(content, dict):
        raise HandrailError("SUMMARY_CONTENT_INVALID", "Summary content must be a JSON object")
    version = content.get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise HandrailError("SUMMARY_SCHEMA_INVALID", "Use Summary schema 1 or 2")
    fields = FIELDS + (ISSUE_FIELD,) if version == 2 else FIELDS
    language = content.get("language", "en")
    if not isinstance(language, str) or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)*", language):
        raise HandrailError("SUMMARY_LANGUAGE_INVALID", "Use a language code, for example ko or en")
    name = content.get("language_name", {"en": "English", "ko": "한국어"}.get(language))
    if not isinstance(name, str) or not name.strip() or name in ("Agent Context",) or (language != "en" and name == "English"):
        raise HandrailError("SUMMARY_LANGUAGE_INVALID", "Supply the user's language name")
    sections = content.get("sections")
    expected = {"en", language}
    if not isinstance(sections, dict) or set(sections) != expected:
        raise HandrailError("SUMMARY_TRANSLATION_REQUIRED", "Provide English and the user's language in separate sections")
    headings = content.get("headings", {})
    if not isinstance(headings, dict):
        raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "headings must be a language-to-fields object")
    for lang in expected:
        if lang not in LABELS and (not isinstance(headings.get(lang), dict) or set(headings[lang]) != set(fields)):
            raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Supply translated headings for each field", details={"language": lang})
        row = sections[lang]
        if not isinstance(row, dict) or set(row) != set(fields) or any(
                not isinstance(row[k], str) or not row[k].strip() for k in fields):
            raise HandrailError("SUMMARY_CONTENT_REQUIRED", "Complete each narrative field; explicitly identify unknown facts", details={"language": lang, "fields": fields})
    facts = content.get("agent_context")
    if not isinstance(facts, dict) or any(key not in facts for key in ("scope", "decisions", "rules", "avoid", "considerations", "verification")):
        raise HandrailError("SUMMARY_CONTEXT_REQUIRED", "Supply scoped decisions, rules, avoid, considerations and verification in agent_context")
    if version == 2:
        issues.validate(facts.get(ISSUE_FIELD))
    elif ISSUE_FIELD in facts:
        raise HandrailError("SUMMARY_SCHEMA_INVALID", "Use schema 2 to separate execution issues")
    if len(json.dumps(content, ensure_ascii=False)) > 150000:
        raise HandrailError("SUMMARY_TOO_LARGE", "Keep the summary concise and link detailed evidence")
    normalized_headings = {lang: headings.get(lang) or dict(zip(fields, LABELS[lang] + ((ISSUE_LABELS[lang],) if version == 2 else ()))) for lang in expected}
    if any(not isinstance(labels, dict) or set(labels) != set(fields) for labels in normalized_headings.values()):
        raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Use one heading for each narrative field")
    if any(not isinstance(v, str) or not v.strip() for labels in normalized_headings.values() for v in labels.values()):
        raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Use non-empty translated headings")
    if any(len(set(labels.values())) != len(fields) for labels in normalized_headings.values()):
        raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Use unique subsection headings")
    normalized_headings = {lang: {key: value.strip() for key, value in labels.items()} for lang, labels in normalized_headings.items()}
    if any(len(set(labels.values())) != len(fields) for labels in normalized_headings.values()):
        raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Use unique subsection headings after trimming")
    normalized_sections = {lang: {key: value.strip() for key, value in fields.items()} for lang, fields in sections.items()}
    result = dict(content, language=language, language_name=name.strip(), headings=normalized_headings, sections=normalized_sections)
    if version == 2:
        project_headings = content.get("project_headings", {})
        if not isinstance(project_headings, dict):
            raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Supply project_headings by language")
        project_headings = {lang: project_headings.get(lang, PROJECT_LABELS.get(lang)) for lang in expected}
        if any(not isinstance(label, str) or not label.strip() or label.strip() in normalized_headings[lang].values()
               for lang, label in project_headings.items()):
            raise HandrailError("SUMMARY_HEADINGS_REQUIRED", "Supply a distinct project results heading for each language")
        result["project_headings"] = {lang: label.strip() for lang, label in project_headings.items()}
    return result


def render(content, context, marker):
    content = validate(content)
    version = content.get("schema_version", 1)
    facts = content["agent_context"]
    knowledge = ({"project_results": {k: v for k, v in facts.items() if k != ISSUE_FIELD},
                  ISSUE_FIELD: facts[ISSUE_FIELD]} if version == 2 else facts)
    context = dict(context, schema_version=version, knowledge=knowledge, language=content["language"],
                   language_name=content["language_name"], sections={},
                   reading={"first": "Agent Context", "analysis_language": "en", "one_language_at_a_time": True})
    pieces = []
    for lang in dict.fromkeys(("en", content["language"])):
        heading = "English" if lang == "en" else content["language_name"]
        labels = content.get("headings", {}).get(lang) or dict(zip(FIELDS, LABELS[lang]))
        context["sections"][lang] = {"heading": heading, "fields": labels}
        pieces.append("<h1>" + html.escape(heading) + "</h1>")
        state = context["record_status"]
        if lang == "en":
            lifecycle = f"Record: {state}. Cycle: {context['cycle']}. Summary revision: {context['summary_revision']}."
        elif lang == "ko":
            translated = {"draft": "초안", "accepted": "사용자 수락 완료", "stale": "이전 주기 기록 — 재검토 필요"}.get(state, state)
            lifecycle = f"기록 상태: {translated}. 작업 주기: {context['cycle']}. 요약 버전: {context['summary_revision']}."
        else:
            lifecycle = f"{state} / {context['cycle']} / {context['summary_revision']}"
        pieces.append("<p>" + html.escape(lifecycle) + "</p>")
        if version == 2:
            project_heading = content["project_headings"][lang]
            context["sections"][lang]["project_heading"] = project_heading
            pieces.append("<h2>" + html.escape(project_heading) + "</h2>")
        for key in FIELDS + ((ISSUE_FIELD,) if version == 2 else ()):
            tag = "h3" if version == 2 and key != ISSUE_FIELD else "h2"
            pieces.append("<" + tag + ">" + html.escape(labels[key]) + "</" + tag + "><p>" +
                          html.escape(content["sections"][lang][key]).replace("\n", "<br>") + "</p>")
        # Source IDs and links remain shared identifiers, not mixed translated prose.
        pieces.append("<ul>" + "".join('<li><a href="' + html.escape(r["url"], quote=True) + '">#' +
                      str(r["card_id"]) + "</a></li>" for r in context["sources"]) + "</ul>")
    pieces.append("<h1>Agent Context</h1><pre><code>" + html.escape(json.dumps(context, ensure_ascii=False, indent=2)) + "</code></pre>")
    return "\n".join(pieces) + "\n\n" + marker


class Sections(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.top = self.sub = None
        self.heading = None
        self.buffer = []
        self.values = {}
        self.code = False
        self.agent = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3"):
            self.heading, self.buffer = tag, []
        elif tag == "code" and self.top == "Agent Context":
            self.code = True
        elif tag == "ul":
            self.sub = None
        elif tag == "a" and self.top and self.sub:
            href = dict(attrs).get("href")
            if href:
                self.values[self.top][self.sub].append(" (" + href + ") ")
        elif tag in ("br", "p", "li") and self.top and self.sub:
            self.values.setdefault(self.top, {}).setdefault(self.sub, []).append("\n")

    def handle_endtag(self, tag):
        if tag == self.heading:
            title = "".join(self.buffer).strip()
            if tag == "h1":
                if title in self.values or (title == "Agent Context" and self.agent):
                    raise HandrailError("SUMMARY_FORMAT_INVALID", "Duplicate top-level section")
                self.top, self.sub = title, None
                self.values.setdefault(title, {})
            else:
                self.sub = title
                if title in self.values.setdefault(self.top, {}):
                    raise HandrailError("SUMMARY_FORMAT_INVALID", "Duplicate narrative heading")
                self.values[self.top][title] = []
            self.heading = None
        if tag == "code":
            self.code = False

    def handle_data(self, data):
        if self.heading:
            self.buffer.append(data)
        elif self.top == "Agent Context" and self.code:
            self.agent.append(data)
        elif self.top and self.sub:
            self.values[self.top][self.sub].append(data)


def parse(description):
    reader = Sections()
    try:
        reader.feed(description)
        context = json.loads("".join(reader.agent))
        if (not isinstance(context, dict) or context.get("type") != "summary" or type(context.get("schema_version")) is not int or context.get("schema_version") not in (1, 2) or
                not isinstance(context.get("summary_revision"), int) or isinstance(context["summary_revision"], bool) or context["summary_revision"] < 1 or
                context.get("record_status") not in ("draft", "accepted", "stale") or
                not isinstance(context.get("sections"), dict) or not isinstance(context.get("knowledge"), dict) or
                not isinstance(context.get("sources"), list) or not context.get("plan_id") or not context.get("workspace_id") or
                not isinstance(context.get("cycle"), int) or not context.get("source_fingerprint")):
            raise ValueError()
        for lang in dict.fromkeys(("en", context["language"])):
            directory = context["sections"][lang]
            fields = FIELDS + ((ISSUE_FIELD,) if context["schema_version"] == 2 else ())
            if set(directory["fields"]) != set(fields) or not set(directory["fields"].values()) <= set(reader.values[directory["heading"]]):
                raise ValueError()
            if context["schema_version"] == 2 and (not directory.get("project_heading") or
                    directory["project_heading"] in directory["fields"].values() or
                    directory["project_heading"] not in reader.values[directory["heading"]]):
                raise ValueError()
        if context["schema_version"] == 2:
            if not isinstance(context["knowledge"].get("project_results"), dict):
                raise ValueError()
            issues.validate(context["knowledge"].get(ISSUE_FIELD))
        return context, {top: {k: "".join(v).strip() for k, v in fields.items()} for top, fields in reader.values.items()}
    except (ValueError, TypeError, AttributeError, KeyError):
        raise HandrailError("SUMMARY_FORMAT_INVALID", "Inspect the card's headings and Agent Context; no content was rewritten") from None


def content_from(description):
    context, sections = parse(description)
    language = context["language"]
    headings, values = {}, {}
    allowed = {d["heading"] for d in context["sections"].values()} | {"Agent Context"}
    if set(sections) != allowed:
        raise HandrailError("SUMMARY_FORMAT_INVALID", "Additional sections require explicit author reconciliation; preserve their content")
    for lang in dict.fromkeys(("en", language)):
        directory = context["sections"][lang]
        allowed_fields = set(directory["fields"].values())
        if context["schema_version"] == 2:
            allowed_fields.add(directory["project_heading"])
            if sections[directory["heading"]][directory["project_heading"]]:
                raise HandrailError("SUMMARY_FORMAT_INVALID", "Preserve text added to the project heading before publishing")
        if set(sections[directory["heading"]]) != allowed_fields:
            raise HandrailError("SUMMARY_FORMAT_INVALID", "Narrative headings changed; preserve edits before publishing")
        headings[lang] = directory["fields"]
        values[lang] = {key: sections[directory["heading"]][heading] for key, heading in headings[lang].items()}
    content = {"language": language, "language_name": context["language_name"], "headings": headings,
               "sections": values, "agent_context": project_knowledge(context)}
    if context["schema_version"] == 2:
        content.update(schema_version=2, project_headings={lang: row["project_heading"] for lang, row in context["sections"].items()},
                       agent_context=dict(content["agent_context"], handrail_issues=issue_knowledge(context)))
    return validate(content)


def select(description, language="en", fields=None):
    context, sections = parse(description)
    if language == "agent":
        if fields:
            if not set(fields) <= {"project_results", ISSUE_FIELD}:
                raise HandrailError("SUMMARY_SECTION_INVALID", "Agent sections are project_results or handrail_issues")
            knowledge = {"project_results": project_knowledge(context), ISSUE_FIELD: issue_knowledge(context)}
            return dict(context, knowledge={key: knowledge[key] for key in dict.fromkeys(fields)})
        return context
    directory = context.get("sections", {}).get(language)
    if not directory:
        raise HandrailError("SUMMARY_LANGUAGE_UNAVAILABLE", "Select a stored language", details={"languages": list(context.get("sections", {}))})
    fields = fields or tuple(directory["fields"])
    if not set(fields) <= set(directory["fields"]):
        raise HandrailError("SUMMARY_SECTION_INVALID", "Select stored narrative fields; legacy cards have no execution issue section", details={"fields": list(directory["fields"])})
    return {key: sections[directory["heading"]][directory["fields"][key]] for key in fields}
