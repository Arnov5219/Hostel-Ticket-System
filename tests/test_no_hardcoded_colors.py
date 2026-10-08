import re
from pathlib import Path

# Match hex colors (#fff, #1a56db, etc.), rgb(), rgba(), hsl(), hsla()
HEX_COLOR_REGEX = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
RGB_HSL_REGEX = re.compile(r"\b(?:rgb|rgba|hsl|hsla)\s*\(")

# Allowed special keywords and exceptions
ALLOWED_EXCEPTIONS = [
    # Allow inside SVG elements or URL fragments like #id
    re.compile(r'href="#'),
    re.compile(r'action="#'),
    re.compile(r'id="#'),
    re.compile(r'x-ref="#'),
]

BASE_DIR = Path(__file__).resolve().parent.parent


def test_no_hardcoded_colors_in_css():
    """
    CSS files outside tokens.css must not use hard-coded color literals (#hex, rgb, hsl).
    All colors must use var(--token).
    """
    css_dir = BASE_DIR / "static" / "css"
    if not css_dir.exists():
        return

    violations = []
    for css_file in css_dir.rglob("*.css"):
        if css_file.name == "tokens.css":
            continue

        lines = css_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            # Ignore comments
            clean_line = line.strip()
            if clean_line.startswith("/*") or clean_line.startswith("*"):
                continue

            # Check hex
            hex_matches = HEX_COLOR_REGEX.findall(line)
            for match in hex_matches:
                violations.append(f"{css_file.relative_to(BASE_DIR)}:{idx} -> Hex color: {match} in '{clean_line}'")

            # Check rgb/rgba/hsl/hsla
            rgb_matches = RGB_HSL_REGEX.findall(line)
            for match in rgb_matches:
                violations.append(f"{css_file.relative_to(BASE_DIR)}:{idx} -> Color func: {match} in '{clean_line}'")

    assert not violations, "Hardcoded colors found in CSS outside tokens.css:\n" + "\n".join(violations)


def test_no_hardcoded_colors_in_templates():
    """
    Templates must not use hardcoded color literals (#hex, rgb, hsl) in inline styles.
    """
    templates_dir = BASE_DIR / "templates"
    if not templates_dir.exists():
        return

    violations = []
    # Pattern to match style="..." attributes
    style_attr_regex = re.compile(r'style="([^"]*)"', re.IGNORECASE)

    for tmpl_file in templates_dir.rglob("*.html"):
        if tmpl_file.name == "ui_kit.html":
            continue

        content = tmpl_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            for style_match in style_attr_regex.finditer(line):
                style_content = style_match.group(1)
                hex_matches = HEX_COLOR_REGEX.findall(style_content)
                for h in hex_matches:
                    violations.append(f"{tmpl_file.relative_to(BASE_DIR)}:{idx} -> Hex color {h} in style='{style_content}'")
                rgb_matches = RGB_HSL_REGEX.findall(style_content)
                for r in rgb_matches:
                    violations.append(f"{tmpl_file.relative_to(BASE_DIR)}:{idx} -> Color func {r} in style='{style_content}'")

    assert not violations, "Hardcoded colors found in template inline styles:\n" + "\n".join(violations[:40]) + (f"\n... and {len(violations)-40} more" if len(violations) > 40 else "")
