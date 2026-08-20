#!/usr/bin/env python3
"""
Download, execute, and export all ThinkBayes2 chapters + solutions to a single
interleaved PDF: chapter 1, solutions 1, chapter 2, solutions 2, …
"""

import os
import re
import subprocess
import sys
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path

BASE_RAW  = "https://raw.githubusercontent.com/AllenDowney/ThinkBayes2/master/notebooks"
SOLN_RAW  = "https://raw.githubusercontent.com/AllenDowney/ThinkBayes2/master/soln"
UTILS_URL = f"{BASE_RAW}/utils.py"

# (chapter notebook stem, solutions notebook stem)
CHAPTERS = [
    ("chap01", "chap01"), ("chap02", "chap02"), ("chap03", "chap03"),
    ("chap04", "chap04"), ("chap05", "chap05"), ("chap06", "chap06"),
    ("chap07", "chap07"), ("chap08", "chap08"), ("chap09", "chap09"),
    ("chap10", "chap10"), ("chap11", "chap11"), ("chap12", "chap12"),
    ("chap13", "chap13"), ("chap14", "chap14"), ("chap15", "chap15"),
    ("chap16", "chap16"), ("chap17", "chap17"), ("chap18", "chap18"),
    ("chap19_v3", "chap19_v3"), ("chap20", "chap20"),
]

OUT_DIR    = Path(__file__).parent / "chapters"
BOOK_PDF   = Path(__file__).parent / "thinkbayes2.pdf"
TITLE_PAGE = OUT_DIR / "_title.pdf"

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]

PRINT_CSS = """
<style>
/* ── Page breaks ─────────────────────────────────────────────────────────── */
pre, .highlight, .jp-InputArea, .jp-OutputArea, .cell,
.input_area, .output_area { break-inside: avoid; }

/* ── Hide Jupyter chrome & anchors ───────────────────────────────────────── */
.jp-InputPrompt, .jp-OutputPrompt,
.input_prompt, .output_prompt,
.prompt, div.prompt,
.out_prompt_overlay,
#notebook-container .prompt,
.celltoolbar, .ctb_globalshow,
.jp-Toolbar, #menubar, #header,
.navbar, .nav,
a.anchor-link, .anchor-link { display: none !important; }

/* ── Page & content layout ───────────────────────────────────────────────── */
body {
  background: #fff;
  margin: 0;
  padding: 0;
}
#notebook-container,
.jp-Notebook,
.container { max-width: 100% !important; width: 100% !important; padding: 0 !important; box-shadow: none !important; }

/* ── Typography — override nbconvert defaults aggressively ───────────────── */
body, p, li, td, th, blockquote,
.jp-RenderedHTMLCommon,
.jp-RenderedHTMLCommon p,
.text_cell_render {
  font-family: Georgia, 'Times New Roman', serif !important;
  font-size: 11.5pt !important;
  line-height: 1.38 !important;
  color: #1c1c1c !important;
}

/* ── Links — no blue in a book ───────────────────────────────────────────── */
a { color: #1c1c1c !important; text-decoration: none !important; }

/* ── Headings ────────────────────────────────────────────────────────────── */
h1, h2, h3, h4 { font-family: Georgia, serif !important; color: #111 !important; }
h1 {
  font-size: 20pt !important; font-weight: 700;
  margin: 2em 0 0.5em !important;
  padding-bottom: 0.3em;
  border-bottom: 2px solid #ddd;
}
h2 { font-size: 14pt !important; font-weight: 700; margin: 1.6em 0 0.4em !important; }
h3 { font-size: 12pt !important; font-weight: 700; margin: 1.3em 0 0.3em !important; }

/* ── Paragraphs ──────────────────────────────────────────────────────────── */
p { margin: 0 0 0.75em !important; }

/* ── Code ────────────────────────────────────────────────────────────────── */
pre, code, kbd, samp,
.jp-InputArea pre, .highlight pre {
  font-family: 'SF Mono', Menlo, Monaco, 'Courier New', monospace !important;
  font-size: 9pt !important;
  line-height: 1.4 !important;
  color: #1c1c1c !important;
}
div.highlight, .jp-InputArea .highlight {
  background: #f6f6f6 !important;
  border: none !important;
  border-left: 3px solid #5b8dd9 !important;
  border-radius: 0 3px 3px 0 !important;
  padding: 0.85em 1em 0.85em 1.1em !important;
  margin: 0.3em 0 !important;
}

/* ── Output text ─────────────────────────────────────────────────────────── */
.jp-OutputArea-output pre, .output_text pre, .output_subarea pre {
  background: #fafafa !important;
  border-left: 3px solid #d0d0d0 !important;
  padding: 0.55em 1em !important;
  font-size: 8.5pt !important;
  color: #333 !important;
  border-radius: 0 3px 3px 0 !important;
}

/* ── Tables ──────────────────────────────────────────────────────────────── */
table {
  border-collapse: collapse !important;
  margin: 1em auto !important;
  font-family: Georgia, serif !important;
  font-size: 10pt !important;
  width: auto !important;
}
th {
  background: #2e5fa3 !important;
  color: #fff !important;
  padding: 6px 18px !important;
  font-weight: 600 !important;
}
td {
  padding: 5px 18px !important;
  border-bottom: 1px solid #e0e0e0 !important;
  color: #1c1c1c !important;
}
tr:nth-child(even) td { background: #f2f5fb !important; }

/* ── Images ──────────────────────────────────────────────────────────────── */
img, svg { max-width: 88% !important; height: auto; display: block; margin: 1em auto; }

/* ── Blockquotes ─────────────────────────────────────────────────────────── */
blockquote {
  border-left: 3px solid #5b8dd9 !important;
  margin: 1em 0 !important;
  padding: 0.4em 1em !important;
  color: #3a3a3a !important;
  font-style: italic !important;
  background: #f5f7fc !important;
}
</style>
</head>"""

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

