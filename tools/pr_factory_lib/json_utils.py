from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


_SAVED_JSON_PATH_RX = re.compile(r"^SAVED_JSON_PATH\s*=\s*(?P<value>.+?)\s*$")


@dataclass(frozen=True)
class ParsedStageOutput:
    payload: Dict[str, Any]
    source_kind: str
    source_path: str
    source_sha256: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_reported_json_path(raw_value: str, cwd: Optional[Path]) -> Path:
    candidate = Path(raw_value).expanduser()
    if candidate.is_absolute() or cwd is None:
        return candidate
    return (cwd / candidate).resolve()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_stage_output_with_provenance(stdout: str, cwd: Optional[Path] = None) -> ParsedStageOutput:
    """
    Parse a stage's stdout into JSON payload.

    Supports:
    - Raw JSON on stdout
    - `SAVED_JSON_PATH=/abs/path.json` marker, where the file contains JSON
    """
    text = stdout.strip()
    if not text:
        raise ValueError("Stage produced empty stdout; expected JSON.")
    try:
        return ParsedStageOutput(
            payload=json.loads(text),
            source_kind="stdout",
            source_path="",
            source_sha256=_sha256_bytes(text.encode("utf-8")),
        )
    except json.JSONDecodeError as exc:
        json_path: Path | None = None
        for line in text.splitlines():
            path_match = _SAVED_JSON_PATH_RX.match(line.strip())
            if not path_match:
                continue
            raw_value = path_match.group("value").strip()
            if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
                raw_value = raw_value[1:-1]
            json_path = _resolve_reported_json_path(raw_value, cwd)
            break

        if json_path is None:
            raise ValueError(f"Stage stdout is not valid JSON: {exc}") from exc

        if not json_path.is_file():
            raise ValueError(f"Stage reported SAVED_JSON_PATH but file does not exist: {json_path}") from exc

        try:
            raw_bytes = json_path.read_bytes()
            payload = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError as file_exc:
            raise ValueError(
                f"Stage SAVED_JSON_PATH is not valid JSON ({json_path}): {file_exc}"
            ) from file_exc
        return ParsedStageOutput(
            payload=payload,
            source_kind="saved_json_path",
            source_path=str(json_path.resolve()),
            source_sha256=_sha256_bytes(raw_bytes),
        )


def parse_stage_output(stdout: str, cwd: Optional[Path] = None) -> Dict[str, Any]:
    return parse_stage_output_with_provenance(stdout=stdout, cwd=cwd).payload
