"""Small resumable prompts shared by terminal and agent setup flows."""
import sys
from handrail.shared.errors import HandrailError


def ask(field, message, choices=None):
    if not sys.stdin.isatty():
        raise HandrailError("SETUP_INPUT_REQUIRED", message,
                            details={"field": field, "choices": choices or [],
                                     "next": "Continue handrail init with the selected option"})
    print(message, file=sys.stderr)
    if choices:
        for i, row in enumerate(choices, 1):
            print(f"  {i}. {row['label']}", file=sys.stderr)
    while True:
        try:
            value = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            raise HandrailError("SETUP_CANCELLED", "Setup saved its completed steps; run again to continue") from None
        if choices:
            if value.isdigit() and 1 <= int(value) <= len(choices):
                return choices[int(value) - 1]["value"]
        elif value:
            return value


def choose(field, rows, selection=None, automatic=True):
    if selection is not None:
        hits = [row for row in rows if str(row["value"]) == str(selection) or row["name"] == selection]
        if len(hits) == 1:
            return hits[0]["value"]
        raise HandrailError("SETUP_SELECTION_INVALID", "Select an unambiguous " + field,
                            details={"field": field, "choices": rows})
    if automatic and len(rows) == 1:
        return rows[0]["value"]
    if not rows:
        raise HandrailError("SETUP_SELECTION_EMPTY", "No available " + field)
    return ask(field, "Select " + field, rows)
