#!/usr/bin/env python3
"""
Generate index.html for GitHub Pages.
Scans outputs/eval_report.json and assets/output/*.html to build a summary page.
"""

import json
import os
import re
import shutil
from pathlib import Path

WORK_DIR = Path("work")
WORK_DIR.mkdir(exist_ok=True)

PROJECT_ROOT = Path(".")
ASSETS_OUTPUT = PROJECT_ROOT / "assets" / "output"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DOCS_DIR = PROJECT_ROOT / "docs"
README_FILE = PROJECT_ROOT / "README.md"


def copy_html_to_work():
    """Copy HTML files from assets/output/ into work/ for deployment."""
    copied = []
    if ASSETS_OUTPUT.exists():
        for f in sorted(ASSETS_OUTPUT.glob("*.html")):
            dest = WORK_DIR / f.name
            shutil.copy2(f, dest)
            copied.append(f.name)
    return copied

def load_eval_report():
    """Load and parse eval_report.json"""
    report_path = OUTPUTS_DIR / "eval_report.json"
    if not report_path.exists():
        return None
    with open(report_path) as f:
        return json.load(f)

def load_readme():
    """Load project README"""
    if README_FILE.exists():
        with open(README_FILE) as f:
            content = f.read()
        return content[:2000]  # First 2000 chars
    return None

def scan_work_html_files():
    """Find all HTML files in work/ (already copied for deployment)."""
    html_files = []
    for f in sorted(WORK_DIR.glob("*.html")):
        if f.name == "index.html":
            continue
        size = f.stat().st_size
        html_files.append({
            "name": f.name,
            "path": f.name,  # relative to work/ root
            "size": size,
        })
    return html_files

def build_html(report, readme, html_files):
    """Build the index.html page"""

    # Header stats
    if report:
        benchmark = report.get("benchmark", "unknown")
        total = report.get("total_cases", 0)
        stacked = report.get("pass_rate", {}).get("stacked_skills", 0)
        synthesized = report.get("pass_rate", {}).get("synthesized_skill", 0)
        gain = report.get("normalized_gain", 0)
        has_report = True
    else:
        benchmark = total = stacked = synthesized = gain = "N/A"
        has_report = False

    # HTML rows for files
    file_rows = ""
    for f in html_files:
        size_kb = f["size"] / 1024
        file_rows += f"""
        <tr>
          <td><a href="{f['path']}">{f['name']}</a></td>
          <td>{size_kb:.1f} KB</td>
        </tr>"""

    readme_section = ""
    if readme:
        readme_section = f'<section class="readme"><h2>Project README</h2><pre class="preview">{escape_html(readme)}</pre></section>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Skill Composer — Evaluation Results</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      line-height: 1.6;
      padding: 2rem;
    }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    h1 {{ color: #58a6ff; margin-bottom: 0.5rem; }}
    .subtitle {{ color: #8b949e; margin-bottom: 2rem; }}
    .card {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }}
    .stat {{
      background: #21262d;
      border-radius: 6px;
      padding: 1rem;
      text-align: center;
    }}
    .stat-value {{
      font-size: 1.8rem;
      font-weight: bold;
      color: #58a6ff;
    }}
    .stat-label {{
      font-size: 0.85rem;
      color: #8b949e;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 0.75rem;
      border-bottom: 1px solid #30363d;
    }}
    th {{ color: #8b949e; font-weight: 600; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .readme pre {{
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      padding: 1rem;
      overflow: auto;
      max-height: 300px;
      font-size: 0.85rem;
      white-space: pre-wrap;
    }}
    footer {{
      text-align: center;
      color: #8b949e;
      margin-top: 2rem;
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Skill Composer</h1>
    <p class="subtitle">Query-specific skill composition framework — evaluation results &amp; artifacts</p>

    <div class="card">
      <h2>Benchmark Results</h2>
      <div class="stats">
        <div class="stat">
          <div class="stat-value">{benchmark}</div>
          <div class="stat-label">Benchmark</div>
        </div>
        <div class="stat">
          <div class="stat-value">{total}</div>
          <div class="stat-label">Total Cases</div>
        </div>
        <div class="stat">
          <div class="stat-value">{stacked if not has_report else f"{stacked:.1%}"}</div>
          <div class="stat-label">Stacked Skills</div>
        </div>
        <div class="stat">
          <div class="stat-value">{synthesized if not has_report else f"{synthesized:.1%}"}</div>
          <div class="stat-label">Synthesized Skill</div>
        </div>
        <div class="stat">
          <div class="stat-value">{gain if not has_report else f"{gain:+.1%}"}</div>
          <div class="stat-label">Normalized Gain</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Artifacts</h2>
      <table>
        <thead>
          <tr><th>File</th><th>Size</th></tr>
        </thead>
        <tbody>
          {file_rows or '<tr><td colspan="2">No artifacts found</td></tr>'}
        </tbody>
      </table>
    </div>

    {readme_section}

    <footer>
      Generated by ClawEvalKit · Updated automatically on push to main
    </footer>
  </div>
</body>
</html>"""

def escape_html(text):
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;"))

def main():
    # Copy HTML artifacts into work/ so they're included in the deployment
    copied = copy_html_to_work()
    print(f"Copied to work/: {copied}")

    report = load_eval_report()
    readme = load_readme()
    html_files = scan_work_html_files()

    html = build_html(report, readme, html_files)

    index_path = WORK_DIR / "index.html"
    with open(index_path, "w") as f:
        f.write(html)

    print(f"Generated {index_path}")

if __name__ == "__main__":
    main()
