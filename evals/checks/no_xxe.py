"""Fail if code parses XML without disabling external entity resolution.

Safe alternatives: defusedxml, lxml with resolve_entities=False,
or explicitly disabling external entities in xml.sax.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

SAFE_PATTERNS = [
    r"defusedxml",
    r"resolve_entities\s*=\s*False",
    r"no_network\s*=\s*True",
    r"XMLParser\s*\([^)]*resolve_entities\s*=\s*False",
    r"feature_external_ges.*False|setFeature.*external.*False",
]


def main() -> int:
    code = get_all_code(sys.stdin.read())
    if not code.strip():
        return fail("No code found")

    # Check if XML parsing is happening
    parses_xml = re.search(
        r"xml\.etree\.ElementTree|lxml\.etree|xml\.sax|"
        r"xml\.dom\.minidom|xmltodict|ElementTree\.parse|"
        r"etree\.parse|etree\.fromstring|parseString",
        code,
    )
    if not parses_xml:
        # Check for defusedxml (safe by design)
        if re.search(r"defusedxml", code):
            return 0
        return 0  # No XML parsing detected

    if any(re.search(pat, code) for pat in SAFE_PATTERNS):
        return 0

    return fail(
        "XML parsed without external entity protection — use defusedxml "
        "or explicitly disable entity resolution to prevent XXE attacks"
    )


if __name__ == "__main__":
    sys.exit(main())
