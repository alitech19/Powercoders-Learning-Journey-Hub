#!/usr/bin/env python3
"""
Dark-mode coverage pass.

The dark theme overrides the Tailwind --color-gray-* CSS variables, so a *plain*
light utility (bg-white, bg-gray-50, bg-amber-50, text-gray-600 …) with no explicit
`dark:` counterpart renders LIGHT in dark mode — i.e. invisible dark text on a light
tile.  This walks every template and, for each light utility that is missing its dark
counterpart, inserts the correct `dark:` variant immediately AFTER the light token.

In-place insertion (vs. appending to the end of the class) keeps the dark variant
inside the same {% if %}…{% endif %} block as the light token it mirrors, so
conditional classes stay conditional.  Inserting right after a Tailwind token is safe
because those tokens never live inside a Django {% %} / {{ }} tag.

The pass is idempotent: an exact duplicate dark token in the same class attribute is
collapsed afterwards, and a token whose dark variant already follows it is skipped.
"""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "frontend" / "templates"

COLORS = ("red", "green", "amber", "blue", "yellow", "purple", "orange", "indigo", "pink", "teal")

# light utility  ->  dark utility to insert when missing
RULES: dict[str, str] = {
    # neutral surfaces
    "bg-white": "dark:bg-gray-900",
    "bg-gray-50": "dark:bg-gray-800",
    "bg-gray-100": "dark:bg-gray-700",
    # neutral text
    "text-gray-900": "dark:text-gray-100",
    "text-gray-800": "dark:text-gray-200",
    "text-gray-700": "dark:text-gray-300",
    "text-gray-600": "dark:text-gray-400",
    # neutral borders
    "border-gray-300": "dark:border-gray-600",
    "border-gray-200": "dark:border-gray-700",
    "border-gray-100": "dark:border-gray-800",
}
for _c in COLORS:
    RULES[f"bg-{_c}-50"] = f"dark:bg-{_c}-950/40"     # alert / highlight surface
    RULES[f"bg-{_c}-100"] = f"dark:bg-{_c}-900/40"    # badge surface
    RULES[f"text-{_c}-800"] = f"dark:text-{_c}-300"
    RULES[f"text-{_c}-700"] = f"dark:text-{_c}-300"
    RULES[f"text-{_c}-600"] = f"dark:text-{_c}-400"
    RULES[f"border-{_c}-200"] = f"dark:border-{_c}-900/50"

CLASS_ATTR = re.compile(r'class="([^"]*)"')
COUNTERS: dict[str, int] = {}


def fix_attr(attr: str) -> str:
    # The toggle-switch knob is the one bg-white that must STAY white.
    knob = "peer-checked:translate-x" in attr

    for light, dark in RULES.items():
        if light == "bg-white" and knob:
            continue
        esc = re.escape(light)
        base = dark[len("dark:"):]      # e.g. "bg-gray-800"
        prop = light.split("-", 1)[0]   # "bg" | "text" | "border"

        # Match the light token with an optional state prefix (hover:, focus:, …) and an
        # optional /opacity suffix.  Skip it if it is itself a dark: token.  Skip if ANY dark
        # variant of the same CSS property already immediately follows — that means the author
        # (or an earlier hand-edit) already themed this element; don't fight their choice.
        pattern = re.compile(
            r'(?<![\w/:-])((?:[a-z-]+:)*)' + esc + r'(/\d+)?(?![\w/-])'
            r'(?!\s+dark:(?:[a-z-]+:)*' + re.escape(prop) + r'-)'
        )

        def repl(m: re.Match) -> str:
            state = m.group(1) or ""
            if state.startswith("dark:"):
                return m.group(0)
            COUNTERS[light] = COUNTERS.get(light, 0) + 1
            return m.group(0) + " dark:" + state + base

        attr = pattern.sub(repl, attr)

    # collapse any exact duplicate dark: tokens that two passes may have produced
    seen: set[str] = set()
    out: list[str] = []
    for tok in attr.split(" "):
        if tok.startswith("dark:"):
            if tok in seen:
                continue
            seen.add(tok)
        out.append(tok)
    return " ".join(out)


def main() -> None:
    changed = 0
    for path in TEMPLATES.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        updated = CLASS_ATTR.sub(lambda m: 'class="' + fix_attr(m.group(1)) + '"', original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Files changed: {changed}\n")
    print("Replacements by light token:")
    for k in sorted(COUNTERS, key=lambda x: -COUNTERS[x]):
        print(f"  {COUNTERS[k]:>4}  {k}")


if __name__ == "__main__":
    main()
