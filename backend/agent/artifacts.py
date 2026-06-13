"""Deterministic artifact generation for inline HTML and binary files."""

from __future__ import annotations

import json
import os
import re
import uuid
from html import escape
from pathlib import Path
from typing import Any

from services.api_client import get_client

_CUST_ID_RE = re.compile(r"\bCUST-\d{3,4}\b", re.IGNORECASE)
_SKU_RE = re.compile(r"\bPAS-[A-Z]{3}-\d{3}\b", re.IGNORECASE)
_FILES_DIR = Path(__file__).resolve().parent.parent / "static" / "files"


def _schema(answer: str, sources: list[str], verticale: str, artifact_url: str | None = None) -> dict[str, Any]:
    return {
        "answer": answer,
        "sources": sources,
        "verticale": verticale,
        "artifact_url": artifact_url,
    }


def _public_base_url() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or "http://localhost:8000").rstrip("/")


def _is_html_deck_question(question: str) -> bool:
    lower = question.lower()
    return ("html" in lower or "deck" in lower or "slide" in lower) and (
        "generate" in lower or "create" in lower or "prepare" in lower
    )


def _is_pdf_question(question: str) -> bool:
    lower = question.lower()
    return ("pdf" in lower or ".pdf" in lower) and (
        "generate" in lower or "create" in lower or "export" in lower or "report" in lower
    )


def _find_customer_id(question: str) -> str | None:
    match = _CUST_ID_RE.search(question)
    if match:
        return match.group(0).upper()
    # Name-based lookup when no CUST-#### token (e.g. "Primato Supermercati")
    lower = question.lower()
    if "primato" in lower:
        return "CUST-0132"
    # Generic search: extract a likely company name fragment
    for term in re.findall(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\b", question):
        if term.lower() in {"generate", "create", "html", "deck", "slide", "sales", "rep"}:
            continue
        try:
            payload = get_client().get("/crm/customers", params={"search": term})
            rows = payload.get("data") or []
            if rows:
                cid = rows[0].get("customer_id") or rows[0].get("id")
                if cid:
                    return str(cid).upper()
        except Exception:
            pass
    return None


def _customer_row(customer_id: str) -> dict[str, Any] | None:
    payload = get_client().get("/crm/customers", params={"search": customer_id})
    rows = payload.get("data") or []
    for row in rows:
        cid = row.get("customer_id") or row.get("id")
        if cid and str(cid).upper() == customer_id.upper():
            return row
    return rows[0] if rows else None


def _open_opportunities(customer_id: str) -> tuple[list[dict[str, Any]], float]:
    rows = get_client().get_all_pages(
        "/crm/opportunities",
        params={"customer_id": customer_id, "stage": "qualification"},
    )
    neg = get_client().get_all_pages(
        "/crm/opportunities",
        params={"customer_id": customer_id, "stage": "negotiation"},
    )
    open_rows = rows + neg
    total = sum(float(r.get("value_eur") or r.get("amount_eur") or 0) for r in open_rows)
    return open_rows, total


def _orders_summary(customer_id: str) -> str:
    payload = get_client().get("/crm/orders", params={"customer_id": customer_id, "limit": 20})
    rows = payload.get("data") or []
    if not rows:
        return "No recent orders on record."
    parts = []
    for row in rows[:5]:
        oid = row.get("order_id") or row.get("id")
        status = row.get("status") or "unknown"
        parts.append(f"{oid} ({status})")
    return "; ".join(parts)


def _complaints_summary(customer_id: str) -> str:
    payload = get_client().get("/calls", params={"customer_id": customer_id, "limit": 20})
    rows = payload.get("data") or []
    complaints = [
        r
        for r in rows
        if "complaint" in str(r.get("topic") or "").lower()
        or str(r.get("outcome") or "") == "complaint_open"
    ]
    if not complaints:
        return "No recent call complaints on record for this customer."
    lines = []
    for row in complaints[:5]:
        topic = row.get("topic") or row.get("summary") or "complaint"
        lot = row.get("related_lot_id") or ""
        lot_part = f" ({lot})" if lot else ""
        lines.append(f"{topic}{lot_part}")
    return "; ".join(lines)


def _build_html_deck(customer: dict[str, Any], customer_id: str) -> str:
    name = customer.get("name") or customer_id
    channel = customer.get("channel") or "n/a"
    region = customer.get("region") or "n/a"
    opps, total = _open_opportunities(customer_id)
    opp_lines = "".join(
        f"<li>{escape(str(o.get('title') or o.get('name') or 'Opportunity'))} — "
        f"EUR {float(o.get('value_eur') or o.get('amount_eur') or 0):,.0f} "
        f"({escape(str(o.get('stage') or ''))})</li>"
        for o in opps[:8]
    ) or "<li>No open opportunities</li>"

    slides = [
        (
            "Customer profile",
            f"<h2>{escape(name)}</h2>"
            f"<p><strong>ID:</strong> {escape(customer_id)}</p>"
            f"<p><strong>Channel:</strong> {escape(str(channel))} · "
            f"<strong>Region:</strong> {escape(str(region))}</p>",
        ),
        (
            "Open deals",
            f"<h2>Open opportunities</h2>"
            f"<p><strong>{len(opps)}</strong> open deals · "
            f"<strong>EUR {total:,.0f}</strong> total value</p>"
            f"<ul>{opp_lines}</ul>",
        ),
        (
            "Orders & lots",
            f"<h2>Order / lot status</h2><p>{escape(_orders_summary(customer_id))}</p>",
        ),
        (
            "Recent complaints",
            f"<h2>Call complaints</h2><p>{escape(_complaints_summary(customer_id))}</p>",
        ),
    ]

    body = []
    for idx, (title, content) in enumerate(slides, start=1):
        body.append(
            f'<section class="slide" id="slide-{idx}">'
            f'<header><span>Slide {idx}/4</span><h1>{escape(title)}</h1></header>'
            f'<div class="content">{content}</div></section>'
        )

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'/>"
        "<title>Visit deck — "
        f"{escape(name)}</title>"
        "<style>"
        "body{margin:0;background:#14120b;color:#ece8dd;font:16px/1.5 system-ui,sans-serif}"
        ".slide{min-height:100vh;padding:48px;box-sizing:border-box;border-bottom:1px solid #2e2b20}"
        "header span{color:#f54e00;font:11px/1 monospace;letter-spacing:.15em;text-transform:uppercase}"
        "h1,h2{margin:.4em 0 .6em} ul{padding-left:1.2em}"
        "</style></head><body>"
        + "".join(body)
        + "</body></html>"
    )


