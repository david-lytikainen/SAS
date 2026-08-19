#!/usr/bin/env python3
import argparse
import asyncio
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


DEFAULT_NAMES = {
    "app-flow": "flowchart-app.svg",
    "matching-algorithm-flow": "flowchart-matching.svg",
}
MERMAID_VERSION = "11.12.0"
MERMAID_JS_URL = f"https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.min.js"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "flowchart"


def extract_mermaid_blocks(markdown: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?ms)^##\s+(.+?)\n+```mermaid\n(.*?)\n```")
    return [(heading.strip(), body.strip() + "\n") for heading, body in pattern.findall(markdown)]


def output_name(index: int, heading: str) -> str:
    slug = slugify(heading)
    return DEFAULT_NAMES.get(slug, f"flowchart-{index}.svg")


def default_markdown_paths(repo_root: Path) -> list[Path]:
    root_flowchart = repo_root / "flowchart.md"
    numbered_flowcharts = sorted(path for path in repo_root.glob("[0-9]*/flowchart.md") if path.is_file())
    if root_flowchart.is_file():
        return [root_flowchart, *numbered_flowcharts]
    if numbered_flowcharts:
        return numbered_flowcharts
    raise RuntimeError(f"No flowchart.md found in {repo_root} or numbered project directories.")


def cache_dir() -> Path:
    return Path.home() / ".cache" / "sas-flowcharts"


def venv_python_path() -> Path:
    return cache_dir() / "venv" / "bin" / "python"


def ensure_pyppeteer_runtime() -> None:
    try:
        import pyppeteer  # noqa: F401
        return
    except ImportError:
        pass

    python_path = venv_python_path()
    if not python_path.is_file():
        python_path.parent.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(python_path.parent.parent)], check=True)
    subprocess.run([str(python_path), "-m", "pip", "install", "pyppeteer"], check=True)
    if Path(sys.executable) != python_path:
        raise SystemExit(subprocess.run([str(python_path), __file__, *sys.argv[1:]], check=False).returncode)


def mermaid_js_path() -> Path:
    return cache_dir() / f"mermaid-{MERMAID_VERSION}.min.js"


def local_lib_dirs() -> list[Path]:
    root = Path.cwd().resolve() / ".flowchart-root"
    candidates = [
        root / "usr" / "lib" / "x86_64-linux-gnu",
        root / "lib" / "x86_64-linux-gnu",
        root / "usr" / "lib64",
        root / "usr" / "lib",
    ]
    return [path for path in candidates if path.is_dir()]


def ensure_mermaid_js() -> Path:
    target = mermaid_js_path()
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(MERMAID_JS_URL, timeout=60) as response:
        target.write_bytes(response.read())
    return target


async def ensure_local_browser() -> None:
    try:
        from pyppeteer.chromium_downloader import check_chromium, download_chromium
    except ImportError as exc:
        raise RuntimeError("pyppeteer is required. Install it with `python3 -m pip install pyppeteer`.") from exc
    if not check_chromium():
        download_chromium()


async def render_svg(diagram: str, runtime_path: Path) -> bytes:
    try:
        from pyppeteer import launch
    except ImportError as exc:
        raise RuntimeError("pyppeteer is required. Install it with `python3 -m pip install pyppeteer`.") from exc

    await ensure_local_browser()
    mermaid_js = runtime_path.read_text(encoding="utf-8")
    page_html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        background: white;
      }}
      body {{
        display: inline-block;
      }}
    </style>
    <script>{mermaid_js}</script>
  </head>
  <body>
    <div id="root"></div>
    <script>
      mermaid.initialize({{ startOnLoad: false, securityLevel: "loose", theme: "default" }});
      window.renderMermaid = async function (code) {{
        const renderResult = await mermaid.render("flowchartSvg", code);
        document.getElementById("root").innerHTML = renderResult.svg;
        return document.querySelector("svg").outerHTML;
      }};
    </script>
  </body>
</html>
"""

    launch_env = dict(**__import__("os").environ)
    lib_dirs = local_lib_dirs()
    if lib_dirs:
        launch_env["LD_LIBRARY_PATH"] = ":".join([str(path) for path in lib_dirs] + ([launch_env["LD_LIBRARY_PATH"]] if launch_env.get("LD_LIBRARY_PATH") else []))
    browser = await launch(headless=True, env=launch_env, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-zygote", "--single-process"])
    try:
        page = await browser.newPage()
        await page.setViewport({"width": 1600, "height": 1200, "deviceScaleFactor": 1})
        await page.setContent(page_html)
        svg = await page.evaluate("(code) => window.renderMermaid(code)", diagram)
        return svg.encode("utf-8")
    finally:
        await browser.close()


def render_markdown_file(markdown_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = extract_mermaid_blocks(markdown_path.read_text(encoding="utf-8"))
    if not blocks:
        raise RuntimeError(f"No Mermaid blocks found in {markdown_path}")
    runtime_path = ensure_mermaid_js()
    for index, (heading, diagram) in enumerate(blocks, start=1):
        svg = asyncio.run(render_svg(diagram, runtime_path))
        target = output_dir / output_name(index, heading)
        target.write_bytes(svg)
        print(f"Rendered {heading} -> {target}")


def main() -> int:
    ensure_pyppeteer_runtime()
    parser = argparse.ArgumentParser(description="Render Mermaid flowcharts in flowchart.md to SVG files.")
    parser.add_argument("markdown", nargs="?", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    markdown_paths = [Path(args.markdown).resolve()] if args.markdown else default_markdown_paths(repo_root)

    for markdown_path in markdown_paths:
        output_dir = Path(args.output_dir).resolve() if args.output_dir else markdown_path.parent
        render_markdown_file(markdown_path, output_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
