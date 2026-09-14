"""Static checks for the dependency directions in docs/ARCHITECTURE.md."""

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[2] / "src" / "lbr_dashboard"

FORBIDDEN_IMPORTS = {
    "core": {"app", "ui", "sources", "importers", "units", "analysis"},
    "sources": {"app", "ui"},
    "importers": {"app", "ui"},
    "units": {"app", "ui"},
    "analysis": {"app", "ui"},
    "ui": {"sources", "importers", "units", "analysis"},
}


def _layer_for(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT)
    return relative.parts[0] if len(relative.parts) > 1 else "app"


def _imported_layer(path: Path, node: ast.Import | ast.ImportFrom) -> str | None:
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    else:
        if node.level:
            package = ["lbr_dashboard", *_layer_package(path)]
            package = package[: len(package) - node.level + 1]
            names = [".".join((*package, node.module or ""))]
        else:
            names = [node.module or ""]

    for name in names:
        parts = name.split(".")
        if parts[0] == "lbr_dashboard" and len(parts) > 1:
            return parts[1]
    return None


def _layer_package(path: Path) -> tuple[str, ...]:
    """Return the package components below ``lbr_dashboard`` for a file."""

    relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
    parts = relative.parts[:-1]
    return parts


def test_production_imports_respect_documented_boundaries() -> None:
    violations: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        layer = _layer_for(path)
        forbidden = FORBIDDEN_IMPORTS.get(layer, set())
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported_layer = _imported_layer(path, node)
                if imported_layer in forbidden:
                    violations.append(f"{path}: {layer} -> {imported_layer}")

    assert violations == [], "Forbidden architecture imports:\n" + "\n".join(violations)