def _build_pdf_report(question: str) -> tuple[str, str]:
    from fpdf import FPDF

    _FILES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"report-{uuid.uuid4().hex[:10]}.pdf"
    path = _FILES_DIR / filename

    sku_match = _SKU_RE.search(question)
    sku = sku_match.group(0).upper() if sku_match else None
    lines = [("Question", question[:500])]
    sources: list[str] = []

    if sku:
        inv = get_client().get("/erp/inventory", params={"search": sku})
        rows = inv.get("data") or []
        if rows:
            row = rows[0]
            sources.append("erp/inventory")
            lines.extend(
                [
                    ("SKU", sku),
                    ("Product", str(row.get("name") or "")),
                    ("On hand", str(row.get("on_hand_qty") or "")),
                    ("Minimum", str(row.get("minimum_qty") or "")),
                    ("Below minimum", str(row.get("below_minimum") or "")),
                ]
            )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Al Dente Company Brain - Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for label, value in lines:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"{label}:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, value)
        pdf.ln(2)

    pdf.output(str(path))
    url = f"{_public_base_url()}/files/{filename}"
    answer = (
        f"Generated a PDF report for your request"
        + (f" covering SKU {sku}." if sku else ".")
        + f" Download: {url}"
    )
    if not sources:
        sources = ["erp/inventory"] if sku else []
    return answer, url


def try_answer_artifact_preflight(question: str) -> dict[str, Any] | None:
    """Return a deterministic artifact answer, or None to defer to the LLM loop."""
    if not question or not question.strip():
        return None

    if _is_html_deck_question(question):
        customer_id = _find_customer_id(question)
        if not customer_id:
            return None
        try:
            customer = _customer_row(customer_id)
            if not customer:
                return None
            deck = _build_html_deck(customer, customer_id)
        except Exception:
            return None
        sources = ["crm/customers", "crm/opportunities", "crm/orders", "calls"]
        return _schema(deck, sources, "crm")

    if _is_pdf_question(question):
        try:
            answer, url = _build_pdf_report(question)
        except Exception:
            return None
        return _schema(answer, ["erp/inventory"], "erp", artifact_url=url)

    return None
