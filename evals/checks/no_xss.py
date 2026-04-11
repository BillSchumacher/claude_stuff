"""Fail if code constructs HTML responses with user data via string interpolation.

Multi-language: Python f-string HTML, Go fmt.Fprintf with HTML, JS template
literal HTML, PHP echo without htmlspecialchars.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _security_lib import get_all_code, fail

# Safe patterns that indicate proper escaping/templating
SAFE_PATTERNS = [
    r"render_template\s*\(",        # Python Jinja2
    r"template\.Execute\w*\s*\(",   # Go html/template
    r"html/template",               # Go html/template import
    r"\.render\s*\(",               # Express res.render
    r"ejs|handlebars|pug|nunjucks", # JS template engines
    r"htmlspecialchars\s*\(",       # PHP
    r"htmlentities\s*\(",           # PHP
    r"escape\s*\(|markupsafe",      # Python escape
    r"bleach\.clean\s*\(",          # Python bleach
    r"DOMPurify|sanitize",          # JS sanitizer
    r"Html\.Encode|HtmlEncoder",    # C#
]


def main() -> int:
    stdin = sys.stdin.read()
    code = get_all_code(
        stdin,
        languages=(
            "python", "py", "go", "golang", "javascript", "js",
            "typescript", "ts", "php", "csharp", "cs",
        ),
        strip_docs=False,
        require_language_tag=True,
    )
    if not code.strip():
        return fail("No code found")

    # If any safe pattern is present, trust the approach
    if any(re.search(pat, code, re.IGNORECASE) for pat in SAFE_PATTERNS):
        return 0

    # Python: f-string with HTML tags
    if re.search(r'f["\'].*<\w+[\s>]', code):
        return fail("HTML via f-string — use render_template (Jinja2 auto-escaping)")

    # Go: fmt.Fprintf/Sprintf with HTML tags
    if re.search(r'fmt\.(?:Fprintf|Sprintf)\s*\([^)]*<\w+', code):
        return fail("HTML via fmt.Fprintf — use html/template instead")

    # JS/TS: template literal with HTML tags
    if re.search(r"`[^`]*<\w+[^`]*\$\{", code):
        return fail("HTML via template literal — use a template engine with auto-escaping")

    # PHP: echo/print with variable (without htmlspecialchars)
    if re.search(r"(?:echo|print)\s+.*\$\w+.*[;]", code):
        if re.search(r"<\w+", code):
            return fail("PHP echo with variable in HTML context — use htmlspecialchars()")

    # String concatenation with HTML tags (universal)
    if re.search(r'["\']<\w+[\s>]["\']\s*\+', code):
        return fail("HTML via string concatenation — use a template engine with auto-escaping")

    # .format() with HTML tags
    if re.search(r'["\'].*<\w+[\s>].*["\']\.format\s*\(', code):
        return fail("HTML via .format() — use a template engine with auto-escaping")

    return 0


if __name__ == "__main__":
    sys.exit(main())
