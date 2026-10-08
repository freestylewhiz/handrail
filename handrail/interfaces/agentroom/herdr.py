"""Explicit Herdr CLI transport.

The client pins one endpoint and never retries a command. HERDR_ENV is left
untouched. Focus-routing variables are removed so an omitted target cannot
follow the caller pane. Approval for keys and close stays with the caller.
"""
from __future__ import annotations

import errno
import json
import os
import re
import subprocess

from handrail.shared.errors import HandrailError

_STALL_CODES = {"agent_prompt_stalled", "agent_wait_timeout"}
_TIMEOUT_CODES = {"timeout", "command_timeout", "deadline_exceeded"}
_PREINPUT_CODES = {"agent_not_ready"}
_FOCUS_ENV = ("HERDR_PANE_ID", "HERDR_TAB_ID", "HERDR_WORKSPACE_ID")
_READ_SOURCES = {"visible", "recent-unwrapped"}
_MUTATING = {"prompt", "send-keys", "start", "create", "close"}
_SOCKET_ERRNOS = {
    errno.EPERM, errno.EACCES, errno.ECONNREFUSED, errno.ENOENT, errno.EPIPE,
    errno.ECONNRESET, errno.ENOTSOCK, errno.ECONNABORTED, errno.ETIMEDOUT,
}


