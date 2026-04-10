"""Check that the code uses OpenTelemetry instrumentation (spans, attributes) on I/O boundaries."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code:
        return fail("No code found")

    # Must import opentelemetry
    if "opentelemetry" not in code and "from opentelemetry" not in code:
        return fail("No `opentelemetry` import found")

    # Must actually create at least one span
    span_indicators = [
        "start_as_current_span",
        "start_span",
        "tracer.start",
    ]
    if not any(ind in code for ind in span_indicators):
        return fail(
            "OpenTelemetry imported but no span is created "
            "(expected start_as_current_span / start_span)"
        )

    # Must NOT use print() for logging in a production service
    # (allow it in __main__ examples; flag if it's the only logging)
    has_print_only = "print(" in code and (
        "logging" not in code
        and "structlog" not in code
        and "logger" not in code
    )
    if has_print_only:
        return fail(
            "Service uses print() for output but no structured logger "
            "(expected `logging`, `structlog`, or equivalent)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
