"""Exit status follows delivery envelopes, never arbitrary user content."""
def exit_status(value):
    if isinstance(value, list):
        return max([exit_status(item) for item in value] or [0])
    if not isinstance(value, dict):
        return 0
    result = 1 if value.get("status") in ("failed", "unknown", "blocked") else 0
    if value.get("exit_code"):
        result = max(result, 2 if value["exit_code"] == 2 else 1)
    for key in ("cleanup", "board", "boards", "summary", "deliveries", "results", "delivery", "followthrough"):
        if key in value:
            result = max(result, exit_status(value[key]))
    return result
