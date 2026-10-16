import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Classes that must not appear in any template
FORBIDDEN_CLASSES = [
    re.compile(r"\bbtn-accent\b"),
    re.compile(r"\bann-pill-(?:info|imp|urgent)\b"),
    re.compile(r"\btable-striped\b"),
    re.compile(r"\bcard-accent\b"),
]


def test_no_legacy_component_classes_in_templates():
    """Ensure no legacy component classes remain in HTML templates."""
    templates_dir = BASE_DIR / "templates"
    if not templates_dir.exists():
        return

    violations = []
    for tmpl_file in templates_dir.rglob("*.html"):
        lines = tmpl_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            for pat in FORBIDDEN_CLASSES:
                if pat.search(line):
                    violations.append(
                        f"{tmpl_file.relative_to(BASE_DIR)}:{idx} -> Matched forbidden class {pat.pattern}: '{line.strip()}'"
                    )

    assert not violations, "Legacy component classes found in templates:\n" + "\n".join(violations)
