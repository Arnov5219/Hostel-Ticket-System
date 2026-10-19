import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LEGACY_TOKEN_PATTERNS = [
    re.compile(r"--accent\b"),
    re.compile(r"--ann-(?:info|imp|urg)-(?:bg|fg)"),
    re.compile(r"--bg-base\b"),
    re.compile(r"#1D5FB4", re.IGNORECASE),
]


def test_no_legacy_tokens_in_css():
    """Ensure no legacy token references remain in CSS files."""
    css_dir = BASE_DIR / "static" / "css"
    if not css_dir.exists():
        return

    violations = []
    for css_file in css_dir.rglob("*.css"):
        lines = css_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            clean_line = line.strip()
            # Skip comments
            if clean_line.startswith("/*") or clean_line.startswith("*"):
                continue
            for pat in LEGACY_TOKEN_PATTERNS:
                if pat.search(line):
                    violations.append(
                        f"{css_file.relative_to(BASE_DIR)}:{idx} -> Matched legacy token {pat.pattern}: '{clean_line}'"
                    )

    assert not violations, "Legacy tokens found in CSS files:\n" + "\n".join(violations)


def test_no_legacy_tokens_in_templates():
    """Ensure no legacy token references remain in HTML templates."""
    templates_dir = BASE_DIR / "templates"
    if not templates_dir.exists():
        return

    violations = []
    for tmpl_file in templates_dir.rglob("*.html"):
        lines = tmpl_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            for pat in LEGACY_TOKEN_PATTERNS:
                if pat.search(line):
                    violations.append(
                        f"{tmpl_file.relative_to(BASE_DIR)}:{idx} -> Matched legacy token {pat.pattern}: '{line.strip()}'"
                    )

    assert not violations, "Legacy tokens found in templates:\n" + "\n".join(violations)
