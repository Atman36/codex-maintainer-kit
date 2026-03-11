from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict


_SAVED_JSON_PATH_RX = re.compile(r"^SAVED_JSON_PATH\s*=\s*(?P<value>.+?)\s*$")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_stage_output(stdout: str) -> Dict[str, Any]:
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
        return json.loads(text)
    except json.JSONDecodeError as exc:
        json_path: Path | None = None
        for line in text.splitlines():
            path_match = _SAVED_JSON_PATH_RX.match(line.strip())
            if not path_match:
                continue
            raw_value = path_match.group("value").strip()
            if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
                raw_value = raw_value[1:-1]
            json_path = Path(raw_value).expanduser()
            break

        if json_path is None:
            raise ValueError(f"Stage stdout is not valid JSON: {exc}") from exc

        if not json_path.is_file():
            raise ValueError(f"Stage reported SAVED_JSON_PATH but file does not exist: {json_path}") from exc

        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as file_exc:
            raise ValueError(
                f"Stage SAVED_JSON_PATH is not valid JSON ({json_path}): {file_exc}"
            ) from file_exc
