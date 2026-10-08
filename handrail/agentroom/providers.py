"""Provider-specific launch preparation; requested settings are not effective rights."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from handrail.shared.errors import HandrailError
from handrail.shared.identity import now


def register_coordinator(store, provider, model, effort, surface, evidence, session_id=None):
    if provider not in ("codex", "cursor") or not isinstance(model, str) or not model.strip() or model.startswith("-"):
        raise HandrailError("COORDINATOR_IDENTITY", "Record the observed provider and exact model; do not infer it from the CLI default")
    if surface not in ("CLI", "IDE") or not isinstance(evidence, str) or not evidence.strip():
        raise HandrailError("COORDINATOR_IDENTITY", "Record CLI/IDE and model observation evidence")
    if provider == "cursor" and effort:
        raise HandrailError("HERDR_EFFORT_INVALID", "Record Cursor's exact model identifier including its supported reasoning setting")
    value = {"id": "current", "provider": provider, "model": model.strip(), "effort": effort,
             "surface": surface, "evidence": evidence, "observed_at": now(),
             "session_id": session_id, "observation_source": "coordinator attestation", "host_wakeup": "unavailable"}
    with store.transaction() as tx:
        tx.put("coordinator", "current", value)
        tx.event("coordinator", "coordinator.registered", value)
    return value


def capabilities(provider):
    executable = shutil.which("codex" if provider == "codex" else "cursor-agent")
    if not executable:
        raise HandrailError("PROVIDER_MISSING", "Install the selected provider CLI", details={"provider": provider})
    try:
        help_result = subprocess.run([executable, "--help"], capture_output=True, text=True, timeout=15)
        version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        raise HandrailError("PROVIDER_CAPABILITY_UNKNOWN", "Could not inspect the selected provider CLI") from None
    if help_result.returncode or version.returncode:
        raise HandrailError("PROVIDER_CAPABILITY_UNKNOWN", "Provider capability inspection failed")
    help_text = help_result.stdout
    return {"provider": provider, "version": version.stdout.strip(), "executable": executable,
            "add_dir": "--add-dir" in help_text, "sandbox": "--sandbox" in help_text,
            "host_wakeup": "not_configured", "observed_at": now()}


def model_capability(provider, model, effort, executable):
    if provider == "codex":
        cache = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "models_cache.json"
        try:
            data = json.loads(cache.read_text())
        except (OSError, ValueError):
            raise HandrailError("MODEL_CAPABILITY_UNKNOWN", "Open the provider model picker once or refresh its model catalog; retry the same selection") from None
        hits = [r for r in data.get("models", []) if r.get("slug") == model]
        if len(hits) != 1:
            raise HandrailError("MODEL_SELECTION_REQUIRED", "The exact model is absent from the observed Codex catalog",
                                details={"model": model, "next": "Refresh the provider catalog or select an available exact model"})
        supported = [r.get("effort") for r in hits[0].get("supported_reasoning_levels", [])]
        if effort and effort not in supported:
            raise HandrailError("HERDR_EFFORT_INVALID", "The selected model does not advertise this reasoning setting",
                                details={"model": model, "effort": effort, "supported": supported})
        return {"source": str(cache), "catalog_time": data.get("fetched_at"), "model": model,
                "effort": effort, "availability": "catalog-observed; server launch remains authoritative"}
    try:
        result = subprocess.run([executable, "models"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        raise HandrailError("MODEL_CAPABILITY_UNKNOWN", "Cursor model catalog could not be observed") from None
    listing = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", result.stdout)
    identifiers = {line.strip().lstrip("*•│| ").split()[0] for line in listing.splitlines() if line.strip().lstrip("*•│| ").split()}
    if result.returncode or model not in identifiers:
        raise HandrailError("MODEL_SELECTION_REQUIRED", "Select an exact identifier from cursor-agent models; reasoning must be part of that identifier",
                            details={"model": model})
    return {"source": "cursor-agent models", "observed_at": now(), "model": model,
            "availability": "catalog-observed; server launch remains authoritative"}


def selection(store, work_id, provider=None, model=None, effort=None):
    existing = store.read("worker_selection", work_id)
    coordinator = store.read("coordinator", "current")
    if provider or model:
        if not provider or not model:
            raise HandrailError("MODEL_SELECTION_REQUIRED", "Supply provider and exact model together")
        selected = {"provider": provider, "model": model, "effort": effort, "source": "explicit"}
    elif existing:
        selected = dict(existing)
    elif coordinator:
        selected = {k: coordinator.get(k) for k in ("provider", "model", "effort")}
        selected["source"] = "observed_coordinator"
    else:
        raise HandrailError("MODEL_SELECTION_REQUIRED", "Record the coordinator's actual provider/model or select a worker model",
                            details={"next": "coordinator register --provider PROVIDER --model EXACT_MODEL --evidence OBSERVATION"})
    if effort is not None:
        selected["effort"] = effort
        if selected["source"] != "explicit":
            selected["source"] += "+explicit_effort"
    if selected["provider"] not in ("codex", "cursor") or not isinstance(selected["model"], str) or not selected["model"].strip():
        raise HandrailError("MODEL_SELECTION_INVALID", "Select Codex or Cursor and an exact model")
    if any(ch.isspace() or ord(ch) < 32 for ch in selected["model"]) or selected["model"].startswith("-"):
        raise HandrailError("MODEL_SELECTION_INVALID", "Model must be a non-flag token")
    if selected.get("effort"):
        if selected["provider"] == "cursor":
            raise HandrailError("HERDR_EFFORT_INVALID", "Use Cursor's exact model identifier with its supported reasoning setting")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", selected["effort"]):
            raise HandrailError("HERDR_EFFORT_INVALID", "Invalid effort")
    selected.update(id=work_id, capabilities=capabilities(selected["provider"]))
    if not selected["capabilities"]["sandbox"] or not selected["capabilities"]["add_dir"]:
        raise HandrailError("PROVIDER_UNSUPPORTED", "This CLI lacks scoped sandbox workspace support", details=selected["capabilities"])
    selected["model_capability"] = model_capability(selected["provider"], selected["model"], selected.get("effort"),
                                                   selected["capabilities"]["executable"])
    with store.transaction() as tx:
        tx.put("worker_selection", work_id, selected)
    return selected


def launch_settings(provider, model, effort, paths):
    if provider == "codex":
        args = ["-m", model, "-c", 'sandbox_mode="workspace-write"', "-c", 'approval_policy="on-request"']
        if effort:
            args += ["-c", "model_reasoning_effort=" + json.dumps(effort)]
    else:
        args = ["--model", model, "--trust", "--sandbox", "enabled"]
    for path in dict.fromkeys(str(Path(p).resolve()) for p in paths):
        args += ["--add-dir", path]
    policy = {"surface": "CLI", "managed_policy": "unknown", "effective_configuration": "unknown"}
    if provider == "codex":
        config_path = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
        try:
            config_text = config_path.read_text()
            policy.update(legacy_key_present=bool(re.search(r"^\s*sandbox_mode\s*=", config_text, re.M)),
                          profile_key_present=bool(re.search(r"^\s*default_permissions\s*=|^\s*\[permissions\.", config_text, re.M)))
        except OSError:
            policy["user_config_observation"] = "unavailable"
        policy["precedence"] = "Launch explicitly requests legacy workspace-write; managed requirements can reject or supersede it. Permission profiles do not compose with legacy settings."
    else:
        policy["precedence"] = "CLI approval rules and sandbox path policy are distinct; deny/managed policy can override requested added directories"
    return {"argv": args, "requested_paths": list(dict.fromkeys(map(str, paths))), "policy_observation": policy,
            "strategy": "workspace-write-with-explicit-roots", "effective_rights": "unknown",
            "limitations": ["Managed permission profiles can supersede launch settings",
                            "Shared Git storage is not branch isolation; hooks/config protections may remain",
                            "The worker must run the scoped probe in its own sandbox before implementation"]}
