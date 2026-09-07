"""Open-access PDF acquisition (FR-9): download the PDF for every paper with
an arXiv ID and no `pdf_local_path` yet. Non-arXiv papers keep only their
URL/DOI on record — no paywall bypass is attempted (per SRS Section 2 scope).
"""
from __future__ import annotations

import logging

from . import db
from .clients.arxiv import ArxivClient

logger = logging.getLogger(__name__)


def fetch_pdfs(conn, config) -> dict:
    arxiv = ArxivClient(config)
    pdf_dir = config.path("pdf_dir")
    counts = {"downloaded": 0, "already_had": 0, "failed": 0, "skipped_no_arxiv": 0}

    for row in db.all_papers(conn):
        if not row["arxiv_id"]:
            counts["skipped_no_arxiv"] += 1
            continue
        if row["pdf_local_path"]:
            counts["already_had"] += 1
            continue
        dest = pdf_dir / f"{row['arxiv_id']}.pdf"
        try:
            ok = arxiv.download_pdf(row["arxiv_id"], dest)
        except Exception as exc:
            logger.warning("PDF download failed for %s: %s", row["arxiv_id"], exc)
            ok = False
        if ok:
            conn.execute(
                "UPDATE papers SET pdf_local_path = ? WHERE paper_id = ?",
                (str(dest), row["paper_id"]),
            )
            counts["downloaded"] += 1
        else:
            counts["failed"] += 1

    conn.commit()
    return counts
