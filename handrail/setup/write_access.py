"""Probe the setup process's own writes without claiming worker authority."""
import os
import tempfile
from pathlib import Path
from handrail.shared.errors import HandrailError


def check_writes(resources):
    """Collect denied setup paths before any board provisioning.

    Temporary files are closed and removed by TemporaryFile, including errors.
    Newly needed directories are retained for setup to resume. This observes
    only the caller's filesystem boundary; it grants no provider permissions.
    """
    issues, checked = [], set()
    for label, resource in resources:
        path = Path(resource)
        if str(path) in checked:
            continue
        checked.add(str(path))
        try:
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.TemporaryFile(dir=str(path)) as stream:
                stream.write(b"handrail setup access check\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            issues.append({"resource": str(path), "purpose": label, "errno": exc.errno,
                           "actor": "handrail setup", "boundary": "host/filesystem"})
    if issues:
        raise HandrailError("SETUP_ACCESS_REQUIRED", "Allow the listed setup paths, then run handrail init again",
                            details={"missing": issues, "worker_authority": "not_proven"})
    return {"setup_process_write_access": True, "worker_authority": "not_proven"}
