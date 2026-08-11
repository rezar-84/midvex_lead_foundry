from pathlib import Path

failures = []
templates = list(Path("templates").rglob("*.html"))
base = Path("templates/foundry/base.html").read_text()
if 'lang="' not in base:
    failures.append("base template has no language attribute")
if "skip-link" not in base:
    failures.append("base template has no skip link")
for template in templates:
    text = template.read_text()
    if "<img" in text and "alt=" not in text:
        failures.append(f"{template}: image without visible alt attribute")
if failures:
    raise SystemExit("\n".join(failures))
print(f"Static accessibility checks passed for {len(templates)} templates.")
