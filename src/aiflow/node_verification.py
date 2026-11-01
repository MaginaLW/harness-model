"""Pure validation of the Node V0 build-output contract.

These helpers do not execute tools or authenticate any supplied materials.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from time import monotonic

from aiflow.errors import ContractError

MAX_PATHS = 65_536
MAX_PATH_BYTES = 1_024
MAX_PATH_SEGMENTS = 64
_WINDOWS_DEVICES = frozenset(
    {"con", "prn", "aux", "nul", "conin$", "conout$"}
    | {f"{prefix}{number}" for prefix in ("com", "lpt") for number in "123456789¹²³"}
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _invalid(message: str) -> ContractError:
    return ContractError(message, code="NODE_OUTPUT_INVALID")


def _path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise _invalid("Node output path must be a canonical relative file path")
    if len(value) > MAX_PATH_BYTES:
        raise _invalid("Node path exceeds the size limit")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as error:
        raise _invalid("Node output path is not valid UTF-8") from error
    if len(encoded) > MAX_PATH_BYTES:
        raise _invalid("Node path exceeds the size limit")
    if unicodedata.normalize("NFC", value) != value:
        raise _invalid("Node output path must be a canonical relative file path")
    segments = value.split("/")
    if len(segments) > MAX_PATH_SEGMENTS:
        raise _invalid("Node path exceeds the segment limit")
    if any(
        not segment
        or segment in {".", ".."}
        or segment[-1] in {".", " "}
        or any(unicodedata.category(char) == "Cc" or char in '\\:*?"<>|' for char in segment)
        or segment.split(".", 1)[0].rstrip(" ").casefold() in _WINDOWS_DEVICES
        for segment in segments
    ):
        raise _invalid("Node output path must be a canonical relative file path")
    return value


def _ordered_paths(paths: object) -> tuple[str, ...]:
    if not isinstance(paths, (tuple, list)):
        raise _invalid("Node output paths must be an array")
    if len(paths) > MAX_PATHS:
        raise _invalid("Node path list exceeds the item limit")
    result = tuple(_path(item) for item in paths)
    if result != tuple(sorted(set(result), key=lambda path: path.encode("utf-8"))):
        raise _invalid("Node output paths must be UTF-8 sorted and unique")
    folded = [path.casefold() for path in result]
    if len(set(folded)) != len(folded):
        raise _invalid("Node output paths contain case aliases")
    folded_set = set(folded)
    for path in folded:
        segments = path.split("/")
        if any("/".join(segments[:index]) in folded_set for index in range(1, len(segments))):
            raise _invalid("Node output paths cannot contain one another")
    return result


def _output_paths(paths: object) -> tuple[str, ...]:
    outputs = _ordered_paths(paths)
    if any(segment.casefold() == ".git" for path in outputs for segment in path.split("/")):
        raise _invalid("Node output cannot occupy a Git administration path")
    return outputs


def _projection(value: object) -> dict[str, tuple[str, str]]:
    if not isinstance(value, (list, tuple)):
        raise _invalid("Node state projection must be an array")
    if len(value) > MAX_PATHS:
        raise _invalid("Node state projection exceeds the item limit")
    result: dict[str, tuple[str, str]] = {}
    paths: list[str] = []
    for entry in value:
        if (
            not isinstance(entry, Mapping)
            or len(entry) != 3
            or set(entry) != {"path", "git_status", "sha256"}
        ):
            raise _invalid("Node state projection entry is invalid")
        path = _path(entry["path"])
        status = entry["git_status"]
        digest = entry["sha256"]
        if status not in ("tracked", "untracked", "ignored") or not isinstance(digest, str):
            raise _invalid("Node state projection contains unknown state")
        if len(digest) != 64 or not _SHA256.fullmatch(digest):
            raise _invalid("Node state projection has an invalid digest")
        paths.append(path)
        result[path] = (status, digest)
    _ordered_paths(paths)
    return result


def validate_node_v0_output_delta(
    before: Sequence[Mapping[str, object]],
    after: Sequence[Mapping[str, object]],
    outputs: Sequence[str],
    *,
    protected_paths: Sequence[str],
    reserved_paths: Sequence[str],
) -> None:
    """Validate full before/after projections against declared exact output files.

    The caller must independently reconstruct both projections from controlled
    originals, establish that every entry is a safe regular file with stable
    object identity, and supply the complete tracked and installed file inventory
    as protected paths. Upstream file reads and enumeration must also be bounded.
    Reserved audit paths prevent output conflicts even when separately authorized
    exclusions omit them from the projections; the caller must supply and prove
    the complete exclusion list. Audit
    exclusions themselves must be independently verified. Never pass evidence's
    self-reported projections as these facts. This function does not establish
    those prerequisites or execute a runner.
    """
    declared = _output_paths(outputs)
    protected = _ordered_paths(protected_paths)
    reserved = _ordered_paths(reserved_paths)
    before_state, after_state = _projection(before), _projection(after)
    all_paths = (
        set(declared) | set(protected) | set(reserved) | set(before_state) | set(after_state)
    )
    aliases: dict[str, str] = {}
    for path in all_paths:
        folded = path.casefold()
        if folded in aliases and aliases[folded] != path:
            raise _invalid("Node paths contain case aliases")
        aliases[folded] = path
    restricted = sorted({path.casefold() for path in (*protected, *reserved)})
    restricted_set = set(restricted)
    for output in declared:
        folded = output.casefold()
        segments = folded.split("/")
        if any(
            "/".join(segments[:index]) in restricted_set for index in range(1, len(segments) + 1)
        ):
            raise _invalid("Node output conflicts with a protected path")
        prefix = folded + "/"
        position = bisect_left(restricted, prefix)
        if position < len(restricted) and restricted[position].startswith(prefix):
            raise _invalid("Node output conflicts with a protected path")
    declared_set, protected_set = set(declared), set(protected)
    if any(
        path not in before_state
        or path not in after_state
        or before_state[path] != after_state[path]
        for path in protected
    ):
        raise _invalid("Node protected files must exist and remain unchanged")
    for path in set(before_state) | set(after_state):
        if path not in declared_set and path not in protected_set:
            raise _invalid("Node state contains an undeclared path")
        old, new = before_state.get(path), after_state.get(path)
        if old is not None and new is None:
            raise _invalid("Node state contains a deleted file")
        if path not in protected_set and new is not None:
            if new[0] not in ("untracked", "ignored") or (old is not None and old[0] != new[0]):
                raise _invalid("Node output has an invalid Git status")


COVERAGE_METHOD = "vite-8.2.1-oxc-es2024-ast-v8-to-istanbul-zero-hit-v1"
_MAX_HITS = 2**53 - 1


def _coverage_invalid(message: str) -> ContractError:
    return ContractError(message, code="NODE_COVERAGE_INVALID")


def _source_lines(contents: object) -> list[str]:
    if not isinstance(contents, bytes):
        raise _coverage_invalid("Coverage source must be bound UTF-8 bytes")
    try:
        text = contents.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise _coverage_invalid("Coverage source is not valid UTF-8") from error
    if re.search(r"(?:istanbul|v8|c8)\s+ignore", text, re.IGNORECASE):
        raise _coverage_invalid("Production coverage ignore directives are forbidden")
    return re.split(r"\r\n|[\r\n\u2028\u2029]", text)


def _line_numbers(value: object, lines: list[str]) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > len(lines):
        raise _coverage_invalid("Executable lines must be a bounded ordered array")
    result: list[int] = []
    for number in value:
        if type(number) is not int or not 1 <= number <= len(lines):
            raise _coverage_invalid("Executable line is outside the source")
        if result and number <= result[-1]:
            raise _coverage_invalid("Executable lines must be sorted and unique")
        result.append(number)
    return tuple(result)


def _position(
    value: object,
    lines: list[str],
    boundaries_cache: dict[int, set[int]],
    deadline: float,
    *,
    allow_line_end: bool = False,
) -> tuple[int, int]:
    if monotonic() > deadline:
        raise ContractError(
            "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
        )
    if not isinstance(value, Mapping) or set(value) != {"line", "column"}:
        raise _coverage_invalid("Statement coordinate is invalid")
    line, column = value["line"], value["column"]
    if (
        type(line) is not int
        or not 1 <= line <= len(lines)
        or (type(column) is not int and not (allow_line_end and column is None))
    ):
        raise _coverage_invalid("Statement coordinate is outside the source")
    boundaries = boundaries_cache.get(line)
    if boundaries is None:
        boundaries = {0}
        offset = 0
        for index, character in enumerate(lines[line - 1]):
            if index % 4096 == 0 and monotonic() > deadline:
                raise ContractError(
                    "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
                )
            offset += 2 if ord(character) > 0xFFFF else 1
            boundaries.add(offset)
        boundaries_cache[line] = boundaries
    # The bound converter's Infinity end marker is serialized as JSON null.
    # Derive a finite offset from the original source; never rewrite the report.
    if column is None:
        column = max(boundaries)
    if column not in boundaries:
        raise _coverage_invalid("Statement column splits a character or exceeds source content")
    return line, column


def _source_range(
    value: object, lines: list[str], boundaries_cache: dict[int, set[int]], deadline: float
) -> tuple[int, int]:
    if not isinstance(value, Mapping) or set(value) != {"start", "end"}:
        raise _coverage_invalid("Coverage source range is invalid")
    start = _position(value["start"], lines, boundaries_cache, deadline)
    end = _position(value["end"], lines, boundaries_cache, deadline, allow_line_end=True)
    if end < start:
        raise _coverage_invalid("Coverage source range is reversed")
    return start


def _auxiliary_source_map(
    value: object,
    name: str,
    lines: list[str],
    boundaries_cache: dict[int, set[int]],
    deadline: float,
) -> None:
    if not isinstance(value, Mapping):
        raise _coverage_invalid("Coverage auxiliary source map is invalid")
    allowed_ends: set[tuple[object, ...]] = set()
    for identity, entry in value.items():
        if monotonic() > deadline:
            raise ContractError(
                "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
            )
        if not isinstance(identity, str) or not isinstance(entry, Mapping):
            raise _coverage_invalid("Coverage auxiliary source entry is invalid")
        for role in ("decl", "loc") if name == "fnMap" else ("loc",):
            if role in entry:
                _source_range(entry[role], lines, boundaries_cache, deadline)
                allowed_ends.add((identity, role, "end"))
        if name == "branchMap" and "locations" in entry:
            if not isinstance(entry["locations"], list):
                raise _coverage_invalid("Coverage branch locations are invalid")
            for index, location in enumerate(entry["locations"]):
                _source_range(location, lines, boundaries_cache, deadline)
                allowed_ends.add((identity, "locations", index, "end"))
    pending: list[tuple[object, tuple[object, ...]]] = [
        (entry, (identity,)) for identity, entry in value.items()
    ]
    while pending:
        if monotonic() > deadline:
            raise ContractError(
                "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
            )
        entry, path = pending.pop()
        if isinstance(entry, Mapping):
            if "line" in entry and "column" in entry:
                _position(
                    entry,
                    lines,
                    boundaries_cache,
                    deadline,
                    allow_line_end=path in allowed_ends,
                )
            elif "line" in entry and (
                type(entry["line"]) is not int or not 1 <= entry["line"] <= len(lines)
            ):
                raise _coverage_invalid("Coverage auxiliary source line is invalid")
            pending.extend((child, (*path, key)) for key, child in entry.items())
        elif isinstance(entry, list):
            pending.extend((child, (*path, index)) for index, child in enumerate(entry))
        elif entry is None and path[:-1] not in allowed_ends:
            raise _coverage_invalid("Coverage auxiliary null is not a source range end")


def validate_node_line_coverage(
    reports: Mapping[str, object],
    *,
    tracked_sources: Mapping[str, bytes],
    changed_lines: Mapping[str, Sequence[int]],
    deleted_sources: Sequence[str],
    expected_executable_lines: Mapping[str, Sequence[int]],
) -> dict[str, object]:
    """Recompute Istanbul line coverage from complete, independently bound maps.

    This pure function does not prove provenance of the originals. The execution
    service binds their bytes and the complete Git source and diff inventories.
    """
    deadline = monotonic() + 30
    if not all(
        isinstance(value, Mapping)
        for value in (reports, tracked_sources, expected_executable_lines, changed_lines)
    ):
        raise _coverage_invalid("Coverage inputs must be complete mappings")
    if any(
        len(value) > MAX_PATHS
        for value in (reports, tracked_sources, changed_lines, expected_executable_lines)
    ):
        raise _coverage_invalid("Coverage inventory exceeds the item limit")
    source_paths = _ordered_paths(
        sorted((_path(path) for path in tracked_sources), key=lambda path: path.encode("utf-8"))
    )
    if set(reports) != set(source_paths) or set(expected_executable_lines) != set(source_paths):
        raise _coverage_invalid("Coverage and executable maps must include every tracked source")
    if any(not path.startswith("src/local/") or not path.endswith(".ts") for path in source_paths):
        raise _coverage_invalid("Coverage scope is restricted to production local TypeScript")
    deleted = _ordered_paths(deleted_sources)
    if set(deleted) & set(source_paths):
        raise _coverage_invalid("A deleted source is still in the subject inventory")
    changed: dict[str, tuple[int, ...]] = {}
    for path, numbers in changed_lines.items():
        _path(path)
        if (
            not isinstance(numbers, (list, tuple))
            or len(numbers) > MAX_PATHS
            or any(type(number) is not int or number < 1 for number in numbers)
            or list(numbers) != sorted(set(numbers))
        ):
            raise _coverage_invalid("Changed lines must be sorted unique positive integers")
        if path in tracked_sources:
            changed[path] = _line_numbers(numbers, _source_lines(tracked_sources[path]))
        elif path not in deleted and re.search(r"\.(?:[cm]?[jt]sx?|ps1|cs)$", path, re.IGNORECASE):
            if not path.startswith("tests/local/") or not path.endswith(".ts"):
                raise _coverage_invalid("Changed production execution input is not covered")
    total = covered = diff_total = diff_covered = 0
    for path in source_paths:
        if monotonic() > deadline:
            raise ContractError(
                "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
            )
        lines = _source_lines(tracked_sources[path])
        boundaries_cache: dict[int, set[int]] = {}
        expected = _line_numbers(expected_executable_lines[path], lines)
        report = reports[path]
        if not isinstance(report, Mapping) or report.get("path") != path:
            raise _coverage_invalid("Coverage source identity is invalid")
        for name in ("f", "b"):
            auxiliary = report.get(name, {})
            if not isinstance(auxiliary, Mapping):
                raise _coverage_invalid("Coverage auxiliary counters are invalid")
            for value in auxiliary.values():
                counts = value if name == "b" else [value]
                if not isinstance(counts, list) or any(
                    type(count) is not int or not 0 <= count <= _MAX_HITS for count in counts
                ):
                    raise _coverage_invalid("Coverage auxiliary hit count is invalid")
        for name in ("fnMap", "branchMap"):
            _auxiliary_source_map(report.get(name, {}), name, lines, boundaries_cache, deadline)
        statement_map, hits = report.get("statementMap"), report.get("s")
        if not isinstance(statement_map, Mapping) or not isinstance(hits, Mapping):
            raise _coverage_invalid("Coverage statement map is missing")
        if set(statement_map) != set(hits) or len(statement_map) > 1_000_000:
            raise _coverage_invalid("Coverage statement identities do not match")
        line_hits: dict[int, int] = {}
        for identity, statement in statement_map.items():
            if monotonic() > deadline:
                raise ContractError(
                    "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
                )
            if not isinstance(identity, str) or not isinstance(statement, Mapping):
                raise _coverage_invalid("Coverage statement is invalid")
            start = _source_range(statement, lines, boundaries_cache, deadline)
            count = hits[identity]
            if type(count) is not int or not 0 <= count <= _MAX_HITS:
                raise _coverage_invalid("Coverage statement range or count is invalid")
            line_hits[start[0]] = max(line_hits.get(start[0], 0), count)
        if set(line_hits) != set(expected):
            raise _coverage_invalid("Coverage executable lines differ from the independent map")
        candidates = set(changed.get(path, ())) & set(expected)
        total += len(expected)
        covered += sum(count > 0 for count in line_hits.values())
        diff_total += len(candidates)
        diff_covered += sum(line_hits[line] > 0 for line in candidates)
    if monotonic() > deadline:
        raise ContractError(
            "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
        )
    if total and covered * 100 < total * 85:
        raise ContractError(
            "Total TypeScript line coverage is below 85%", code="NODE_TOTAL_COVERAGE_LOW"
        )
    if diff_total and diff_covered * 100 < diff_total * 90:
        raise ContractError(
            "Changed TypeScript line coverage is below 90%", code="NODE_DIFF_COVERAGE_LOW"
        )
    return {
        "scope_files": len(source_paths),
        "total": {"covered": covered, "executable": total, "threshold": 85},
        "changed": {
            "covered": diff_covered,
            "executable": diff_total,
            "threshold": 90,
            "applicability": "applicable" if diff_total else "not_applicable",
        },
        "method": COVERAGE_METHOD,
    }
