#!/usr/bin/env python3
import argparse
import base64
import json
import time
import re
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path


DEFAULT_NAMES = {
    "app-flow": "flowchart-app.svg",
    "matching-algorithm-flow": "flowchart-matching.svg",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "flowchart"


def extract_mermaid_blocks(markdown: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?ms)^##\s+(.+?)\n+```mermaid\n(.*?)\n```")
    return [(heading.strip(), body.strip() + "\n") for heading, body in pattern.findall(markdown)]


def mermaid_ink_url(diagram: str) -> str:
    payload = json.dumps(
        {"code": diagram, "mermaid": {"theme": "default"}},
        separators=(",", ":"),
    ).encode("utf-8")
    compressed = zlib.compress(payload, 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return f"https://mermaid.ink/svg/pako:{encoded}"


def kroki_url(diagram: str) -> str:
    compressed = zlib.compress(diagram.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return f"https://kroki.io/mermaid/svg/{encoded}"


def render_svg(diagram: str) -> bytes:
    errors: list[str] = []
    renderers = [("mermaid.ink", mermaid_ink_url(diagram)), ("kroki", kroki_url(diagram))]

    for name, url in renderers:
        for attempt in range(3):
            request = urllib.request.Request(url, headers={"User-Agent": "SAS flowchart renderer", "Accept": "image/svg+xml,text/plain,*/*"})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                errors.append(f"{name} attempt {attempt + 1}: HTTP {exc.code}: {body}")
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except urllib.error.URLError as exc:
                errors.append(f"{name} attempt {attempt + 1}: {exc.reason}")
            time.sleep(1 + attempt)

    raise RuntimeError("Render failed. " + " | ".join(errors))


def output_name(index: int, heading: str) -> str:
    slug = slugify(heading)
    return DEFAULT_NAMES.get(slug, f"flowchart-{index}.svg")


def render_markdown_file(markdown_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = extract_mermaid_blocks(markdown_path.read_text(encoding="utf-8"))
    if not blocks:
        raise RuntimeError(f"No Mermaid blocks found in {markdown_path}")

    for index, (heading, diagram) in enumerate(blocks, start=1):
        svg = render_svg(diagram)
        target = output_dir / output_name(index, heading)
        target.write_bytes(svg)
        print(f"Rendered {heading} -> {target}")


def default_markdown_paths(repo_root: Path) -> list[Path]:
    root_flowchart = repo_root / "flowchart.md"
    numbered_flowcharts = sorted(path for path in repo_root.glob("[0-9]*/flowchart.md") if path.is_file())

    if root_flowchart.is_file():
        return [root_flowchart, *numbered_flowcharts]

    if numbered_flowcharts:
        return numbered_flowcharts

    raise RuntimeError(f"No flowchart.md found in {repo_root} or numbered project directories.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Mermaid flowcharts in flowchart.md to SVG files.")
    parser.add_argument("markdown", nargs="?", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()

    if args.markdown:
        markdown_paths = [Path(args.markdown).resolve()]
    else:
        markdown_paths = default_markdown_paths(repo_root)

    for markdown_path in markdown_paths:
        if args.output_dir:
            output_dir = Path(args.output_dir).resolve()
        else:
            output_dir = markdown_path.parent
        render_markdown_file(markdown_path, output_dir)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