PREFETCH = {
    "chap19_v3": [
        ("https://github.com/AllenDowney/ThinkBayes2/raw/master/data/WHR20_DataForFigure2.1.xls",
         "WHR20_DataForFigure2.1.xls"),
        ("https://github.com/AllenDowney/ThinkBayes2/raw/master/data/drp_scores.csv",
         "drp_scores.csv"),
    ],
    "soln_chap19_v3": [
        ("https://github.com/AllenDowney/ThinkBayes2/raw/master/data/WHR20_DataForFigure2.1.xls",
         "WHR20_DataForFigure2.1.xls"),
        ("https://github.com/AllenDowney/ThinkBayes2/raw/master/data/drp_scores.csv",
         "drp_scores.csv"),
    ],
}


# ── helpers ───────────────────────────────────────────────────────────────────

def download(url: str, dest: Path, retries: int = 3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            return
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  download retry {attempt + 1}/{retries} for {dest.name}: {e}", flush=True)


def find_chrome() -> str | None:
    for p in CHROME_PATHS:
        if p and Path(p).exists():
            return p
    return None


def execute_to_html(nb_path: Path, html_path: Path, work_dir: Path):
    result = subprocess.run(
        [
            sys.executable, "-m", "nbconvert",
            "--to", "html",
            "--execute",
            "--ExecutePreprocessor.timeout=600",
            "--ExecutePreprocessor.kernel_name=python3",
            "--output", str(html_path.resolve()),
            str(nb_path.resolve()),
        ],
        cwd=str(work_dir.resolve()),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])


def title_from_html(html_path: Path) -> str:
    text = html_path.read_text(encoding="utf-8")
    m = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.DOTALL)
    if not m:
        return html_path.stem
    return re.sub(r'<[^>]+>', '', m.group(1)).replace('¶', '').strip()


def patch_html(html_path: Path):
    text = html_path.read_text(encoding="utf-8")
    html_path.write_text(text.replace("</head>", PRINT_CSS, 1), encoding="utf-8")


def header_template(label: str) -> str:
    return (
        '<div style="font-family: -apple-system, Helvetica, sans-serif; '
        'font-size: 9px; width: 100%; padding: 0 15mm; box-sizing: border-box; '
        'display: flex; justify-content: space-between; color: #888;">'
        f'<span>{label}</span>'
        '<span><span class="pageNumber"></span></span>'
        '</div>'
    )


