"""Conservative diagnostic-output helpers for V24 smoke runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def json_ready(value: Any) -> Any:
    """Return a JSON-serializable representation of small diagnostic values."""

    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def write_json_diagnostic(
    payload: dict[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write non-final diagnostic JSON without overwriting by default."""

    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing diagnostic output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_ready(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
