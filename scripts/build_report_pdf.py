"""Render the Markdown technical report to a printable PDF with WeasyPrint."""
from pathlib import Path
import mistune
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "TECHNICAL_REPORT.md"
OUTPUT = SOURCE.with_suffix(".pdf")

CSS = """
@page { size: letter; margin: 0.62in 0.70in 0.58in; @bottom-right { content: counter(page); font-size: 9px; color: #61748a; }}
html { font-family: 'DejaVu Sans', sans-serif; font-size: 11.1px; color: #17283b; }
body { line-height: 1.5; }
h1 { font-size: 22px; letter-spacing: -.35px; line-height: 1.18; color: #103f68; margin: 0 0 12px 0; border-bottom: 3px solid #20a4a0; padding-bottom: 10px; }
h2 { font-size: 14.5px; line-height: 1.25; color: #0d5176; margin-top: 15px; margin-bottom: 5px; page-break-after: avoid; }
p { margin-top: 5px; margin-bottom: 8px; orphans: 2; widows: 2; }
li { padding-bottom: 2px; }
ul,ol { margin-top: 4px; padding-left: 20px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 10px; font-size: 9.7px; page-break-inside: avoid; }
th { background: #e5f2f8; text-align: left; border-bottom: 1px solid #8fb4c6; }
td,th { padding: 5px 7px; vertical-align: top; border-bottom: 1px solid #dce9ed; }
img { display: block; max-width: 95%; max-height: 190px; width: auto; margin: 8px auto 6px; object-fit: contain; page-break-inside: avoid; }
img[src$="architecture.png"] { max-width: 100%; max-height: 178px; }
a { color: #135e92; text-decoration: none; overflow-wrap: anywhere; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9.5px; color: #1d4670; background-color: #f3f6fa; padding: 1px 3px; }
strong { font-weight: 700; }
"""

def main():
    source = SOURCE.read_text(encoding="utf-8")
    parser = mistune.create_markdown(plugins=["table", "url"])
    html = f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{parser(source)}</body></html>'
    HTML(string=html, base_url=str(SOURCE.parent)).write_pdf(str(OUTPUT))
    print("Created:", OUTPUT, "bytes:", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
