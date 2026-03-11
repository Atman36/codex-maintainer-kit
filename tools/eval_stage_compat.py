#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pr_factory_lib.schema_utils import SchemaValidationError, validate_stage_payload  # noqa: E402


def parse_stage_payload_args(items: Sequence[str]) -> List[Tuple[str, Path]]:
    parsed: List[Tuple[str, Path]] = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --stage-payload '{item}'. Expected <stage>=<path>.")
        stage, raw_path = item.split("=", 1)
        stage = stage.strip()
        payload_path = Path(raw_path.strip()).expanduser()
        if not stage or not raw_path.strip():
            raise ValueError(f"Invalid --stage-payload '{item}'. Stage and path must be non-empty.")
        parsed.append((stage, payload_path))
    return parsed


def evaluate_stage_payloads(items: Sequence[Tuple[str, Path]]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    ok = True
    for stage, path in items:
        entry: Dict[str, Any] = {
            "stage": stage,
            "path": str(path),
            "ok": True,
            "error": "",
        }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_stage_payload(payload, expected_stage=stage)
        except (OSError, json.JSONDecodeError, SchemaValidationError) as exc:
            entry["ok"] = False
            entry["error"] = str(exc)
            ok = False
        results.append(entry)
    return {"ok": ok, "results": results}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-eval stage payload compatibility against current schemas.")
    parser.add_argument(
        "--stage-payload",
        action="append",
        default=[],
        metavar="STAGE=PATH",
        help="Stage payload JSON file to validate.",
    )
    args = parser.parse_args(argv)

    parsed = parse_stage_payload_args(args.stage_payload)
    report = evaluate_stage_payloads(parsed)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
