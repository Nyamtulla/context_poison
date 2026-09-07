import sys
import json
import openpyxl

PATH = "/home/n646s681/context_sok/data/exports/paper_dashboard_source.xlsx"

def write_rows(records):
    wb = openpyxl.load_workbook(PATH)
    ws = wb["Papers"]
    header = [c.value for c in ws[1]]
    idx = {name: header.index(name) + 1 for name in header}
    for rec in records:
        row = rec.pop("row")
        for field, value in rec.items():
            ws.cell(row=row, column=idx[field], value=value)
        # mark PDF path now that it's downloaded
        arxiv_id = ws.cell(row=row, column=idx["arxiv_id"]).value
        if arxiv_id:
            ws.cell(row=row, column=idx["pdf_local_path"], value=f"data/papers/{arxiv_id}.pdf")
    wb.save(PATH)
    print(f"wrote {len(records)} rows")

if __name__ == "__main__":
    records = json.loads(sys.stdin.read())
    write_rows(records)
