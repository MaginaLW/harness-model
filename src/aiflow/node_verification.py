"""Pure validation of the Node V0 build-output contract.

These helpers do not execute tools or authenticate any supplied materials.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from pathlib import Path
from time import monotonic
from typing import Any, cast

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
COVERAGE_ISTANBUL_METHOD = "vitest-4.1.10-istanbul-vite-8.2.1-oxc-es2024-zero-hit-ts-ast-wire-v2"
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


def _closed_istanbul(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise _coverage_invalid("Istanbul input has unknown or missing fields")
    return cast(dict[str, Any], value)


def _node_json(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as error:
        raise _coverage_invalid("Node input is not finite canonical JSON") from error


def _hit(value: object) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_HITS:
        raise _coverage_invalid("Istanbul count is not a bounded nonnegative integer")
    return value


def _istanbul_ids(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or len(value) > 1_000_000:
        raise _coverage_invalid("Istanbul map is missing or exceeds its item limit")
    for identity in value:
        if (
            not isinstance(identity, str)
            or not re.fullmatch(r"0|[1-9][0-9]{0,15}", identity)
            or int(identity) > _MAX_HITS
        ):
            raise _coverage_invalid("Istanbul map identity is not canonical decimal")
    return cast(dict[str, Any], value)


def validate_node_istanbul_line_coverage(
    reports: Mapping[str, object],
    *,
    tracked_sources: Mapping[str, bytes],
    changed_lines: Mapping[str, Sequence[int]],
    deleted_sources: Sequence[str],
    catalog: Mapping[str, object],
) -> dict[str, object]:
    """Validate the rev2 wire protocol against an independently produced domain.

    The execution layer binds the catalog's producer, source and process bytes;
    this pure reader neither executes the producer nor authenticates its caller.
    """
    deadline = monotonic() + 30
    if len(_node_json(reports)) > 16 * 1024 * 1024 or len(_node_json(catalog)) > 16 * 1024 * 1024:
        raise _coverage_invalid("Istanbul JSON exceeds its byte limit")
    domain = _closed_istanbul(
        catalog, {"kind", "producer", "transform", "typescript_parser", "files"}
    )
    if (
        domain["kind"] != "independent-istanbul-zero-hit-domain-v1"
        or domain["producer"] != "@vitest/coverage-istanbul@4.1.10"
        or domain["transform"] != "vite@8.2.1-oxc-es2024"
        or domain["typescript_parser"] != "@babel/parser@7.29.12"
        or not all(isinstance(x, Mapping) for x in (reports, tracked_sources, changed_lines))
        or not isinstance(domain["files"], Mapping)
        or any(
            len(x) > MAX_PATHS for x in (reports, tracked_sources, changed_lines, domain["files"])
        )
    ):
        raise _coverage_invalid("Independent Istanbul catalog contract is invalid")
    sources = _ordered_paths(
        sorted((_path(path) for path in tracked_sources), key=lambda path: path.encode("utf-8"))
    )
    if (
        set(domain["files"]) != set(sources)
        or not set(reports).issubset(sources)
        or any(not path.startswith("src/local/") or not path.endswith(".ts") for path in sources)
    ):
        raise _coverage_invalid("Istanbul source inventories disagree")
    deleted = _ordered_paths(deleted_sources)
    if set(deleted) & set(sources):
        raise _coverage_invalid("A deleted source remains in the Istanbul subject")
    changed: dict[str, tuple[int, ...]] = {}
    for path, numbers in changed_lines.items():
        _path(path)
        if (
            not isinstance(numbers, (list, tuple))
            or len(numbers) > MAX_PATHS
            or any(type(number) is not int or number < 1 for number in numbers)
            or list(numbers) != sorted(set(numbers))
        ):
            raise _coverage_invalid("Changed lines must be ordered unique positive integers")
        if path in tracked_sources:
            changed[path] = _line_numbers(numbers, _source_lines(tracked_sources[path]))
        elif path not in deleted and re.search(r"\.(?:[cm]?[jt]sx?|ps1|cs)$", path, re.IGNORECASE):
            if not path.startswith("tests/local/") or not path.endswith(".ts"):
                raise _coverage_invalid("Changed production execution input is not covered")
    total = covered = diff_total = diff_covered = 0
    for path in sources:
        if monotonic() > deadline:
            raise ContractError(
                "TypeScript coverage calculation timed out", code="NODE_COVERAGE_TIMEOUT"
            )
        data = tracked_sources[path]
        lines = _source_lines(data)
        boundaries: dict[int, set[int]] = {}
        entry = domain["files"][path]
        if not isinstance(entry, Mapping):
            raise _coverage_invalid("Independent Istanbul source entry is invalid")
        empty = "empty_domain" in entry
        row = _closed_istanbul(
            entry, {"sha256", "lines", "implicit_else"} | ({"empty_domain"} if empty else set())
        )
        if row["sha256"] != hashlib.sha256(data).hexdigest():
            raise _coverage_invalid("Independent Istanbul source bytes differ")
        expected = _line_numbers(row["lines"], lines)
        tuples = row["implicit_else"]
        if not isinstance(tuples, list) or len(tuples) > 1_000_000:
            raise _coverage_invalid("Implicit-else catalog must be a bounded array")
        allowed: set[bytes] = set()
        for item in tuples:
            certificate = _closed_istanbul(
                item, {"parent", "locations", "type", "ast_start", "ast_end"}
            )
            locations = certificate["locations"]
            if (
                certificate["type"] != "if"
                or not isinstance(locations, list)
                or len(locations) != 2
                or _node_json(locations[1]) != b'{"end":{},"start":{}}'
            ):
                raise _coverage_invalid("Implicit-else catalog has an invalid slot or type")
            _source_range(certificate["parent"], lines, boundaries, deadline)
            _source_range(locations[0], lines, boundaries, deadline)
            start = _position(certificate["ast_start"], lines, boundaries, deadline)
            end = _position(certificate["ast_end"], lines, boundaries, deadline)
            parent = certificate["parent"]
            if (
                _node_json(parent["start"]) != _node_json(certificate["ast_start"])
                or parent["end"]["line"] != end[0]
                or end < start
            ):
                raise _coverage_invalid("Implicit-else original AST span differs")
            column = parent["end"]["column"]
            if column is not None and column != end[1]:
                text = lines[end[0] - 1].encode("utf-16-le")
                trailing_space = column == end[1] + 1 and text[end[1] * 2 : column * 2] == b" \x00"
                # The fixed authenticated producer proves the AST/token identity;
                # this pure reader checks the same bound source's UTF-16 geometry.
                terminal_semicolon = (
                    column == end[1] - 1 and text[column * 2 : end[1] * 2] == b";\x00"
                )
                if not trailing_space and not terminal_semicolon:
                    raise _coverage_invalid("Implicit-else mapped end is not proved trivia")
            key = _node_json({k: certificate[k] for k in ("parent", "locations", "type")})
            if key in allowed:
                raise _coverage_invalid("Implicit-else catalog contains a duplicate tuple")
            allowed.add(key)
        if empty:
            proof = _closed_istanbul(row["empty_domain"], {"kind", "statements"})
            if (
                proof["kind"] != "named_source_reexports_only_v1"
                or type(proof["statements"]) is not int
                or not 0 < proof["statements"] <= MAX_PATHS
                or expected
                or tuples
            ):
                raise _coverage_invalid("Empty Istanbul source certificate is invalid")
        if path not in reports:
            if not empty:
                raise _coverage_invalid("Executable Istanbul source report is missing")
            continue
        report = _closed_istanbul(
            reports[path], {"path", "statementMap", "fnMap", "branchMap", "s", "f", "b"}
        )
        if report["path"] != path:
            raise _coverage_invalid("Istanbul source report identity differs")
        statements, hits = _istanbul_ids(report["statementMap"]), _istanbul_ids(report["s"])
        functions, function_hits = _istanbul_ids(report["fnMap"]), _istanbul_ids(report["f"])
        branches, branch_hits = _istanbul_ids(report["branchMap"]), _istanbul_ids(report["b"])
        if (
            set(statements) != set(hits)
            or set(functions) != set(function_hits)
            or set(branches) != set(branch_hits)
        ):
            raise _coverage_invalid("Istanbul counter and source-map identities disagree")
        if empty and any((statements, hits, functions, function_hits, branches, branch_hits)):
            raise _coverage_invalid("An empty source has executable Istanbul maps")
        for identity, function in functions.items():
            function = _closed_istanbul(function, {"decl", "loc", "name"})
            if not isinstance(function["name"], str) or len(function["name"]) > 16 * 1024 * 1024:
                raise _coverage_invalid("Istanbul function name is invalid")
            for role in ("decl", "loc"):
                _source_range(function[role], lines, boundaries, deadline)
            _hit(function_hits[identity])
        consumed: set[bytes] = set()
        for identity, branch in branches.items():
            branch = _closed_istanbul(branch, {"loc", "locations", "type"})
            locations, counts = branch["locations"], branch_hits[identity]
            if (
                not isinstance(branch["type"], str)
                or branch["type"] not in {"if", "binary-expr", "cond-expr", "default-arg", "switch"}
                or not isinstance(locations, list)
                or not locations
                or not isinstance(counts, list)
                or len(counts) != len(locations)
                or len(counts) > 1_000_000
            ):
                raise _coverage_invalid(
                    "Istanbul branch type, locations or counter arity is invalid"
                )
            _source_range(branch["loc"], lines, boundaries, deadline)
            for index, location in enumerate(locations):
                _hit(counts[index])
                if _node_json(location) == b'{"end":{},"start":{}}':
                    key = _node_json(
                        {"parent": branch["loc"], "locations": locations, "type": branch["type"]}
                    )
                    if index != 1 or key not in allowed or key in consumed:
                        raise _coverage_invalid("Istanbul implicit else is not uniquely certified")
                    consumed.add(key)
                else:
                    _source_range(location, lines, boundaries, deadline)
        if consumed != allowed:
            raise _coverage_invalid("Istanbul implicit-else catalog is incomplete or unused")
        line_hits: dict[int, int] = {}
        for identity, statement in statements.items():
            start = _source_range(statement, lines, boundaries, deadline)
            count = _hit(hits[identity])
            line_hits[start[0]] = max(line_hits.get(start[0], 0), count)
        if set(line_hits) != set(expected):
            raise _coverage_invalid("Istanbul executable lines differ from the independent domain")
        candidates = set(changed.get(path, ())) & set(expected)
        total += len(expected)
        covered += sum(count > 0 for count in line_hits.values())
        diff_total += len(candidates)
        diff_covered += sum(line_hits[line] > 0 for line in candidates)
    if total and covered * 100 < total * 85:
        raise ContractError(
            "Total TypeScript line coverage is below 85%", code="NODE_TOTAL_COVERAGE_LOW"
        )
    if diff_total and diff_covered * 100 < diff_total * 90:
        raise ContractError(
            "Changed TypeScript line coverage is below 90%", code="NODE_DIFF_COVERAGE_LOW"
        )
    return {
        "scope_files": len(sources),
        "total": {"covered": covered, "executable": total, "threshold": 85},
        "changed": {
            "covered": diff_covered,
            "executable": diff_total,
            "threshold": 90,
            "applicability": "applicable" if diff_total else "not_applicable",
        },
        "method": COVERAGE_ISTANBUL_METHOD,
    }


PRODUCT_TESTS = (
    (
        "acceptance",
        "tests/local/personal-dot-integration.test.ts",
        "personal dot authenticated MCP + unified WeChat host (offline)",
        "persists duplicate input once, publishes one event, executes original text once "
        "and replies to the saved conversation once",
    ),
    (
        "acceptance",
        "tests/local/personal-dot-integration.test.ts",
        "personal dot authenticated MCP + unified WeChat host (offline)",
        "rejects unauthenticated event calls, foreign targets and direct submissions "
        "before any dispatch",
    ),
    (
        "integration",
        "tests/local/weixin-shared-integration.test.ts",
        "synthetic Weixin, HTTP and shared runtime integration",
        "persists a polled task contract and returns its terminal result "
        "through the same shared host",
    ),
    (
        "integration",
        "tests/local/weixin-shared-integration.test.ts",
        "synthetic Weixin, HTTP and shared runtime integration",
        "runs the isolated shared host with durable duplicate and uncertain reply handling",
    ),
    (
        "integration",
        "tests/local/weixin-shared-integration.test.ts",
        "synthetic Weixin, HTTP and shared runtime integration",
        "shares route-bound tasks, reads, stop and client lifetime with a second client",
    ),
)


def validate_node_product_tests(
    report: Mapping[str, object],
    *,
    execution_root: Path,
    tracked_tests: Mapping[str, bytes],
    expected_coverage: Mapping[str, object],
) -> dict[str, object]:
    """Read the fixed full Vitest JSON protocol; process provenance is separate."""
    if len(_node_json(report)) > 16 * 1024 * 1024:
        raise _coverage_invalid("Vitest JSON exceeds its byte limit")
    fields = {
        "coverageMap",
        "numFailedTestSuites",
        "numFailedTests",
        "numPassedTestSuites",
        "numPassedTests",
        "numPendingTestSuites",
        "numPendingTests",
        "numTodoTests",
        "numTotalTestSuites",
        "numTotalTests",
        "snapshot",
        "startTime",
        "success",
        "testResults",
    }
    value = _closed_istanbul(report, fields)
    if value["success"] is not True or _node_json(value["coverageMap"]) != _node_json(
        expected_coverage
    ):
        raise _coverage_invalid("Vitest report failed or its same-run coverage differs")
    for name in fields:
        if name.startswith("num"):
            _hit(value[name])
    if (
        any(
            value[name] != 0
            for name in (
                "numFailedTestSuites",
                "numFailedTests",
                "numPendingTestSuites",
                "numPendingTests",
                "numTodoTests",
            )
        )
        or not 0 < value["numTotalTestSuites"] == value["numPassedTestSuites"]
    ):
        raise _coverage_invalid("Vitest reports incomplete or failed suites/tests")

    def timing(number: object) -> float:
        if type(number) not in (int, float):
            raise _coverage_invalid("Vitest timing is not finite and nonnegative")
        try:
            value = float(cast(Any, number))
        except OverflowError as error:
            raise _coverage_invalid("Vitest timing exceeds its finite range") from error
        if not math.isfinite(value) or value < 0:
            raise _coverage_invalid("Vitest timing is not finite and nonnegative")
        return value

    timing(value["startTime"])
    snapshot = _closed_istanbul(
        value["snapshot"],
        {
            "added",
            "didUpdate",
            "failure",
            "filesAdded",
            "filesRemoved",
            "filesRemovedList",
            "filesUnmatched",
            "filesUpdated",
            "matched",
            "total",
            "unchecked",
            "uncheckedKeysByFile",
            "unmatched",
            "updated",
        },
    )
    for name, number in snapshot.items():
        if name not in {"didUpdate", "failure", "filesRemovedList", "uncheckedKeysByFile"}:
            _hit(number)
    if (
        snapshot["didUpdate"] is not False
        or snapshot["failure"] is not False
        or snapshot["filesRemovedList"] != []
        or snapshot["uncheckedKeysByFile"] != []
        or snapshot["matched"] != snapshot["total"]
        or any(
            snapshot[name] != 0
            for name in (
                "added",
                "filesAdded",
                "filesRemoved",
                "filesUnmatched",
                "filesUpdated",
                "unchecked",
                "unmatched",
                "updated",
            )
        )
    ):
        raise _coverage_invalid("Vitest snapshot results are incomplete or modified")
    paths = _ordered_paths(
        sorted((_path(path) for path in tracked_tests), key=lambda path: path.encode("utf8"))
    )
    if any(not path.startswith("tests/local/") or not path.endswith(".test.ts") for path in paths):
        raise _coverage_invalid("Vitest expected test inventory is outside the fixed full suite")
    inventory = []
    for path in paths:
        data = tracked_tests[path]
        if not isinstance(data, bytes):
            raise _coverage_invalid("Vitest test inventory requires bound source bytes")
        inventory.append({"file": path, "sha256": hashlib.sha256(data).hexdigest()})
    files = value["testResults"]
    if not isinstance(files, list) or not files or len(files) > MAX_PATHS:
        raise _coverage_invalid("Vitest file inventory is missing or too large")
    selected = {(file, ancestor + " " + title): 0 for _, file, ancestor, title in PRODUCT_TESTS}
    found: set[str] = set()
    assertion_count = 0
    for raw_file in files:
        file = _closed_istanbul(
            raw_file, {"assertionResults", "endTime", "message", "name", "startTime", "status"}
        )
        if not isinstance(file["name"], str):
            raise _coverage_invalid("Vitest file name is invalid")
        absolute = Path(file["name"])
        if not absolute.is_absolute() or not absolute.is_relative_to(execution_root):
            raise _coverage_invalid("Vitest report contains a foreign file")
        path = _path(absolute.relative_to(execution_root).as_posix())
        if path not in tracked_tests or path in found:
            raise _coverage_invalid("Vitest report contains an unknown or duplicate file")
        found.add(path)
        if (
            file["status"] != "passed"
            or file["message"] != ""
            or timing(file["endTime"]) < timing(file["startTime"])
        ):
            raise _coverage_invalid("Vitest file did not completely pass")
        assertions = file["assertionResults"]
        if not isinstance(assertions, list) or len(assertions) > 1_000_000:
            raise _coverage_invalid("Vitest assertion inventory is invalid")
        for raw_case in assertions:
            case = _closed_istanbul(
                raw_case,
                {
                    "ancestorTitles",
                    "duration",
                    "failureMessages",
                    "fullName",
                    "meta",
                    "status",
                    "tags",
                    "title",
                },
            )
            ancestors = case["ancestorTitles"]
            if (
                not isinstance(ancestors, list)
                or len(ancestors) > MAX_PATHS
                or not all(
                    isinstance(title, str) and len(title) <= 16 * 1024 * 1024 for title in ancestors
                )
                or not isinstance(case["title"], str)
                or not case["title"]
                or len(case["title"]) > 16 * 1024 * 1024
                or case["fullName"] != " ".join([*ancestors, case["title"]])
                or case["status"] != "passed"
                or case["failureMessages"] != []
                or not isinstance(case["meta"], dict)
                or case["meta"] != {}
                or case["tags"] != []
            ):
                raise _coverage_invalid("Vitest assertion is malformed or did not pass")
            timing(case["duration"])
            selector = (path, case["fullName"])
            if selector in selected:
                selected[selector] += 1
                expected_ancestor = next(
                    a for _, f, a, title in PRODUCT_TESTS if (f, a + " " + title) == selector
                )
                if ancestors != [expected_ancestor]:
                    raise _coverage_invalid("Vitest product tuple has a different ancestry")
            assertion_count += 1
            if assertion_count > 1_000_000:
                raise _coverage_invalid("Vitest assertion inventory exceeds its bound")
    if (
        found != set(paths)
        or any(count != 1 for count in selected.values())
        or value["numPassedTests"] != value["numTotalTests"]
        or value["numTotalTests"] != assertion_count
    ):
        raise _coverage_invalid("Vitest full suite or selected product inventory is incomplete")
    return {
        "inventory_sha256": hashlib.sha256(
            _node_json({"tests": inventory, "products": PRODUCT_TESTS})
        ).hexdigest(),
        "acceptance": [
            {"file": f, "full_name": a + " " + t}
            for c, f, a, t in PRODUCT_TESTS
            if c == "acceptance"
        ],
        "integration": [
            {"file": f, "full_name": a + " " + t}
            for c, f, a, t in PRODUCT_TESTS
            if c == "integration"
        ],
        "file_count": len(files),
        "assertion_count": assertion_count,
        "suite_count": value["numTotalTestSuites"],
    }
