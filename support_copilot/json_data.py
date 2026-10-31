"""Strict JSON parsing shared by HTTP, private case files, and JSONL tools."""

from __future__ import annotations

import json
import math
from typing import Any


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        # A syntactically valid exponent can overflow a Python float.
        raise ValueError("JSON number is outside the supported finite range")
    return value


def _reject_constant(token: str) -> None:
    # Python's default decoder otherwise accepts non-JSON NaN and Infinity.
    raise ValueError("Non-standard JSON numeric constant")


def strict_json_loads(data: str) -> Any:
    return json.loads(data, parse_float=_finite_float, parse_constant=_reject_constant)
