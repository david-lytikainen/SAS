#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path


DEFAULT_NAMES = {
    "app-flow": "flowchart-app.svg",
    "matching-algorithm-flow": "flowchart-matching.svg",
}
NODE_DIST_INDEX_URL = "https://nodejs.org/dist/index.json"
NODE_RUNTIME_NAME = "node"
MERMAID_VERSION = "11.17.0"
SVGDOM_VERSION = "0.1.28"
JSDOM_VERSION = "30.0.1"
DOMPURIFY_VERSION = "3.4.14"
RENDERER_SCRIPT = """import { createHTMLWindow } from 'svgdom';
import createDOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

class SimpleCSSStyleSheet {
  constructor() {
    this.cssRules = [];
  }

  insertRule(rule, index = this.cssRules.length) {
    this.cssRules.splice(index, 0, { cssText: rule });
    return index;
  }

  replaceSync(text) {
    this.cssRules = [{ cssText: text }];
  }
}

globalThis.CSSStyleSheet = SimpleCSSStyleSheet;

const svgWindow = createHTMLWindow();
globalThis.window = svgWindow;
globalThis.document = svgWindow.document;
Object.defineProperty(globalThis, 'navigator', { value: svgWindow.navigator, configurable: true });
globalThis.Element = svgWindow.Element;
globalThis.Node = svgWindow.Node;
globalThis.HTMLElement = svgWindow.HTMLElement;
globalThis.SVGElement = svgWindow.SVGElement;

const domPurifyWindow = new JSDOM('').window;
const domPurifyInstance = createDOMPurify(domPurifyWindow);
Object.assign(createDOMPurify, domPurifyInstance);
globalThis.DOMPurify = createDOMPurify;
window.DOMPurify = createDOMPurify;

const mermaid = (await import('mermaid')).default;
const chunks = [];
for await (const chunk of process.stdin) {
  chunks.push(chunk);
}
const diagram = Buffer.concat(chunks).toString('utf8');
mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  htmlLabels: false,
  flowchart: { htmlLabels: false },
});
const { svg } = await mermaid.render('flowchartSvg', diagram);
process.stdout.write(svg);
"""


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


def runtime_dir() -> Path:
    return cache_dir() / "runtime"


def renderer_script_path() -> Path:
    return runtime_dir() / "render.mjs"


def package_json_path() -> Path:
    return runtime_dir() / "package.json"


def node_root() -> Path:
    return cache_dir() / NODE_RUNTIME_NAME


def node_bin_path() -> Path:
    return node_root() / "bin" / "node"


def npm_bin_path() -> Path:
    return node_root() / "bin" / "npm"


def fetch_node_version() -> str:
    with urllib.request.urlopen(NODE_DIST_INDEX_URL, timeout=60) as response:
        versions = json.load(response)
    for item in versions:
        files = set(item.get("files", []))
        if item.get("lts") and "linux-x64" in files:
            return item["version"]
    raise RuntimeError("Unable to find an LTS Node.js linux-x64 build.")


def ensure_node_runtime() -> None:
    if node_bin_path().is_file() and npm_bin_path().is_file():
        return
    cache_dir().mkdir(parents=True, exist_ok=True)
    version = fetch_node_version()
    archive_name = f"node-{version}-linux-x64.tar.xz"
    archive_path = cache_dir() / archive_name
    extracted_root = cache_dir() / f"node-{version}-linux-x64"
    if not archive_path.is_file():
        archive_url = f"https://nodejs.org/dist/{version}/{archive_name}"
        with urllib.request.urlopen(archive_url, timeout=120) as response:
            archive_path.write_bytes(response.read())
    if not extracted_root.is_dir():
        with tarfile.open(archive_path) as archive:
            archive.extractall(cache_dir())
    if node_root().exists() or node_root().is_symlink():
        node_root().unlink() if node_root().is_symlink() else None
    if not node_root().exists():
        node_root().symlink_to(extracted_root, target_is_directory=True)


def ensure_runtime_files() -> None:
    runtime_dir().mkdir(parents=True, exist_ok=True)
    package_json = {
        "private": True,
        "type": "module",
        "dependencies": {
            "dompurify": DOMPURIFY_VERSION,
            "jsdom": JSDOM_VERSION,
            "mermaid": MERMAID_VERSION,
            "svgdom": SVGDOM_VERSION,
        },
    }
    package_json_path().write_text(json.dumps(package_json, indent=2) + "\n", encoding="utf-8")
    renderer_script_path().write_text(RENDERER_SCRIPT, encoding="utf-8")


def ensure_node_dependencies() -> None:
    ensure_node_runtime()
    ensure_runtime_files()
    node_modules = runtime_dir() / "node_modules"
    package_lock = runtime_dir() / "package-lock.json"
    install_needed = not node_modules.is_dir()
    if not install_needed and package_lock.is_file():
        try:
            lock_data = json.loads(package_lock.read_text(encoding="utf-8"))
            install_needed = lock_data.get("packages", {}).get("", {}).get("dependencies", {}) != {
                "dompurify": DOMPURIFY_VERSION,
                "jsdom": JSDOM_VERSION,
                "mermaid": MERMAID_VERSION,
                "svgdom": SVGDOM_VERSION,
            }
        except json.JSONDecodeError:
            install_needed = True
    if not install_needed:
        return
    env = dict(os.environ)
    env["PATH"] = f"{node_root() / 'bin'}:{env.get('PATH', '')}"
    subprocess.run(
        [str(npm_bin_path()), "install", "--no-fund", "--no-audit"],
        cwd=runtime_dir(),
        env=env,
        check=True,
    )


def render_svg(diagram: str) -> bytes:
    ensure_node_dependencies()
    completed = subprocess.run(
        [str(node_bin_path()), str(renderer_script_path())],
        cwd=runtime_dir(),
        input=diagram.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8").strip() or "Local Mermaid render failed.")
    return completed.stdout


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


def main() -> int:
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
