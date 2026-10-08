#!/usr/bin/env python3
"""Static syntax and named internal-import checks; never execute the runtime."""
import argparse
import ast
import json
from pathlib import Path


def bindings(statements):
    names = set()
    for node in statements:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(n.id for target in targets for n in ast.walk(target)
                         if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
        elif isinstance(node, ast.Import):
            names.update(n.asname or n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(n.asname or n.name for n in node.names)
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            names.update(bindings(node.body))
            names.update(bindings(getattr(node, "orelse", [])))
            names.update(bindings(getattr(node, "finalbody", [])))
            for handler in getattr(node, "handlers", []):
                names.update(bindings(handler.body))
    return names


def audit(package):
    package = Path(package).resolve()
    modules, errors = {}, []
    if not (package / "__init__.py").is_file():
        errors.append({"path": str(package), "error": "missing_package"})
    for path in sorted(package.rglob("*.py")):
        parts = list(path.relative_to(package.parent).with_suffix("").parts)
        is_package = parts[-1] == "__init__"
        if is_package:
            parts.pop()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9))
        except SyntaxError as exc:
            errors.append({"path": str(path), "line": exc.lineno, "error": "syntax", "detail": exc.msg})
            continue
        modules[".".join(parts)] = (path, parts if is_package else parts[:-1], tree, bindings(tree.body))
    for path, context, tree, exports in modules.values():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            parts = (context[:len(context) - node.level + 1] if node.level else [])
            parts += node.module.split(".") if node.module else []
            if not parts or parts[0] != package.name:
                continue
            name = ".".join(parts)
            if name not in modules:
                errors.append({"path": str(path), "line": node.lineno, "error": "missing_module", "module": name})
                continue
            exported = modules[name][3]
            for alias in node.names:
                if alias.name == "*":
                    errors.append({"path": str(path), "line": node.lineno, "error": "unresolved_star_import", "module": name})
                elif alias.name not in exported and name + "." + alias.name not in modules:
                    errors.append({"path": str(path), "line": node.lineno, "error": "missing_symbol",
                                   "module": name, "symbol": alias.name})
    return {"package": str(package), "modules": len(modules), "errors": errors,
            "scope": "static syntax and named internal imports; no runtime behavior or external API coverage"}


def require_valid(package):
    result = audit(package)
    if result["errors"]:
        raise SystemExit(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    result = audit(parser.parse_args().package)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
