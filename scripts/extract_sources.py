"""Preserve source exports and fingerprints; requires .[sources]."""
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rulebook', type=Path)
    parser.add_argument('workbook', type=Path)
    args = parser.parse_args()
    pages = PdfReader(args.rulebook).pages
    text = '\n\n'.join(f'--- PAGE {i+1} ---\n{p.extract_text() or ""}' for i, p in enumerate(pages))
    (ROOT / 'docs/rulebook-extracted.txt').write_text(text, encoding='utf-8')
    workbook = load_workbook(args.workbook, data_only=True)
    rows = {sheet.title: list(sheet.values) for sheet in workbook}
    (ROOT / 'data/card-table-extracted.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    manifest = {'sources': [{'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                            for path in (args.rulebook, args.workbook)], 'pdf_pages': len(pages)}
    (ROOT / 'data/source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
