"""Reading the app's own definitions instead of copying them.

Several things an agent needs to choose correctly — which sort orders an
endpoint accepts, which search methods the optimizer knows, which Monte Carlo
perturbations exist — are already declared in the app. Copying them here would
work until the app changed, and then the copy would be wrong without anything
failing.

So they are read from the app's files at import time. The explanatory text that
goes with each name is still ours (the app does not carry documentation), but
the names themselves always come from the source that defines them, and a name
we have no description for is reported rather than hidden.

When the repo is not reachable — a customer has the app, not a checkout — those
reads fail soft and every name set comes back empty, which every caller treats
as "do not validate". That silently removes the guard that refuses a misspelled
search method, and the engine then falls back to Random without saying so. So a
generated snapshot ships inside the package and answers when the source cannot.
The source still wins wherever it exists, so the snapshot can never mask a
change in the app it was generated from.
"""

from __future__ import annotations

import ast
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_REGISTRY = REPO_ROOT / "resources" / "ai" / "tool_registry.json"
OPTIMIZER_METHODS = REPO_ROOT / "strategy_optimizer" / "optimization_methods" / "__init__.py"
MONTE_CARLO_SRC = (
    REPO_ROOT / "strategy_optimizer" / "robustness_tests" / "monte_carlo_trades.py"
)
LOCALE_EN = REPO_ROOT / "frontend" / "src" / "locales" / "en.json"

# Generated from the app's own source and regenerated whenever it changes, so
# this copy cannot drift silently.
SNAPSHOT = Path(__file__).resolve().parent / "appdata_snapshot.json"


@lru_cache(maxsize=1)
def _snapshot() -> Dict[str, Any]:
    """The frozen vocabulary, for machines with the app but no repo."""
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not read %s: %s", SNAPSHOT, exc)
        return {}


@lru_cache(maxsize=1)
def _locale_en() -> Dict[str, Any]:
    try:
        return json.loads(LOCALE_EN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _snapshot().get("validation_text", {})


def validation_text(code: str, params: Dict[str, Any] | None = None) -> str:
    """The app's own English wording for a validation code.

    The backend answers with i18n keys so the desktop app can say it in the
    user's language. An agent needs the sentence, and the app already has it —
    so it is read from there rather than written a third time. A key we cannot
    resolve is reported as itself, which is still legible.
    """
    node: Any = _locale_en()
    for part in code.split("."):
        if not isinstance(node, dict) or part not in node:
            node = None
            break
        node = node[part]

    values = params or {}
    if not isinstance(node, str):
        detail = ", ".join(f"{k}={v}" for k, v in values.items())
        return f"{code}({detail})" if detail else code

    text = node
    for name, value in values.items():
        text = text.replace(f"{{{{{name}}}}}", str(value))
    return text


@lru_cache(maxsize=1)
def _registry() -> Dict[str, Any]:
    try:
        return json.loads(TOOL_REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not read %s: %s", TOOL_REGISTRY, exc)
        return {}


@lru_cache(maxsize=None)
def enum_for(tool_name: str, argument: str) -> tuple[str, ...]:
    """The accepted values of an argument, as the app's tool registry declares.

    Empty when the registry cannot be read, which callers treat as "do not
    validate" rather than "reject everything".
    """
    for tool in _registry().get("tools", []):
        if tool.get("name") != tool_name:
            continue
        schema = (
            tool.get("openai_definition", {})
            .get("parameters", {})
            .get("properties", {})
            .get(argument, {})
        )
        for candidate in (schema, *(schema.get("anyOf") or [])):
            values = candidate.get("enum")
            if values:
                return tuple(str(v) for v in values)
    frozen = _snapshot().get("enums", {}).get(f"{tool_name}.{argument}")
    return tuple(frozen) if frozen else ()


def _literal_names(path: Path, name: str) -> Set[str]:
    """Read a module-level dict's keys or a set's members without importing it.

    The MCP has no numpy or pandas, so the app's modules cannot be imported
    here; parsing keeps this free of the app's runtime dependencies.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        logger.warning("Could not parse %s: %s", path, exc)
        return set()

    for node in tree.body:
        targets = (
            node.targets if isinstance(node, ast.Assign)
            else [node.target] if isinstance(node, ast.AnnAssign)
            else []
        )
        if not any(isinstance(t, ast.Name) and t.id == name for t in targets):
            continue
        value = node.value
        if isinstance(value, ast.Call) and value.args:  # frozenset({...})
            value = value.args[0]
        try:
            if isinstance(value, ast.Dict):
                return {ast.literal_eval(k) for k in value.keys}
            return set(ast.literal_eval(value))
        except ValueError:
            return set()
    return set()


@lru_cache(maxsize=1)
def search_method_names() -> Set[str]:
    """Names the optimizer accepts. Anything else falls back to Random."""
    return _literal_names(OPTIMIZER_METHODS, "METHODS") or set(
        _snapshot().get("search_methods", ())
    )


@lru_cache(maxsize=1)
def monte_carlo_mode_names() -> Set[str]:
    """Perturbation modes the Monte Carlo test accepts."""
    return _literal_names(MONTE_CARLO_SRC, "VALID_MODES") or set(
        _snapshot().get("monte_carlo_modes", ())
    )


def describe(names: Set[str], descriptions: Dict[str, Any]) -> Dict[str, Any]:
    """Pair names read from the app with the notes we wrote for them.

    A name with no note is surfaced as undocumented rather than dropped: it
    means the app gained something and this catalogue has not caught up.
    """
    if not names:  # source unreadable — fall back to what we know
        return dict(descriptions)
    catalogue: Dict[str, Any] = {}
    for name in sorted(names):
        catalogue[name] = descriptions.get(
            name, "Available in this app version; not documented here yet."
        )
    return catalogue