def _identifier_present(value, key):
    if isinstance(value, dict):
        found = value.get(key)
        if isinstance(found, str) and found.strip():
            return True
        if isinstance(found, int) and not isinstance(found, bool) and found > 0:
            return True
        return any(_identifier_present(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_identifier_present(item, key) for item in value)
    return False


def _command_name(args):
    if len(args) > 1 and args[0] in {"agent", "workspace", "tab", "pane"}:
        return str(args[1])
    return str(args[0]) if args else ""


def _explicit_id(value, label):
    if not isinstance(value, str) or not value or value != value.strip():
        raise HandrailError("HERDR_TARGET_REQUIRED", label + " must be an explicit id")
    lowered = value.lower()
    if lowered in {"current", "--current"} or value.startswith("-") or any(ch.isspace() for ch in value):
        raise HandrailError("HERDR_TARGET_REQUIRED", label + " must not use the focused pane or a flag")
    return value


def _error_parts(payload):
    if not isinstance(payload, dict):
        return None, None
    error = payload.get("error")
    code = payload.get("code") if isinstance(payload.get("code"), str) else None
    message = payload.get("message") if isinstance(payload.get("message"), str) else None
    if isinstance(error, dict):
        if isinstance(error.get("code"), str):
            code = code or error["code"]
        if isinstance(error.get("message"), str):
            message = error["message"]
    elif isinstance(error, str):
        message = error
    failed = payload.get("ok") is False or payload.get("success") is False or error is not None
    return (code, message) if failed else (None, None)


class HerdrClient:
    def __init__(self, endpoint: dict, executable="herdr", timeout=30):
        if not isinstance(endpoint, dict) or set(endpoint) not in ({"session"}, {"socket"}):
            raise HandrailError("HERDR_ENDPOINT_INVALID", "endpoint must be exactly {session: name} or {socket: absolute_path}")
        if not isinstance(executable, str) or not executable.strip() or executable != executable.strip():
            raise HandrailError("HERDR_EXECUTABLE_INVALID", "Herdr executable must be a command name or path")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise HandrailError("HERDR_TIMEOUT_INVALID", "timeout must be a positive number of seconds")
        if "session" in endpoint:
            session = endpoint["session"]
            if not isinstance(session, str) or not session or session != session.strip() or "/" in session or session.startswith("-"):
                raise HandrailError("HERDR_ENDPOINT_INVALID", "session name must be an explicit non-flag token")
            self._mode = "session"
            self._pin = session
        else:
            socket = endpoint["socket"]
            if not isinstance(socket, str) or not os.path.isabs(socket) or "\x00" in socket:
                raise HandrailError("HERDR_ENDPOINT_INVALID", "socket must be an absolute path")
            self._mode = "socket"
            self._pin = socket
        self.executable = executable
        self.timeout = timeout

    def _child_env(self):
        env = os.environ.copy()
        for key in _FOCUS_ENV:
            env.pop(key, None)
        if self._mode == "socket":
            env.pop("HERDR_SESSION", None)
            env["HERDR_SOCKET_PATH"] = self._pin
        else:
            env.pop("HERDR_SOCKET_PATH", None)
            env.pop("HERDR_SESSION", None)
        inherited = os.environ.get("HERDR_ENV")
        if inherited is None:
            env.pop("HERDR_ENV", None)
        else:
            env["HERDR_ENV"] = inherited
        return env

    def _argv(self, *args):
        argv = [self.executable]
        if self._mode == "session":
            argv.extend(["--session", self._pin])
        argv.extend(str(arg) for arg in args)
        return argv

    def _classify(self, code, command, *, parsed):
        mutating = command in _MUTATING
        details = {"command": command, "parsed": parsed}
        if code:
            details["herdr_code"] = code
        if code in _PREINPUT_CODES and command == "prompt":
            return HandrailError(
                "HERDR_NOT_READY",
                "Herdr rejected the prompt before input was submitted",
                details=details,
                retryable=True,
                uncertain=False,
            )
        if code in _STALL_CODES or (isinstance(code, str) and "stall" in code.lower()):
            return HandrailError(
                "HERDR_STALLED",
                "Herdr reported a stall; delivery is uncertain and was not resent",
                details=details,
                retryable=False,
                uncertain=True,
            )
        if code in _TIMEOUT_CODES or (isinstance(code, str) and code.lower() == "timeout"):
            return HandrailError(
                "HERDR_TIMEOUT",
                "Herdr reported a timeout; delivery is uncertain and was not resent",
                details=details,
                retryable=False,
                uncertain=True,
            )
        if code in _PREINPUT_CODES and command == "start":
            return HandrailError(
                "HERDR_NOT_READY",
                "Herdr start was not ready; a process may already exist and was not restarted",
                details=details,
                retryable=False,
                uncertain=True,
            )
        if mutating:
            return HandrailError(
                "HERDR_UNCERTAIN",
                "Herdr mutation outcome is uncertain and was not resent",
                details=details,
                retryable=False,
                uncertain=True,
            )
        if code in _PREINPUT_CODES:
            return HandrailError("HERDR_NOT_READY", "Herdr target was not ready", details=details, retryable=True, uncertain=False)
        return HandrailError("HERDR_FAILED", "Herdr command failed", details=details, retryable=False, uncertain=False)

    def _transport_error(self, code, message, command):
        mutating = command in _MUTATING
        error = HandrailError(code, message, details={"command": command}, retryable=not mutating, uncertain=mutating)
        error.__suppress_context__ = True
        raise error

    def _run(self, *args, timeout=None):
        command = _command_name(args)
        argv = self._argv(*args)
        limit = self.timeout if timeout is None else timeout
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=limit,
                check=False,
                shell=False,
                env=self._child_env(),
            )
        except FileNotFoundError:
            raise HandrailError("HERDR_EXECUTABLE_MISSING", "Herdr executable was not found", uncertain=False) from None
        except PermissionError:
            self._transport_error("HERDR_PERMISSION", "Herdr socket or executable permission was denied", command)
        except subprocess.TimeoutExpired:
            raise HandrailError(
                "HERDR_TIMEOUT",
                "Herdr command timed out; it was not resent",
                details={"command": command},
                retryable=False,
                uncertain=True,
            ) from None
        except OSError as exc:
            if exc.errno in _SOCKET_ERRNOS:
                self._transport_error("HERDR_SOCKET", "Herdr socket connection failed", command)
            self._transport_error("HERDR_OS_ERROR", "Herdr process could not be completed", command)
        output = completed.stdout or ""
        payload = None
        parsed = False
        for raw in (output, completed.stderr or ""):
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
            except (ValueError, TypeError):
                continue
            parsed = True
            break
        code = None
        failed = False
        if isinstance(payload, dict):
            code, _message = _error_parts(payload)
            failed = bool(code) or payload.get("ok") is False or payload.get("success") is False or payload.get("error") is not None
        if completed.returncode or failed:
            raise self._classify(code, command, parsed=parsed and isinstance(payload, dict))
        return output

    def _reject_failure(self, value, command):
        if not isinstance(value, dict):
            return
        code, _message = _error_parts(value)
        if code or value.get("ok") is False or value.get("success") is False or value.get("error") is not None:
            raise self._classify(code, command, parsed=True)

    def _unwrap(self, output, *, allow_text, command):
        mutating = command in _MUTATING
        if not str(output).strip():
            if allow_text:
                return ""
            if mutating:
                raise self._classify(None, command, parsed=False)
            return {}
        try:
            value = json.loads(output)
        except (ValueError, TypeError):
            if allow_text:
                return str(output).rstrip("\n")
            if mutating:
                raise self._classify(None, command, parsed=False)
            raise HandrailError("HERDR_INVALID_RESPONSE", "Herdr returned non-JSON output", details={"command": command}, uncertain=False) from None
        self._reject_failure(value, command)
        while isinstance(value, dict) and "result" in value and any(key in value for key in ("ok", "success", "id", "error")):
            value = value["result"]
            self._reject_failure(value, command)
        if allow_text and isinstance(value, str):
            return value
        if isinstance(value, dict) and (value or not mutating):
            return value
        if allow_text and value is None:
            return ""
        if mutating:
            raise self._classify(None, command, parsed=False)
        if allow_text:
            return "" if value is None else str(value)
        raise HandrailError("HERDR_INVALID_RESPONSE", "Herdr result must be an object", details={"command": command}, uncertain=False)

    def _json(self, *args, timeout=None):
        command = _command_name(args)
        return self._unwrap(self._run(*args, timeout=timeout), allow_text=False, command=command)

    def _require_identifier(self, value, command, *keys):
        if any(_identifier_present(value, key) for key in keys):
            return value
        raise HandrailError(
            "HERDR_UNCERTAIN",
            "Herdr create result did not include " + " or ".join(keys),
            details={"command": command, "fields": list(keys)},
            retryable=False,
            uncertain=True,
        )

    def agent_get(self, target):
        return self._json("agent", "get", _explicit_id(target, "agent target"))

    def agent_prompt(self, target, text):
        if not isinstance(text, str) or not text:
            raise HandrailError("HERDR_TEXT_REQUIRED", "agent prompt text must be explicit")
        agent = _explicit_id(target, "agent target")
        return self._json(
            "agent", "prompt", agent, text, "--wait",
            "--until", "working", "--until", "blocked", "--until", "done",
            "--timeout", str(self.timeout * 1000),
            timeout=self.timeout + 5,
        )

    def agent_read(self, target, source="visible", lines=120):
        if source not in _READ_SOURCES:
            raise HandrailError("HERDR_SOURCE_INVALID", "agent read source must be visible or recent-unwrapped")
        if isinstance(lines, bool) or not isinstance(lines, int) or not 1 <= lines <= 1000:
            raise HandrailError("HERDR_LINES_INVALID", "agent read lines must be from 1 to 1000")
        output = self._run(
            "agent", "read", _explicit_id(target, "agent target"),
            "--lines", str(lines), "--source", source, "--format", "text",
        )
        return self._unwrap(output, allow_text=True, command="read")

    def agent_keys(self, target, keys):
        agent = _explicit_id(target, "agent target")
        if isinstance(keys, str):
            sequence = [keys]
        elif isinstance(keys, (list, tuple)) and keys and all(isinstance(item, str) and item for item in keys):
            sequence = list(keys)
        else:
            raise HandrailError("HERDR_KEYS_REQUIRED", "keys must be a non-empty string or list of strings")
        return self._json("agent", "send-keys", agent, *sequence)

    def agent_start(self, name, provider, pane_id, model, effort=None, writable_paths=None):
        worker = _explicit_id(name, "agent name")
        pane = _explicit_id(pane_id, "pane id")
        if not isinstance(provider, str) or provider.lower() not in {"codex", "cursor"}:
            raise HandrailError("HERDR_PROVIDER_UNSUPPORTED", "provider must be codex or cursor")
        if not isinstance(model, str) or not model or model != model.strip() or "\n" in model:
            raise HandrailError("HERDR_MODEL_REQUIRED", "model must be an explicit model name")
        kind = provider.lower()
        args = ["agent", "start", worker, "--kind", kind, "--pane", pane, "--timeout", str(self.timeout * 1000), "--"]
        if kind == "codex":
            args.extend(["-m", model, "-c", 'sandbox_mode="workspace-write"', "-c", 'approval_policy="on-request"'])
            if effort is not None:
                if not isinstance(effort, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", effort):
                    raise HandrailError("HERDR_EFFORT_INVALID", "effort must be a short token")
                args.extend(["-c", 'model_reasoning_effort="' + effort + '"'])
        else:
            args.extend(["--model", model, "--trust", "--sandbox", "enabled"])
            if effort is not None:
                raise HandrailError("HERDR_EFFORT_INVALID", "cursor start does not accept a reasoning effort")
        for path in writable_paths or []:
            if not isinstance(path, str) or not os.path.isabs(path):
                raise HandrailError("WORKER_PATH_INVALID", "Worker writable paths must be absolute")
            args.extend(["--add-dir", path])
        return self._require_identifier(self._json(*args, timeout=self.timeout + 5), "start", "pane_id", "name")

    def workspace_create(self, cwd, label):
        if not isinstance(cwd, str) or not os.path.isabs(cwd):
            raise HandrailError("HERDR_CWD_REQUIRED", "workspace cwd must be an absolute path")
        if not isinstance(label, str) or not label.strip():
            raise HandrailError("HERDR_LABEL_REQUIRED", "workspace label is required")
        return self._require_identifier(
            self._json("workspace", "create", "--cwd", cwd, "--label", label, "--no-focus"),
            "create", "workspace_id")

    def workspace_get(self, id):
        return self._json("workspace", "get", _explicit_id(id, "workspace id"))

    def workspace_close(self, id):
        return self._json("workspace", "close", _explicit_id(id, "workspace id"))

    def tab_create(self, workspace_id, cwd, label):
        if not isinstance(cwd, str) or not os.path.isabs(cwd):
            raise HandrailError("HERDR_CWD_REQUIRED", "tab cwd must be an absolute path")
        if not isinstance(label, str) or not label.strip():
            raise HandrailError("HERDR_LABEL_REQUIRED", "tab label is required")
        return self._require_identifier(self._json(
            "tab", "create",
            "--workspace", _explicit_id(workspace_id, "workspace id"),
            "--cwd", cwd, "--label", label, "--no-focus",
        ), "create", "pane_id")

    def pane_get(self, id):
        return self._json("pane", "get", _explicit_id(id, "pane id"))

    def pane_process_info(self, id):
        return self._json("pane", "process-info", "--pane", _explicit_id(id, "pane id"))
