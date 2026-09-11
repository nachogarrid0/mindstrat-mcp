"""The indicator catalogues, read from the manual that ships with this server.

Two of the knowledge documents are too large to hand over whole — pandas-ta
carries 571 headings and talipp 139 — so they are looked up by name instead of
served as resources. Everything else is a resource; see server.py.

The classification a lookup returns is not written here. ``talipp_reference.md``
groups its indicators under headings that already state the binding assignment
("Trend / Path-Dependent (use talipp)" versus "Momentum (convergent — talipp
also offered)"), so the heading is read as the source of truth. That matters
more than it sounds: choosing the wrong library is the single most common way a
strategy passes backtest and breaks in live, and a copy of the assignment kept
here would be wrong the moment the catalogue moved without anything failing.
"""

from __future__ import annotations

import difflib
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import McpToolError

logger = logging.getLogger(__name__)

# The manual ships with the server. It used to be read out of the repo's
# the app's repo, which tied this server to a checkout it
# cannot assume exists: on a customer's machine there is no repo, so every
# lookup failed and the library assignment got decided from memory — the exact
# error this module exists to prevent.
MANUAL_DIR = Path(__file__).resolve().parents[1] / "manual"

PANDAS_TA_DOC = MANUAL_DIR / "pandas_ta_reference.md"
TALIPP_DOC = MANUAL_DIR / "talipp_reference.md"
RUNTIME_DOC = MANUAL_DIR / "runtime_constraints.md"

PATH_DEPENDENT = "path-dependent"
CONVERGENT = "convergent"

# The two catalogues spell several indicators differently, and a name that fails
# to join across them would be classified from pandas-ta alone — reporting a
# path-dependent indicator as convergent, which is the exact error this lookup
# exists to prevent. These map SPELLINGS only; the classification still comes
# from talipp's own grouping.
_ALIASES = {
    "psar": "parabolicsar",
    "ad": "accudist",
    "adosc": "chaikinosc",
    "kvo": "kvo",
    "efi": "forceindex",
    "willr": "williams",
    "stochrsi": "stochrsi",
    "donchian": "donchianchannels",
    "kc": "keltnerchannels",
    "massi": "massindex",
    "ha": "heikinashi",  # path-dependent, absent from talipp → DIY persist
}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise McpToolError(
            f"Cannot read the reference document at {path}. The manual ships "
            "with this server under mcp/manual/ and is read from disk; this "
            "server is not useful for writing strategies without it."
        ) from exc


