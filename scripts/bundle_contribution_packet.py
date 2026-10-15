"""Bundle one contribution-screen packet with its PDFs, ready to hand off.

    python3 scripts/bundle_contribution_packet.py 1
    python3 scripts/bundle_contribution_packet.py 1 --zip

Produces data/exports/contribution_screen/bundles/packet-NN/ holding the
spreadsheet, the 60 PDFs, and the prompt. The spreadsheet's pdf column is
rewritten to a bare filename so it resolves inside the bundle rather than
against this repo.
"""
import argparse
import pathlib
import shutil

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "exports" / "contribution_screen"
OUT = SRC / "bundles"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("packet", type=int)
    ap.add_argument("--zip", action="store_true")
    a = ap.parse_args()

    xl = SRC / f"contribution-screen-{a.packet:02d}.xlsx"
    if not xl.exists():
        raise SystemExit(f"no such packet: {xl}")
    dest = OUT / f"packet-{a.packet:02d}"
    pdfs = dest / "pdfs"
    pdfs.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.load_workbook(xl)
    ws = wb["papers"]
    col = [c.value for c in ws[1]].index("pdf") + 1
    copied = missing = 0
    for r in range(2, ws.max_row + 1):
        p = ws.cell(r, col).value
        if not p:
            continue
        src = REPO / p
        if src.exists():
            shutil.copy2(src, pdfs / src.name)
            ws.cell(r, col).value = f"pdfs/{src.name}"
            copied += 1
        else:
            ws.cell(r, col).value = "MISSING"
            missing += 1
    wb.save(dest / xl.name)
    wb.close()

    prompt = REPO / "CONTRIBUTION_SCREEN_PROMPT.md"
    if prompt.exists():
        shutil.copy2(prompt, dest / "PROMPT.md")

    size = sum(f.stat().st_size for f in pdfs.rglob("*")) / 1e6
    print(f"bundle: {dest}")
    print(f"  {copied} PDFs copied ({size:.0f} MB), {missing} missing")
    if a.zip:
        shutil.make_archive(str(dest), "zip", dest)
        print(f"  zipped: {dest}.zip")


if __name__ == "__main__":
    main()
