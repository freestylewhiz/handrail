"""Observed execution issues are evidence, never policy or an automatic backlog."""
from handrail.shared.errors import HandrailError

ASSESSMENTS = ("not_reviewed", "none_observed", "observed")
STATUSES = ("open", "recovered", "resolved", "unknown")
ATTRIBUTIONS = ("handrail", "provider", "host", "coordination", "unknown")
TEXT_FIELDS = ("id", "stage", "expected", "observed", "impact", "recovery")


def validate(value):
    if not isinstance(value, dict) or set(value) != {"assessment", "items"}:
        raise HandrailError("SUMMARY_ISSUES_INVALID", "Supply handrail_issues assessment and items")
    assessment, items = value["assessment"], value["items"]
    if assessment not in ASSESSMENTS or not isinstance(items, list):
        raise HandrailError("SUMMARY_ISSUES_INVALID", "Use not_reviewed, none_observed or observed with an items list")
    if (assessment == "observed") != bool(items):
        raise HandrailError("SUMMARY_ISSUES_INVALID", "Only observed issues have nonempty items; missing history is not none_observed")
    seen = set()
    for item in items:
        if (not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip() for k in TEXT_FIELDS)
                or item.get("status") not in STATUSES or item.get("attribution") not in ATTRIBUTIONS
                or not isinstance(item.get("evidence"), list) or not item["evidence"]
                or any(not isinstance(ref, str) or not ref.strip() for ref in item["evidence"])):
            raise HandrailError("SUMMARY_ISSUES_INVALID", "Each issue needs id, stage, expected, observed, impact, recovery, status, attribution and evidence references")
        identity = item["id"].strip()
        if identity in seen:
            raise HandrailError("SUMMARY_ISSUES_INVALID", "Use distinct issue IDs within the Summary")
        seen.add(identity)
    return value


def template():
    return {"assessment": "not_reviewed", "items": []}


def guidance():
    return {"authority": "observations_only", "assessments": ASSESSMENTS,
            "statuses": STATUSES, "attributions": ATTRIBUTIONS,
            "item_fields": list(TEXT_FIELDS) + ["status", "attribution", "evidence"],
            "instructions": "Classify by affected responsibility, not who found the issue. Keep application bugs in project results. "
                            "Record concrete evidence references, not raw logs or credentials. Attribution is the author's assessment; "
                            "use unknown when unproven. recovered means work resumed, not that the product defect was fixed. "
                            "Do not create permissions, standing instructions or development tasks from these observations."}