def _normalize(name: str) -> str:
    """Compare names across the two catalogues' conventions.

    pandas-ta writes lowercase snake_case (``supertrend``, ``willr``), talipp
    writes CamelCase (``SuperTrend``, ``Williams``).
    """
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _split_sections(text: str, marker: str) -> list[tuple[str, str]]:
    """Cut a document into (heading, body) pairs at the given heading level."""
    pattern = re.compile(rf"^{re.escape(marker)} (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.start():end].rstrip()))
    return sections


@lru_cache(maxsize=1)
def _talipp_index() -> dict[str, dict[str, Any]]:
    """talipp's indicators, each carrying the classification of its group.

    A ``###`` only counts as an indicator when its enclosing ``##`` group states
    an assignment — the document ends with prose sections ("Common patterns",
    "Anti-patterns") whose subsections are not indicators.
    """
    index: dict[str, dict[str, Any]] = {}
    for group_heading, group_body in _split_sections(_read(TALIPP_DOC), "##"):
        lowered = group_heading.lower()
        if "use talipp" in lowered:
            classification = PATH_DEPENDENT
        elif "convergent" in lowered:
            classification = CONVERGENT
        else:
            continue
        for name, body in _split_sections(group_body, "###"):
            index[_normalize(name)] = {
                "name": name,
                "classification": classification,
                "group": group_heading,
                "section": body,
            }
    return index


@lru_cache(maxsize=1)
def _pandas_ta_index() -> dict[str, dict[str, Any]]:
    """pandas-ta's indicators, keyed by name. Headings read ``name (Category)``."""
    index: dict[str, dict[str, Any]] = {}
    for heading, body in _split_sections(_read(PANDAS_TA_DOC), "#"):
        match = re.match(r"^([A-Za-z0-9_]+)\s*\((.+)\)$", heading)
        if not match:  # the document title and the "Category:" dividers
            continue
        name = match.group(1)
        index[_normalize(name)] = {
            "name": name,
            "category": match.group(2),
            "section": body,
        }
    return index


@lru_cache(maxsize=1)
def _decision_rule() -> str:
    """The Library Decision Rule, quoted rather than paraphrased."""
    for heading, body in _split_sections(_read(RUNTIME_DOC), "##"):
        if "library decision rule" in heading.lower():
            return body
    return ""


@lru_cache(maxsize=1)
def _path_dependent_names() -> frozenset[str]:
    """The path-dependent set as the Library Decision Rule itself names it.

    talipp's grouping covers what talipp implements; this covers the rest —
    Heikin-Ashi and Renko are path-dependent but absent from talipp, so they
    need the DIY persist recipe rather than a pandas-ta call. Without this they
    would be classified from pandas-ta alone and reported as safe.
    """
    rule = _decision_rule()
    marker = rule.find("engine.persist")
    if marker < 0:
        return frozenset()
    listed = re.search(r"\*\*(.+?)\*\*", rule[marker:], re.DOTALL)
    if not listed:
        return frozenset()
    names: set[str] = set()
    for raw in listed.group(1).replace("\n", " ").split(","):
        cleaned = _normalize(raw.split("/")[0])
        if cleaned:
            names.add(cleaned)
    return frozenset(names)


def _suggest(normalized: str, limit: int = 6) -> list[str]:
    """Names worth retrying, so a near-miss does not become an invented signature."""
    catalogue = {
        key: f"{entry['name']} ({library})"
        for index, library in ((_talipp_index(), "talipp"), (_pandas_ta_index(), "pandas-ta"))
        for key, entry in index.items()
    }
    close = difflib.get_close_matches(normalized, catalogue, n=limit, cutoff=0.6)
    return [catalogue[key] for key in close]


def lookup_indicator(name: str, library: str | None = None) -> dict[str, Any]:
    """Look one indicator up in the reference catalogues.

    Returns its documented signature plus which library must implement it —
    the mechanical decision that decides whether the strategy behaves the same
    in live as it did in the backtest.
    """
    if library is not None and library not in ("pandas_ta", "talipp"):
        raise McpToolError("library must be 'pandas_ta', 'talipp', or omitted")

    normalized = _normalize(name)
    if not normalized:
        raise McpToolError("name is required")

    talipp = _talipp_index().get(normalized) or _talipp_index().get(
        _ALIASES.get(normalized, "")
    )
    pandas_ta = _pandas_ta_index().get(normalized)

    if not talipp and not pandas_ta:
        return {
            "indicator": name,
            "found": False,
            "did_you_mean": _suggest(normalized),
            "note": (
                "Not in either catalogue under that name. Retry with one of the "
                "suggestions rather than writing a signature from memory — an "
                "invented constructor fails at runtime, and a guessed library "
                "assignment fails silently in live."
            ),
        }

    # talipp's grouping states the assignment for everything talipp implements.
    # For the rest, the Library Decision Rule's own list decides — it names the
    # path-dependent indicators talipp lacks (Heikin-Ashi, Renko), which need
    # the DIY persist recipe and would otherwise read as safe pandas-ta calls.
    aliased = _ALIASES.get(normalized, normalized)
    if talipp:
        classification = talipp["classification"]
    elif normalized in _path_dependent_names() or aliased in _path_dependent_names():
        classification = PATH_DEPENDENT
    else:
        classification = CONVERGENT

    path_dependent = classification == PATH_DEPENDENT
    if not path_dependent:
        binding = "pandas-ta, inline into a local numpy array"
    elif talipp:
        binding = "talipp + engine.persist"
    else:
        binding = "DIY engine.persist recipe (talipp does not implement it)"

    result: dict[str, Any] = {
        "indicator": (talipp or pandas_ta)["name"],
        "found": True,
        "classification": classification,
        "binding_library": binding,
    }
    if talipp:
        result["talipp_group"] = talipp["group"]

    wanted = library or ("talipp" if path_dependent else "pandas_ta")
    if wanted == "talipp" and talipp:
        result["reference"] = talipp["section"]
    elif wanted == "pandas_ta" and pandas_ta:
        result["reference"] = pandas_ta["section"]
        result["category"] = pandas_ta["category"]
    else:
        # Asked for a library that does not document it: give what exists
        # rather than nothing, and say which one this is.
        source = talipp or pandas_ta
        result["reference"] = source["section"]
        result["reference_from"] = "talipp" if talipp else "pandas-ta"
        result["note"] = (
            f"{result['indicator']} is not documented in the {wanted} catalogue; "
            "the reference above is the one that exists."
        )

    if path_dependent:
        result["why_it_matters"] = (
            "Path-dependent: its value depends on the whole history since the "
            "series started, so a sliding window corrupts it. Implemented with "
            "pandas-ta it passes the backtest — one pass over full history — and "
            "diverges in live, where the window slides and the state resets."
        )
        result["decision_rule"] = _decision_rule()
        if pandas_ta:
            result["trap"] = (
                f"pandas-ta also exposes {pandas_ta['name']}, and using it here is "
                "the classic error. The catalogue assignment is binding: this one "
                "goes through talipp + engine.persist."
            )

    return result