def html_to_pdf(html_path: Path, pdf_path: Path, chrome: str, header: str = ""):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("""async () => {
            if (window.MathJax && MathJax.typesetPromise) {
                await MathJax.typesetPromise();
            }
        }""")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "20mm", "bottom": "15mm",
                    "left": "15mm", "right": "15mm"},
            print_background=True,
            display_header_footer=True,
            header_template=header_template(header) if header else "<span></span>",
            footer_template="<span></span>",
        )
        browser.close()


def make_divider_page(chrome: str, label: str, title: str, out_pdf: Path):
    html = out_pdf.with_suffix(".html")
    html.write_text(f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: #fff;
    color: #111;
    text-align: center;
  }}
  .rule {{ width: 80px; height: 3px; background: #2e5fa3; margin: 0 auto 28px; }}
  .label {{
    font-size: 11pt;
    font-weight: 400;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #2e5fa3;
    margin-bottom: 18px;
  }}
  .title {{
    font-size: 28pt;
    font-weight: 700;
    line-height: 1.25;
    max-width: 75%;
    color: #111;
  }}
</style>
</head>
<body>
  <div class="rule"></div>
  <div class="label">{label}</div>
  <div class="title">{title}</div>
</body>
</html>
""", encoding="utf-8")
    html_to_pdf(html, out_pdf, chrome)


def make_title_page(chrome: str):
    html = OUT_DIR / "_title.html"
    html.write_text("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, Helvetica, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    text-align: center;
    color: #222;
    background: #fff;
  }
  .subtitle  { font-size: 18px; color: #555; margin-top: 12px; }
  .title     { font-size: 42px; font-weight: 700; margin-top: 8px; }
  .edition   { font-size: 16px; color: #888; margin-top: 8px; }
  .author    { font-size: 22px; margin-top: 48px; }
  .note      { font-size: 13px; color: #888; margin-top: 8px; }
  .divider   { width: 60px; height: 3px; background: #ddd; margin: 40px auto; }
  .license   { font-size: 12px; color: #aaa; max-width: 400px; line-height: 1.6; }
</style>
</head>
<body>
  <div class="subtitle">Bayesian Statistics Made Simple</div>
  <div class="title">Think Bayes</div>
  <div class="edition">Second Edition</div>
  <div class="author">Allen B. Downey</div>
  <div class="note">With executed code, charts, and solutions</div>
  <div class="divider"></div>
  <div class="license">
    Original work by Allen Downey.<br>
    Source: <em>github.com/AllenDowney/ThinkBayes2</em><br>
    Licensed under CC BY-NC-SA 4.0
  </div>
</body>
</html>
""", encoding="utf-8")
    html_to_pdf(html, TITLE_PAGE, chrome)


def merge_pdfs(pdf_paths: list[Path], out: Path):
    from pypdf import PdfWriter
    writer = PdfWriter()
    for p in pdf_paths:
        writer.append(str(p))
    with open(out, "wb") as f:
        writer.write(f)


def process_notebook(key: str, nb_url: str, nb_path: Path,
                     html_path: Path, pdf_path: Path,
                     chrome: str, header_prefix: str = "") -> Path | None:
    """Returns pdf_path on success, None on failure."""
    # ── step 1: execute notebook → HTML (slow, cached independently) ──────────
    if html_path.exists():
        print(f"  {key}: html cached", flush=True)
    else:
        print(f"  {key}: downloading ...", flush=True)
        try:
            download(nb_url, nb_path)
        except Exception as e:
            print(f"  {key}: FAILED (download): {e}", flush=True)
            return None

        for url, fname in PREFETCH.get(key, []):
            dest = OUT_DIR / fname
            if not dest.exists():
                try:
                    download(url, dest)
                except Exception as e:
                    print(f"  {key}: WARN prefetch {fname}: {e}", flush=True)

        print(f"  {key}: executing ...", flush=True)
        try:
            execute_to_html(nb_path, html_path, OUT_DIR)
        except Exception as e:
            print(f"  {key}: FAILED (execute):\n{str(e)[:2000]}", flush=True)
            return None

    # Always re-patch so CSS changes apply without re-executing
    patch_html(html_path)

    # ── step 2: HTML → PDF (fast; delete *.pdf to redo without re-executing) ──
    if pdf_path.exists():
        print(f"  {key}: pdf cached", flush=True)
        return pdf_path

    title  = title_from_html(html_path)
    header = f"{header_prefix}{title}" if header_prefix else title

    print(f"  {key}: → PDF ...", flush=True)
    try:
        html_to_pdf(html_path, pdf_path, chrome, header=header)
        print(f"  {key}: done", flush=True)
        return pdf_path
    except Exception as e:
        print(f"  {key}: FAILED (pdf): {e}", flush=True)
        return None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    chrome = find_chrome()
    if not chrome:
        print("ERROR: Chrome not found. Install Google Chrome and retry.")
        sys.exit(1)

    # Cap workers: each kernel uses ~300 MB RAM; playwright adds ~150 MB per browser
    workers = min(os.cpu_count() or 4, 8)
    print(f"Using Chrome: {chrome}")
    print(f"Parallel workers: {workers}\n")

    OUT_DIR.mkdir(exist_ok=True)

    utils_dest = OUT_DIR / "utils.py"
    if not utils_dest.exists():
        print("Downloading utils.py ...")
        download(UTILS_URL, utils_dest)

    print("Generating title page ...")
    make_title_page(chrome)

    # Build task list: (chap_key, soln_key, paths...)
    tasks: list[tuple] = []
    for chap, soln in CHAPTERS:
        soln_key = f"soln_{soln}"
        tasks.append((
            chap, soln_key,
            OUT_DIR / f"{chap}.html",   OUT_DIR / f"{chap}.pdf",
            OUT_DIR / f"{soln_key}.html", OUT_DIR / f"{soln_key}.pdf",
        ))

    # Submit all notebooks (chapters + solutions) concurrently
    with ThreadPoolExecutor(max_workers=workers) as pool:
        chap_futures: list[tuple[Future, Future, tuple]] = []
        for chap, soln_key, ch_html, ch_pdf, sl_html, sl_pdf in tasks:
            cf = pool.submit(
                process_notebook, chap,
                f"{BASE_RAW}/{chap}.ipynb", OUT_DIR / f"{chap}.ipynb",
                ch_html, ch_pdf, chrome, "",
            )
            sf = pool.submit(
                process_notebook, soln_key,
                f"{SOLN_RAW}/{soln_key.removeprefix('soln_')}.ipynb",
                OUT_DIR / f"{soln_key}.ipynb",
                sl_html, sl_pdf, chrome, "Solutions — ",
            )
            chap_futures.append((cf, sf, chap, soln_key, ch_html, sl_html, ch_pdf, sl_pdf))

        # Collect results in chapter order
        interleaved: list[Path] = [TITLE_PAGE]
        failed: list[str] = []

        for cf, sf, chap, soln_key, ch_html, sl_html, ch_pdf, sl_pdf in chap_futures:
            chap_result = cf.result()
            soln_result = sf.result()

            if chap_result:
                chap_num = re.search(r'\d+', chap).group()
                div_pdf  = OUT_DIR / f"{chap}_divider.pdf"
                make_divider_page(chrome, f"Chapter {chap_num}", title_from_html(ch_html), div_pdf)
                interleaved += [div_pdf, chap_result]
            else:
                failed.append(chap)

            if soln_result:
                soln_num = re.search(r'\d+', soln_key).group()
                sdiv_pdf = OUT_DIR / f"{soln_key}_divider.pdf"
                make_divider_page(chrome, f"Solutions — Chapter {soln_num}", title_from_html(sl_html), sdiv_pdf)
                interleaved += [sdiv_pdf, soln_result]
            else:
                failed.append(soln_key)

    if len(interleaved) <= 1:
        print("\nNothing succeeded.")
        sys.exit(1)

    print(f"\nMerging {len(interleaved)} PDFs into {BOOK_PDF.name} ...")
    merge_pdfs(interleaved, BOOK_PDF)
    print(f"Done!  {BOOK_PDF.resolve()}")

    if failed:
        print(f"\nFailed (skipped): {', '.join(failed)}")


if __name__ == "__main__":
    main()
