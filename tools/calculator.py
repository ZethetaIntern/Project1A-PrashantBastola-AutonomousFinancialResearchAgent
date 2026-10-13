
"""Safe calculator for financial research."""

import math
import operator
from typing import Any


_OPERATIONS = {
    "add": operator.add,
    "subtract": operator.sub,
    "multiply": operator.mul,
    "divide": operator.truediv,
}


def calculate(
    operation: str,
    a: float,
    b: float,
) -> dict[str, Any]:
    """Calculate a basic arithmetic operation."""
    if operation not in _OPERATIONS:
        raise ValueError(f"Unsupported operation: {operation}")

    if not math.isfinite(a) or not math.isfinite(b):
        raise ValueError("Inputs must be finite numbers.")

    if operation == "divide" and b == 0:
        raise ValueError("Cannot divide by zero.")

    result = _OPERATIONS[operation](a, b)

    if not math.isfinite(result):
        raise ValueError("Calculation produced a non-finite result.")

    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
    }
